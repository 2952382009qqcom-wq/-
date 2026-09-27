from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from core.extensions import limiter
from core.models import db
from core.recommendations.events import record_event
from core.search.client import search_ids
from core.search.indexing import enqueue_index, process_outbox
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
from .services import create_comment, create_post, make_ai_post_draft, related_cases_for_post


community_bp = Blueprint("community", __name__, url_prefix="/api/community")


def _json():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _post_or_404(post_id, include_hidden=False):
    query = CommunityPost.query.filter_by(id=post_id)
    if not include_hidden:
        query = query.filter_by(status="published")
    return query.first()


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
        return jsonify({"error": str(error)}), 400
    return jsonify({"status": "ok", "post": serialize_post(post, current_user.id), "privacy_meta": privacy_meta}), 201


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
    post = _post_or_404(post_id, include_hidden=True)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    if post.author_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "无权修改该帖子"}), 403
    data = _json()
    if "help_status" in data and post.post_type == "legal_help":
        if data["help_status"] not in {"open", "answered", "resolved"}:
            return jsonify({"error": "求助状态无效"}), 400
        post.help_status = data["help_status"]
    if "title" in data or "body" in data:
        from .services import clean_public_text

        try:
            if "title" in data:
                post.title, _ = clean_public_text(data["title"], max_length=160, field_name="标题")
            if "body" in data:
                post.body, _ = clean_public_text(data["body"], max_length=12000, field_name="正文")
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
    enqueue_index("community_post", post.id, {
        "title": post.title, "body": post.body, "category": post.category.slug,
        "post_type": post.post_type, "status": post.status,
    })
    db.session.commit()
    process_outbox(limit=10)
    return jsonify({"status": "ok", "post": serialize_post(post, current_user.id, detail=True)})


@community_bp.delete("/posts/<int:post_id>")
@login_required
@limiter.limit("20 per hour")
def delete_post(post_id):
    post = _post_or_404(post_id, include_hidden=True)
    if post is None:
        return jsonify({"error": "帖子不存在"}), 404
    if post.author_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "无权删除该帖子"}), 403
    post.status = "deleted"
    enqueue_index("community_post", post.id, operation="delete")
    if current_user.is_admin:
        db.session.add(ModerationAction(
            moderator_id=current_user.id, target_type="post", target_id=str(post.id), action="delete", reason="管理员删除"
        ))
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
        comment = create_comment(current_user.id, post, _json())
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"status": "ok", "comment": serialize_comment(comment, post, current_user.id)}), 201


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
    if target_type not in {"post", "comment", "message"} or not target_id or not reason:
        return jsonify({"error": "举报信息不完整"}), 400
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
    if not current_user.is_admin:
        return jsonify({"error": "需要管理员权限"}), 403
    rows = CommunityReport.query.order_by(CommunityReport.created_at.desc()).limit(100).all()
    return jsonify({"reports": [{
        "id": row.id, "target_type": row.target_type, "target_id": row.target_id,
        "reason": row.reason, "detail": row.detail, "status": row.status,
        "created_at": row.created_at.isoformat(timespec="minutes"),
    } for row in rows]})


@community_bp.post("/moderation/reports/<int:report_id>/resolve")
@login_required
def resolve_report(report_id):
    if not current_user.is_admin:
        return jsonify({"error": "需要管理员权限"}), 403
    report = CommunityReport.query.get(report_id)
    if report is None:
        return jsonify({"error": "举报不存在"}), 404
    data = _json()
    action = data.get("action", "dismiss")
    if action == "hide" and report.target_type == "post" and report.target_id.isdigit():
        target = CommunityPost.query.get(int(report.target_id))
        if target:
            target.status = "hidden"
    elif action == "hide" and report.target_type == "comment" and report.target_id.isdigit():
        target = CommunityComment.query.get(int(report.target_id))
        if target:
            target.status = "hidden"
    report.status = "resolved" if action == "hide" else "dismissed"
    report.resolved_at = datetime.utcnow()
    db.session.add(ModerationAction(
        moderator_id=current_user.id, target_type=report.target_type, target_id=report.target_id,
        action=action, reason=str(data.get("reason") or report.reason)[:240],
    ))
    db.session.commit()
    return jsonify({"status": "ok"})
