import hashlib
import json
import re

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from core.cases.models import LegalCase
from core.cases.matching import find_context_cases
from core.models import Conversation, ConversationMessage, db
from core.moderation.actions import apply_content_status, queue_content_review
from core.moderation.models import PendingReview
from core.moderation.words import decide, describe_hits, scan_text, top_severity
from core.privacy import RedactionSession, public_redaction_summary
from core.recommendations.events import record_event
from core.search.indexing import process_outbox
from core.taxonomy import domain_for_category, infer_legal_domain

from .models import (
    CommunityCategory,
    CommunityComment,
    CommunityPost,
    CommunityPostCaseLink,
    CommunityPostOrigin,
    Notification,
)


def clean_public_text(value, *, max_length, field_name):
    if not isinstance(value, str):
        raise ValueError(f"{field_name}必须是文本")
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value).strip()
    if not value:
        raise ValueError(f"请输入{field_name}")
    if len(value) > max_length:
        raise ValueError(f"{field_name}不能超过{max_length}字")
    session = RedactionSession()
    return session.redact(value), public_redaction_summary(session)


def _screen_banned_words(text):
    """违禁词分级筛查。返回 (action, hits, reason, warnings)。

    action: ok 无命中 / reject 直接拒绝 / review 转人工审核 / warn 提示但放行。
    """
    action, hits = decide(scan_text(text))
    warnings = list(dict.fromkeys(hit["word"] for hit in hits))
    return action, hits, describe_hits(hits), warnings


def category_or_error(value):
    category = None
    if isinstance(value, int) or str(value or "").isdigit():
        category = CommunityCategory.query.filter_by(id=int(value), is_active=True).first()
    elif isinstance(value, str):
        category = CommunityCategory.query.filter_by(slug=value.strip(), is_active=True).first()
    if category is None:
        raise ValueError("请选择有效的社区分类")
    return category


def related_cases_for_post(post, limit=4):
    linked = [
        case for case in LegalCase.query.join(CommunityPostCaseLink, CommunityPostCaseLink.case_id == LegalCase.id)
        .filter(
            CommunityPostCaseLink.post_id == post.id,
            LegalCase.status == "published",
            LegalCase.verification_status == "verified",
        )
        .order_by(CommunityPostCaseLink.relevance_score.desc())
        .limit(limit).all()
    ]
    if len(linked) >= limit:
        return linked
    post_context = f"{post.title}\n{post.body}"
    domain = infer_legal_domain(post_context, fallback=domain_for_category(post.category.slug))
    excluded = [item.id for item in linked]
    linked.extend(find_context_cases(
        post_context, domain, limit=limit - len(linked), exclude_ids=excluded,
    ))
    return linked


def create_post(user_id, data):
    category = category_or_error(data.get("category"))
    title, title_meta = clean_public_text(data.get("title", ""), max_length=160, field_name="标题")
    body, body_meta = clean_public_text(data.get("body", ""), max_length=12000, field_name="正文")
    post_type = data.get("post_type", "discussion")
    if not isinstance(post_type, str) or post_type not in {"discussion", "legal_help"}:
        raise ValueError("帖子类型无效")
    action, hits, reason, warnings = _screen_banned_words(f"{title}\n{body}")
    if action == "reject":
        raise ValueError("内容包含违禁信息，已拒绝发布：" + "、".join(warnings))
    draft_token = str(data.get("draft_token") or "")
    origin = verify_ai_draft_token(draft_token, user_id) if draft_token else None
    review_state = "pending" if action == "review" else "approved"
    post = CommunityPost(
        author_id=user_id,
        category_id=category.id,
        post_type=post_type,
        title=title,
        body=body,
        is_anonymous=bool(data.get("is_anonymous")),
        help_status="open",
        status="hidden" if review_state == "pending" else "published",
    )
    db.session.add(post)
    db.session.flush()
    if review_state == "pending":
        queue_content_review(
            "post", post.id,
            severity=top_severity(hits),
            reason=reason,
        )
        db.session.add(Notification(
            user_id=user_id,
            notification_type="moderation",
            target_type="post",
            target_id=str(post.id),
            summary="你的帖子包含敏感词，已提交人工审核",
        ))

    if origin:
        db.session.add(CommunityPostOrigin(
            post_id=post.id,
            source_conversation_id=origin.get("conversation_id"),
            source_message_id=origin.get("message_id"),
            redaction_summary_json=json.dumps({"title": title_meta, "body": body_meta}, ensure_ascii=False),
        ))
    record_event(
        user_id,
        "post",
        entity_type="post",
        entity_id=post.id,
        legal_domain=domain_for_category(category.slug),
        commit=False,
    )
    apply_content_status("post", post, post.status)
    db.session.commit()
    process_outbox(limit=10)
    return post, {
        "masked_count": title_meta.get("masked_count", 0) + body_meta.get("masked_count", 0),
        "review_state": review_state,
        "warnings": warnings,
    }


def update_post(post, data):
    """Screen the complete proposed edit before changing any stored fields."""
    if post.status == "deleted":
        raise ValueError("已删除的帖子不能修改")
    help_status = post.help_status
    if "help_status" in data and post.post_type == "legal_help":
        if not isinstance(data["help_status"], str) or data["help_status"] not in {"open", "answered", "resolved"}:
            raise ValueError("求助状态无效")
        help_status = data["help_status"]

    title, body = post.title, post.body
    title_meta, body_meta = {}, {}
    changed_content = "title" in data or "body" in data
    action, hits, reason, warnings = "ok", [], "", []
    if changed_content:
        if "title" in data:
            title, title_meta = clean_public_text(data["title"], max_length=160, field_name="标题")
        if "body" in data:
            body, body_meta = clean_public_text(data["body"], max_length=12000, field_name="正文")
        action, hits, reason, warnings = _screen_banned_words(f"{title}\n{body}")
        if action == "reject":
            raise ValueError("内容包含违禁信息，已拒绝发布：" + "、".join(warnings))

    pending_review = PendingReview.query.filter_by(
        target_type="post", target_id=str(post.id), status="pending"
    ).order_by(PendingReview.id.desc()).first()
    needs_review = bool(pending_review) or (changed_content and (action == "review" or post.status == "hidden"))
    post.title, post.body, post.help_status = title, body, help_status
    if changed_content and needs_review:
        # A cleared word match does not let the author undo a pending/manual hold.
        if not reason:
            reason = "内容已修改，等待管理员复核"
            if pending_review and pending_review.reason:
                reason += "；原审核原因：" + pending_review.reason
        queue_content_review("post", post.id, severity=top_severity(hits) or "medium", reason=reason)
    if needs_review:
        apply_content_status("post", post, "hidden")
    else:
        apply_content_status("post", post, post.status)
    db.session.commit()
    process_outbox(limit=10)
    return post, {
        "masked_count": title_meta.get("masked_count", 0) + body_meta.get("masked_count", 0),
        "review_state": "pending" if needs_review else ("approved" if post.status == "published" else "hidden"),
        "warnings": warnings,
    }


def create_comment(user_id, post, data):
    body, _meta = clean_public_text(data.get("body", ""), max_length=4000, field_name="评论")
    parent = None
    parent_id = data.get("parent_id")
    if parent_id:
        parent = CommunityComment.query.filter_by(id=parent_id, post_id=post.id, status="published").first()
        if parent is None:
            raise ValueError("回复的评论不存在")
        if parent.parent_id:
            parent = CommunityComment.query.get(parent.parent_id)
    action, hits, reason, warnings = _screen_banned_words(body)
    if action == "reject":
        raise ValueError("内容包含违禁信息，已拒绝发布：" + "、".join(warnings))
    review_state = "pending" if action == "review" else "approved"
    comment = CommunityComment(
        post_id=post.id,
        author_id=user_id,
        parent_id=parent.id if parent else None,
        reply_to_user_id=parent.author_id if parent else None,
        body=body,
        status="hidden" if review_state == "pending" else "published",
    )
    db.session.add(comment)
    db.session.flush()
    if review_state == "pending":
        queue_content_review(
            "comment", comment.id,
            severity=top_severity(hits),
            reason=reason,
        )
        db.session.add(Notification(
            user_id=user_id,
            notification_type="moderation",
            target_type="post",
            target_id=str(post.id),
            summary="你的回复包含敏感词，已提交人工审核",
        ))
    else:
        post.comment_count += 1
        recipient = parent.author_id if parent else post.author_id
        if recipient and recipient != user_id:
            db.session.add(Notification(
                user_id=recipient,
                actor_id=user_id,
                notification_type="reply" if parent else "comment",
                target_type="post",
                target_id=str(post.id),
                summary=f"你的帖子《{post.title[:48]}》有了新回复",
            ))
    record_event(
        user_id,
        "comment",
        entity_type="post",
        entity_id=post.id,
        legal_domain=domain_for_category(post.category.slug),
        commit=False,
    )
    db.session.commit()
    return comment, {"review_state": review_state, "warnings": warnings}


def _draft_serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="community-ai-draft")


def make_ai_post_draft(user_id, conversation_id, message_id=None):
    conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
    if conversation is None:
        raise ValueError("会话不存在或无权访问")
    query = ConversationMessage.query.filter_by(conversation_id=conversation.id, role="user")
    if message_id:
        query = query.filter(ConversationMessage.id <= int(message_id))
    messages = query.order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc()).limit(5).all()
    messages.reverse()
    if not messages:
        raise ValueError("该会话没有可整理的问题")
    source = "\n".join(message.content for message in messages)
    session = RedactionSession()
    safe_source = session.redact(source)[:8000]
    compact = re.sub(r"\s+", " ", safe_source).strip()
    title = compact[:42] + ("…" if len(compact) > 42 else "")
    domain = infer_legal_domain(compact)
    category_slug = {
        "campus": "campus-rights",
        "labor": "internship-jobs",
        "housing": "renting",
        "consumer": "consumer-rights",
        "cyber": "cyber-security",
    }.get(domain, "campus-rights")
    body = f"【事情经过】\n{safe_source}\n\n【我想了解】\n希望了解可行的处理步骤、需要保留的证据，以及应当注意的法律风险。"
    token = _draft_serializer().dumps({
        "user_id": user_id,
        "conversation_id": conversation.id,
        "message_id": int(message_id) if message_id else None,
        "source_hash": hashlib.sha256(safe_source.encode("utf-8")).hexdigest(),
    })
    return {
        "title": title,
        "body": body,
        "category": category_slug,
        "post_type": "legal_help",
        "is_anonymous": True,
        "draft_token": token,
        "privacy_meta": public_redaction_summary(session),
    }


def verify_ai_draft_token(token, user_id):
    try:
        value = _draft_serializer().loads(token, max_age=1800)
    except SignatureExpired as error:
        raise ValueError("求助草稿已过期，请重新生成") from error
    except BadSignature as error:
        raise ValueError("求助草稿凭证无效") from error
    if int(value.get("user_id") or 0) != int(user_id):
        raise ValueError("求助草稿凭证不属于当前用户")
    return value
