from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import case, or_

from core.extensions import limiter
from core.models import User, db
from core.moderation.actions import apply_content_status
from core.moderation.audit import log_admin_action
from core.moderation.models import PendingReview
from core.recommendations.events import record_event
from core.search.client import search_ids
from core.search.indexing import process_outbox
from core.taxonomy import domain_for_category, safe_search_terms

from .models import (
    CommunityCategory,
    CommunityComment,
    CommunityCommentLike,
    CommunityPost,
    CommunityPostFavorite,
    CommunityPostLike,
    CommunityReport,
    ModerationAction,
    Notification,
)
from .serializers import serialize_comment, serialize_post
from .services import create_comment, create_post, make_ai_post_draft, related_cases_for_post, update_post


community_bp = Blueprint("community", __name__, url_prefix="/api/community")


def _json():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _post_or_404(post_id, include_hidden=False, *, for_update=False):
    query = CommunityPost.query.filter_by(id=post_id)
    if not include_hidden:
        query = query.filter_by(status="published")
    if for_update:
        query = query.with_for_update()
    return query.first()


def _admin_guard():
    if not current_user.is_admin:
        return jsonify({"error": "需要管理员权限"}), 403
    return None


def _audit_author(author):
    if author is None:
        return {"id": None, "username": "已注销用户"}
    return {"id": author.id, "username": author.username}


def _moderation_post_payload(post, *, detail=False):
    payload = {
        "id": post.id,
        "title": post.title,
        "body": post.body if detail else post.body[:240] + ("…" if len(post.body) > 240 else ""),
        "post_type": post.post_type,
        "help_status": post.help_status,
        "is_anonymous": post.is_anonymous,
        "status": post.status,
        "category": {"slug": post.category.slug, "name": post.category.name},
        "author_account": _audit_author(post.author),
        "counts": {
            "views": post.view_count,
            "likes": post.like_count,
            "comments": post.comment_count,
            "favorites": post.favorite_count,
        },
        "created_at": post.created_at.isoformat(timespec="minutes"),
        "updated_at": post.updated_at.isoformat(timespec="minutes"),
        "review": _content_review_payload("post", post.id),
    }
    return payload


def _moderation_comment_payload(comment):
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "parent_id": comment.parent_id,
        "body": comment.body,
        "status": comment.status,
        "like_count": comment.like_count,
        "author_account": _audit_author(comment.author),
        "created_at": comment.created_at.isoformat(timespec="minutes"),
        "review": _content_review_payload("comment", comment.id),
    }


def _content_review_payload(target_type, target_id):
    review = PendingReview.query.filter_by(
        target_type=target_type, target_id=str(target_id)
    ).order_by(PendingReview.id.desc()).first()
    if review is None:
        return None
    return {
        "id": review.id, "status": review.status,
        "severity": review.severity, "reason": review.reason,
        "resolved_by_id": review.resolved_by,
        "resolved_at": review.resolved_at.isoformat(timespec="seconds") if review.resolved_at else "",
    }


def _report_target_payload(report):
    if not report.target_id.isdigit():
        return {"exists": False, "summary": f"{report.target_type} #{report.target_id}"}
    target_id = int(report.target_id)
    if report.target_type == "post":
        target = CommunityPost.query.get(target_id)
        if target:
            return {
                "exists": True,
                "status": target.status,
                "summary": target.title,
                "preview": target.body[:160],
                "author_account": _audit_author(target.author),
                "is_anonymous": target.is_anonymous,
            }
    elif report.target_type == "comment":
        target = CommunityComment.query.get(target_id)
        if target:
            return {
                "exists": True,
                "status": target.status,
                "summary": f"帖子《{target.post.title}》中的回复",
                "preview": target.body[:160],
                "author_account": _audit_author(target.author),
                "is_anonymous": bool(target.post.is_anonymous and target.author_id == target.post.author_id),
            }
    return {"exists": False, "summary": f"{report.target_type} #{report.target_id}"}


def _moderation_report_payload(report):
    reporter = User.query.get(report.reporter_id)
    resolver = User.query.get(report.resolved_by) if report.resolved_by else None
    return {
        "id": report.id,
        "target_type": report.target_type,
        "target_id": report.target_id,
        "reason": report.reason,
        "detail": report.detail,
        "status": report.status,
        "reporter": _audit_author(reporter),
        "resolved_by": resolver.username if resolver else "",
        "resolved_by_id": report.resolved_by,
        "target": _report_target_payload(report),
        "created_at": report.created_at.isoformat(timespec="minutes"),
        "resolved_at": report.resolved_at.isoformat(timespec="minutes") if report.resolved_at else "",
    }


def _apply_moderation_action(target_type, target_id, action):
    status_for_action = {"hide": "hidden", "restore": "published", "delete": "deleted"}
    next_status = status_for_action.get(action)
    if next_status is None:
        raise ValueError("不支持的管理操作")
    if target_type == "post":
        target = CommunityPost.query.filter_by(id=target_id).with_for_update().first()
    elif target_type == "comment":
        target = CommunityComment.query.filter_by(id=target_id).with_for_update().first()
    else:
        raise ValueError("不支持的内容类型")
    if target is None:
        return None

    return apply_content_status(
        target_type, target, next_status, reviewer_id=current_user.id, resolve_reviews=True
    )


@community_bp.get("/categories")
@login_required
def categories():
    rows = CommunityCategory.query.filter_by(is_active=True).order_by(CommunityCategory.sort_order.asc()).all()
    return jsonify({"categories": [
        {"id": row.id, "slug": row.slug, "name": row.name, "description": row.description, "icon": row.icon}
        for row in rows
    ]})


@community_bp.get("/posts")
@login_required
@limiter.limit("90 per minute")
def posts():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 12, type=int), 30))
    query = CommunityPost.query.filter_by(status="published")
    category = request.args.get("category", "").strip()
    if category:
        query = query.join(CommunityCategory).filter(CommunityCategory.slug == category)
    post_type = request.args.get("type", "").strip()
    if post_type in {"discussion", "legal_help"}:
        query = query.filter(CommunityPost.post_type == post_type)
    feed = request.args.get("feed", "latest").strip()
    if feed == "favorites":
        query = query.join(CommunityPostFavorite).filter(CommunityPostFavorite.user_id == current_user.id)
    elif feed == "resolved":
        query = query.filter(CommunityPost.post_type == "legal_help", CommunityPost.help_status == "resolved")

    search = request.args.get("q", "").strip()[:120]
    if search:
        ids = search_ids("community_posts", search, filters="status = published", limit=100)
        if ids is not None:
            integer_ids = [int(value) for value in ids if value.isdigit()]
            query = query.filter(CommunityPost.id.in_(integer_ids or [-1]))
        else:
            term = f"%{search}%"
            query = query.filter(or_(CommunityPost.title.ilike(term), CommunityPost.body.ilike(term)))
        terms = safe_search_terms(search)
        for domain in terms or ["other"]:
            record_event(current_user.id, "search", entity_type="community", legal_domain=domain, commit=False)
        db.session.commit()

    if feed == "popular":
        query = query.order_by(CommunityPost.like_count.desc(), CommunityPost.comment_count.desc(), CommunityPost.created_at.desc())
    else:
        query = query.order_by(CommunityPost.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "posts": [serialize_post(row, current_user.id) for row in pagination.items],
        "pagination": {"page": page, "pages": pagination.pages, "total": pagination.total, "has_next": pagination.has_next},
    })


@community_bp.post("/posts")
@login_required
@limiter.limit("8 per hour")
def add_post():
    try:
        post, privacy_meta = create_post(current_user.id, _json())
    except ValueError as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 400
    return jsonify({
        "status": "ok",
        "post": serialize_post(post, current_user.id),
        "privacy_meta": privacy_meta,
        "review_state": privacy_meta.get("review_state", "approved"),
        "warnings": privacy_meta.get("warnings", []),
    }), 201


@community_bp.get("/posts/<int:post_id>")
@login_required
@limiter.limit("120 per minute")
def post_detail(post_id):
    post = _post_or_404(post_id)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    post.view_count += 1
    record_event(
        current_user.id,
        "view",
        entity_type="post",
        entity_id=post.id,
        legal_domain=domain_for_category(post.category.slug),
        commit=False,
    )
    db.session.commit()
    comments = CommunityComment.query.filter_by(post_id=post.id, status="published").order_by(CommunityComment.created_at.asc()).all()
    return jsonify({
        "post": serialize_post(post, current_user.id, detail=True, related_cases=related_cases_for_post(post)),
        "comments": [serialize_comment(row, post, current_user.id) for row in comments],
    })


@community_bp.patch("/posts/<int:post_id>")
@login_required
@limiter.limit("20 per hour")
def edit_post(post_id):
    post = _post_or_404(post_id, include_hidden=True, for_update=True)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    if post.author_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "无权修改该帖子"}), 403
    try:
        if current_user.is_admin:
            log_admin_action("community_edit", target_type="post", target_id=str(post.id), detail="管理员修改帖子")
        post, privacy_meta = update_post(post, _json())
    except ValueError as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 400
    return jsonify({
        "status": "ok", "post": serialize_post(post, current_user.id, detail=True),
        "privacy_meta": privacy_meta, "review_state": privacy_meta["review_state"],
        "warnings": privacy_meta["warnings"],
    })


@community_bp.delete("/posts/<int:post_id>")
@login_required
@limiter.limit("20 per hour")
def delete_post(post_id):
    post = _post_or_404(post_id, include_hidden=True, for_update=True)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    if post.author_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "无权删除该帖子"}), 403
    apply_content_status(
        "post", post, "deleted",
        reviewer_id=current_user.id if current_user.is_admin else None,
        resolve_reviews=True,
    )
    if current_user.is_admin:
        db.session.add(ModerationAction(
            moderator_id=current_user.id, target_type="post", target_id=str(post.id), action="delete", reason="管理员删除"
        ))
        log_admin_action("community_moderate", target_type="post", target_id=str(post.id), detail="delete：管理员删除")
    db.session.commit()
    process_outbox(limit=10)
    return jsonify({"status": "ok"})


@community_bp.post("/posts/<int:post_id>/like")
@login_required
@limiter.limit("60 per minute")
def toggle_post_like(post_id):
    post = _post_or_404(post_id)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    row = CommunityPostLike.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    liked = row is None
    if liked:
        db.session.add(CommunityPostLike(user_id=current_user.id, post_id=post.id))
        post.like_count += 1
        record_event(current_user.id, "like", entity_type="post", entity_id=post.id, legal_domain=domain_for_category(post.category.slug), commit=False)
    else:
        db.session.delete(row)
        post.like_count = max(0, post.like_count - 1)
    db.session.commit()
    return jsonify({"status": "ok", "liked": liked, "like_count": post.like_count})


@community_bp.post("/posts/<int:post_id>/favorite")
@login_required
@limiter.limit("60 per minute")
def toggle_post_favorite(post_id):
    post = _post_or_404(post_id)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    row = CommunityPostFavorite.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    favorited = row is None
    if favorited:
        db.session.add(CommunityPostFavorite(user_id=current_user.id, post_id=post.id))
        post.favorite_count += 1
        record_event(current_user.id, "favorite", entity_type="post", entity_id=post.id, legal_domain=domain_for_category(post.category.slug), commit=False)
    else:
        db.session.delete(row)
        post.favorite_count = max(0, post.favorite_count - 1)
        record_event(current_user.id, "unfavorite", entity_type="post", entity_id=post.id, legal_domain=domain_for_category(post.category.slug), commit=False)
    db.session.commit()
    return jsonify({"status": "ok", "favorited": favorited, "favorite_count": post.favorite_count})


@community_bp.post("/posts/<int:post_id>/comments")
@login_required
@limiter.limit("30 per hour")
def add_comment(post_id):
    post = _post_or_404(post_id)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    try:
        comment, meta = create_comment(current_user.id, post, _json())
    except ValueError as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 400
    return jsonify({
        "status": "ok",
        "comment": serialize_comment(comment, post, current_user.id),
        "review_state": meta.get("review_state", "approved"),
        "warnings": meta.get("warnings", []),
    }), 201


@community_bp.post("/comments/<int:comment_id>/like")
@login_required
@limiter.limit("60 per minute")
def toggle_comment_like(comment_id):
    comment = CommunityComment.query.filter_by(id=comment_id, status="published").first()
    if comment is None:
        return jsonify({"error": "评论不存在"}), 404
    row = CommunityCommentLike.query.filter_by(user_id=current_user.id, comment_id=comment.id).first()
    liked = row is None
    if liked:
        db.session.add(CommunityCommentLike(user_id=current_user.id, comment_id=comment.id))
        comment.like_count += 1
    else:
        db.session.delete(row)
        comment.like_count = max(0, comment.like_count - 1)
    db.session.commit()
    return jsonify({"status": "ok", "liked": liked, "like_count": comment.like_count})


@community_bp.post("/reports")
@login_required
@limiter.limit("12 per hour")
def report_content():
    data = _json()
    target_type = data.get("target_type")
    target_id = str(data.get("target_id") or "")[:64]
    reason = str(data.get("reason") or "").strip()[:80]
    if not isinstance(target_type, str) or target_type not in {"post", "comment", "message"} or not target_id or not reason:
        return jsonify({"error": "举报信息不完整"}), 400
    if target_type in {"post", "comment"}:
        if not target_id.isascii() or not target_id.isdigit() or int(target_id) > 2147483647:
            return jsonify({"error": "被举报内容不存在"}), 404
        target_id = str(int(target_id))
        if target_type == "post":
            target = _post_or_404(int(target_id))
        else:
            target = CommunityComment.query.filter_by(id=int(target_id), status="published").first()
            if target is not None and target.post.status != "published":
                target = None
        if target is None:
            return jsonify({"error": "被举报内容不存在"}), 404
    db.session.add(CommunityReport(
        reporter_id=current_user.id, target_type=target_type, target_id=target_id, reason=reason,
        detail=str(data.get("detail") or "").strip()[:1000],
    ))
    db.session.commit()
    return jsonify({"status": "ok", "message": "举报已提交"}), 201


@community_bp.post("/ai-draft")
@login_required
@limiter.limit("10 per hour")
def ai_post_draft():
    data = _json()
    conversation_id = data.get("conversation_id")
    if not isinstance(conversation_id, str) or not conversation_id:
        return jsonify({"error": "请选择需要整理的 AI 会话"}), 400
    try:
        draft = make_ai_post_draft(current_user.id, conversation_id, data.get("message_id"))
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"status": "preview", "draft": draft})


@community_bp.get("/notifications")
@login_required
def notifications():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(40).all()
    return jsonify({"notifications": [{
        "id": row.id, "type": row.notification_type, "target_type": row.target_type,
        "target_id": row.target_id, "summary": row.summary, "is_read": row.is_read,
        "created_at": row.created_at.isoformat(timespec="minutes"),
    } for row in rows]})


@community_bp.post("/notifications/read")
@login_required
def read_notifications():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"status": "ok"})


@community_bp.get("/moderation/reports")
@login_required
def moderation_reports():
    denied = _admin_guard()
    if denied:
        return denied
    rows = CommunityReport.query.order_by(CommunityReport.created_at.desc()).limit(100).all()
    return jsonify({"reports": [_moderation_report_payload(row) for row in rows]})


@community_bp.get("/moderation/overview")
@login_required
def moderation_overview():
    denied = _admin_guard()
    if denied:
        return denied

    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 30, type=int), 50))
    status = request.args.get("status", "all").strip()
    query = CommunityPost.query
    if status in {"published", "hidden", "deleted"}:
        query = query.filter(CommunityPost.status == status)
    search = request.args.get("q", "").strip()[:120]
    if search:
        term = f"%{search}%"
        query = query.outerjoin(User, CommunityPost.author_id == User.id).filter(or_(
            CommunityPost.title.ilike(term),
            CommunityPost.body.ilike(term),
            User.username.ilike(term),
        ))
    pagination = query.order_by(CommunityPost.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    reports = CommunityReport.query.order_by(
        case((CommunityReport.status == "pending", 0), else_=1),
        CommunityReport.created_at.desc(),
    ).limit(50).all()
    return jsonify({
        "metrics": {
            "posts": CommunityPost.query.count(),
            "published_posts": CommunityPost.query.filter_by(status="published").count(),
            "hidden_posts": CommunityPost.query.filter_by(status="hidden").count(),
            "comments": CommunityComment.query.count(),
            "pending_reports": CommunityReport.query.filter_by(status="pending").count(),
        },
        "posts": [_moderation_post_payload(row) for row in pagination.items],
        "reports": [_moderation_report_payload(row) for row in reports],
        "pagination": {
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
    })


@community_bp.get("/moderation/posts/<int:post_id>")
@login_required
def moderation_post_detail(post_id):
    denied = _admin_guard()
    if denied:
        return denied
    post = CommunityPost.query.get(post_id)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    comments = CommunityComment.query.filter_by(post_id=post.id).order_by(CommunityComment.created_at.asc()).all()
    return jsonify({
        "post": _moderation_post_payload(post, detail=True),
        "comments": [_moderation_comment_payload(row) for row in comments],
    })


@community_bp.post("/moderation/content/<string:target_type>/<int:target_id>")
@login_required
def moderate_content(target_type, target_id):
    denied = _admin_guard()
    if denied:
        return denied
    data = _json()
    action = str(data.get("action") or "").strip()
    reason = str(data.get("reason") or "管理员处理")[:240]
    try:
        target = _apply_moderation_action(target_type, target_id, action)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    if target is None:
        return jsonify({"error": "内容不存在"}), 404
    db.session.add(ModerationAction(
        moderator_id=current_user.id,
        target_type=target_type,
        target_id=str(target_id),
        action=action,
        reason=reason,
    ))
    if action in {"hide", "delete"}:
        CommunityReport.query.filter_by(
            target_type=target_type, target_id=str(target_id), status="pending"
        ).update(
            {"status": "resolved", "resolved_at": datetime.utcnow(), "resolved_by": current_user.id},
            synchronize_session=False,
        )
    log_admin_action("community_moderate", target_type=target_type, target_id=str(target_id), detail=f"{action}：{reason}")
    db.session.commit()
    if target_type == "post":
        process_outbox(limit=10)
    return jsonify({"status": "ok", "content_status": target.status})


@community_bp.post("/moderation/reports/<int:report_id>/resolve")
@login_required
def resolve_report(report_id):
    denied = _admin_guard()
    if denied:
        return denied
    report = CommunityReport.query.get(report_id)
    if report is None:
        return jsonify({"error": "举报不存在"}), 404
    if report.status != "pending":
        return jsonify({"error": "举报已处理，请刷新列表"}), 409
    data = _json()
    action = data.get("action", "dismiss")
    if not isinstance(action, str) or action not in {"dismiss", "hide", "delete"}:
        return jsonify({"error": "不支持的举报处理方式"}), 400
    if action != "dismiss":
        if report.target_type not in {"post", "comment"} or not report.target_id.isdigit():
            return jsonify({"error": "该举报类型暂不支持直接处理"}), 400
        target = _apply_moderation_action(report.target_type, int(report.target_id), action)
        if target is None:
            return jsonify({"error": "被举报内容不存在"}), 404
    # Claim the still-pending report after locking/changing its target so a
    # concurrent handler cannot overwrite the original decision or audit trail.
    claimed = CommunityReport.query.filter_by(id=report.id, status="pending").update({
        "status": "dismissed" if action == "dismiss" else "resolved",
        "resolved_at": datetime.utcnow(), "resolved_by": current_user.id,
    }, synchronize_session=False)
    if claimed != 1:
        db.session.rollback()
        return jsonify({"error": "举报已处理，请刷新列表"}), 409
    db.session.add(ModerationAction(
        moderator_id=current_user.id, target_type=report.target_type, target_id=report.target_id,
        action=action, reason=str(data.get("reason") or report.reason)[:240],
    ))
    log_admin_action("report_resolve", target_type=report.target_type, target_id=report.target_id, detail=f"{action}：举报 #{report.id}")
    db.session.commit()
    if report.target_type == "post" and action != "dismiss":
        process_outbox(limit=10)
    return jsonify({"status": "ok"})
