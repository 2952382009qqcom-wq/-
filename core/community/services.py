import hashlib
import hashlib
import json
import re
from datetime import datetime

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from core.cases.models import LegalCase
from core.models import Conversation, ConversationMessage, db
from core.privacy import RedactionSession, public_redaction_summary
from core.recommendations.events import record_event
from core.search.indexing import enqueue_index, process_outbox
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
    domain = domain_for_category(post.category.slug)
    excluded = [item.id for item in linked]
    query = LegalCase.query.filter_by(status="published", verification_status="verified", legal_domain=domain)
    if excluded:
        query = query.filter(~LegalCase.id.in_(excluded))
    linked.extend(query.order_by(LegalCase.favorite_count.desc(), LegalCase.view_count.desc()).limit(limit - len(linked)).all())
    return linked


def create_post(user_id, data):
    category = category_or_error(data.get("category"))
    title, title_meta = clean_public_text(data.get("title", ""), max_length=160, field_name="标题")
    body, body_meta = clean_public_text(data.get("body", ""), max_length=12000, field_name="正文")
    post_type = data.get("post_type", "discussion")
    if post_type not in {"discussion", "legal_help"}:
        raise ValueError("帖子类型无效")
    post = CommunityPost(
        author_id=user_id,
        category_id=category.id,
        post_type=post_type,
        title=title,
        body=body,
        is_anonymous=bool(data.get("is_anonymous")),
        help_status="open",
    )
    db.session.add(post)
    db.session.flush()

    draft_token = str(data.get("draft_token") or "")
    if draft_token:
        origin = verify_ai_draft_token(draft_token, user_id)
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
    enqueue_index("community_post", post.id, {
        "title": post.title,
        "body": post.body,
        "category": category.slug,
        "post_type": post.post_type,
        "status": post.status,
    })
    db.session.commit()
    process_outbox(limit=10)
    return post, {"masked_count": title_meta.get("masked_count", 0) + body_meta.get("masked_count", 0)}


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
    comment = CommunityComment(
        post_id=post.id,
        author_id=user_id,
        parent_id=parent.id if parent else None,
        reply_to_user_id=parent.author_id if parent else None,
        body=body,
    )
    post.comment_count += 1
    db.session.add(comment)
    db.session.flush()
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
    return comment


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
