"""管理员控制台接口：案例库维护、会话（脱敏）审计与系统概览。

用户管理、社区审核与全局模型配置沿用既有接口，不在此重复实现。
"""

import os
import re
import uuid
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_, text

from core.auth import admin_required, user_info
from core.cases.models import (
    CaseCategory,
    CaseFavorite,
    CaseLawReference,
    CaseRelation,
    CaseTag,
    LegalCase,
    LegalCaseCategory,
    LegalCaseTag,
)
from core.cases.serializers import serialize_case_detail
from core.community.models import CommunityComment, CommunityPost, CommunityReport
from core.doc_parser import ocr_available
from core.llm_client import is_demo_mode
from core.models import Conversation, ConversationMessage, User, db
from core.moderation.audit import log_admin_action
from core.moderation.models import AdminActionLog, BannedWord, PendingReview
from core.moderation.words import SEVERITY_CHOICES
from core.taxonomy import CASE_CATEGORIES, DOMAIN_LABELS, classify_case_content


admin_bp = Blueprint("admin_console", __name__, url_prefix="/api/admin")

CASE_STATUSES = ("draft", "published", "hidden")
VERIFICATION_STATUSES = ("pending", "verified", "stale", "rejected")
CASE_SOURCE_TYPES = ("official_court", "official_gazette", "public_database", "manual")
CASE_TEXT_FIELDS = (
    "title", "case_number", "guiding_case_number", "court_name", "case_type", "cause",
    "legal_domain", "summary", "dispute_focus", "judgment_result", "judgment_reasoning",
    "ai_plain_language", "keywords", "source_publisher", "source_type", "source_external_id",
    "source_url", "image_url", "image_alt", "image_source_url", "source_hash",
)
CASE_REQUIRED_FIELDS = (
    "title", "summary", "dispute_focus", "judgment_result", "judgment_reasoning",
    "ai_plain_language", "source_publisher", "source_url",
)
CASE_LIMITS = {
    "title": 320, "case_number": 120, "guiding_case_number": 80, "court_name": 160,
    "case_type": 40, "cause": 160, "legal_domain": 40, "keywords": 500,
    "source_publisher": 160, "source_type": 40, "source_external_id": 160,
    "source_url": 1000, "image_url": 1000, "image_alt": 320, "image_source_url": 1000,
    "source_hash": 64,
}


def _payload():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _text(data, key, limit=None):
    value = data.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    return value[:limit] if limit else value


def _parse_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_datetime(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00").replace("+00:00", ""))
    except ValueError:
        return None


def _slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")


def _unique_case_slug(title):
    base = _slugify(title)
    if base:
        candidate = base[:150]
        if not LegalCase.query.filter_by(slug=candidate).first():
            return candidate
    return f"case-{uuid.uuid4().hex[:12]}"


def _case_list_payload(case):
    return {
        "id": case.id,
        "slug": case.slug,
        "title": case.title,
        "case_number": case.case_number,
        "court_name": case.court_name,
        "case_type": case.case_type,
        "cause": case.cause,
        "legal_domain": case.legal_domain,
        "legal_domain_label": DOMAIN_LABELS.get(case.legal_domain, case.legal_domain),
        "decision_date": case.decision_date.isoformat() if case.decision_date else "",
        "source_type": case.source_type,
        "source_publisher": case.source_publisher,
        "verification_status": case.verification_status,
        "status": case.status,
        "view_count": case.view_count,
        "favorite_count": case.favorite_count,
        "created_at": case.created_at.isoformat(timespec="minutes"),
        "updated_at": case.updated_at.isoformat(timespec="minutes"),
    }


def _apply_text_fields(case, data):
    for field in CASE_TEXT_FIELDS:
        if field not in data:
            continue
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"字段 {field} 必须是文本")
        setattr(case, field, _text(data, field, CASE_LIMITS.get(field)))


def _sync_categories(case, category_slug):
    LegalCaseCategory.query.filter_by(case_id=case.id).delete(synchronize_session=False)
    category = CaseCategory.query.filter_by(slug=category_slug).first() if category_slug else None
    if category is not None:
        db.session.add(LegalCaseCategory(case_id=case.id, category_id=category.id))


def _sync_tags(case, tags):
    LegalCaseTag.query.filter_by(case_id=case.id).delete(synchronize_session=False)
    for raw in tags or []:
        name = str(raw or "").strip()[:60]
        if not name:
            continue
        tag = CaseTag.query.filter_by(name=name).first()
        if tag is None:
            slug = _slugify(name) or f"tag-{uuid.uuid4().hex[:8]}"
            if CaseTag.query.filter_by(slug=slug).first():
                slug = f"{slug}-{uuid.uuid4().hex[:4]}"
            tag = CaseTag(slug=slug, name=name)
            db.session.add(tag)
            db.session.flush()
        db.session.add(LegalCaseTag(case_id=case.id, tag_id=tag.id))


def _sync_law_references(case, references):
    CaseLawReference.query.filter_by(case_id=case.id).delete(synchronize_session=False)
    for ref in references or []:
        if not isinstance(ref, dict):
            continue
        law_name = str(ref.get("law_name") or "").strip()[:200]
        if not law_name:
            continue
        db.session.add(CaseLawReference(
            case_id=case.id,
            law_name=law_name,
            article=str(ref.get("article") or "").strip()[:80],
            note=str(ref.get("note") or "").strip()[:500],
        ))


# ===== 案例库维护 =====

@admin_bp.get("/cases")
@login_required
@admin_required
def list_admin_cases():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 20, type=int), 50))
    query = LegalCase.query
    status = request.args.get("status", "").strip()
    if status in CASE_STATUSES:
        query = query.filter(LegalCase.status == status)
    verification = request.args.get("verification_status", "").strip()
    if verification in VERIFICATION_STATUSES:
        query = query.filter(LegalCase.verification_status == verification)
    domain = request.args.get("legal_domain", "").strip()
    if domain:
        query = query.filter(LegalCase.legal_domain == domain)
    source_type = request.args.get("source_type", "").strip()
    if source_type:
        query = query.filter(LegalCase.source_type == source_type)
    search = request.args.get("q", "").strip()[:120]
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            LegalCase.title.ilike(term),
            LegalCase.case_number.ilike(term),
            LegalCase.summary.ilike(term),
            LegalCase.keywords.ilike(term),
        ))
    pagination = query.order_by(LegalCase.updated_at.desc(), LegalCase.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "cases": [_case_list_payload(case) for case in pagination.items],
        "pagination": {
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
        "filters": {
            "domains": [{"value": key, "label": label} for key, label in DOMAIN_LABELS.items()],
            "categories": [{"slug": slug, "name": name} for slug, name, _ in CASE_CATEGORIES],
            "statuses": list(CASE_STATUSES),
            "verification_statuses": list(VERIFICATION_STATUSES),
            "source_types": list(CASE_SOURCE_TYPES),
        },
    })


@admin_bp.get("/cases/<int:case_id>")
@login_required
@admin_required
def get_admin_case(case_id):
    case = LegalCase.query.get(case_id)
    if case is None:
        return jsonify({"error": "案例不存在"}), 404
    payload = serialize_case_detail(case, None)
    # 详情序列化缺少管理端需要的 status/source_type 等字段，补齐以便编辑表单回填。
    payload.update(_case_list_payload(case))
    payload["category_slug"] = payload["categories"][0]["slug"] if payload["categories"] else ""
    return jsonify({"case": payload})


@admin_bp.post("/cases")
@login_required
@admin_required
def create_admin_case():
    data = _payload()
    missing = [field for field in CASE_REQUIRED_FIELDS if not _text(data, field)]
    if missing:
        return jsonify({"error": "缺少必填字段：" + "、".join(missing)}), 400

    status = _text(data, "status") or "published"
    if status not in CASE_STATUSES:
        return jsonify({"error": "status 取值不合法"}), 400
    verification = _text(data, "verification_status") or "verified"
    if verification not in VERIFICATION_STATUSES:
        return jsonify({"error": "verification_status 取值不合法"}), 400

    try:
        case = LegalCase(
            slug=_unique_case_slug(_text(data, "title")),
            status=status,
            verification_status=verification,
            source_type=_text(data, "source_type", 40) or "official_court",
            case_type=_text(data, "case_type", 40) or "民事",
            decision_date=_parse_date(data.get("decision_date")),
            published_at=_parse_datetime(data.get("published_at")) or datetime.utcnow(),
            source_checked_at=_parse_datetime(data.get("source_checked_at")) or datetime.utcnow(),
            created_by=current_user.id,
        )
        _apply_text_fields(case, data)
        if not case.source_type:
            case.source_type = "official_court"
        if not case.case_type:
            case.case_type = "民事"
        category_slug = _text(data, "category_slug")
        if not case.legal_domain or not category_slug:
            inferred_slug, inferred_domain = classify_case_content(
                title=case.title, cause=case.cause, keywords=case.keywords,
                dispute_focus=case.dispute_focus, case_type=case.case_type,
            )
            case.legal_domain = case.legal_domain or inferred_domain
            category_slug = category_slug or inferred_slug
        case.legal_domain = case.legal_domain or "civil"
        db.session.add(case)
        db.session.flush()
        _sync_categories(case, category_slug)
        _sync_tags(case, data.get("tags") if isinstance(data.get("tags"), list) else [])
        _sync_law_references(
            case, data.get("law_references") if isinstance(data.get("law_references"), list) else []
        )
        log_admin_action("case_create", target_type="case", target_id=str(case.id), detail=case.title)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 400
    return jsonify({"status": "ok", "message": "案例已创建", "id": case.id})


@admin_bp.put("/cases/<int:case_id>")
@login_required
@admin_required
def update_admin_case(case_id):
    case = LegalCase.query.get(case_id)
    if case is None:
        return jsonify({"error": "案例不存在"}), 404
    data = _payload()

    status = _text(data, "status")
    if status and status not in CASE_STATUSES:
        return jsonify({"error": "status 取值不合法"}), 400
    verification = _text(data, "verification_status")
    if verification and verification not in VERIFICATION_STATUSES:
        return jsonify({"error": "verification_status 取值不合法"}), 400

    try:
        _apply_text_fields(case, data)
        if status:
            case.status = status
        if verification:
            case.verification_status = verification
        if "decision_date" in data:
            case.decision_date = _parse_date(data.get("decision_date"))
        if "published_at" in data:
            case.published_at = _parse_datetime(data.get("published_at")) or case.published_at
        if "source_checked_at" in data:
            case.source_checked_at = _parse_datetime(data.get("source_checked_at")) or case.source_checked_at
        if not case.title:
            raise ValueError("标题不能为空")
        if "category_slug" in data:
            _sync_categories(case, _text(data, "category_slug"))
        if isinstance(data.get("tags"), list):
            _sync_tags(case, data.get("tags"))
        if isinstance(data.get("law_references"), list):
            _sync_law_references(case, data.get("law_references"))
        log_admin_action("case_update", target_type="case", target_id=str(case.id), detail=case.title)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 400
    return jsonify({"status": "ok", "message": "案例已更新"})


@admin_bp.delete("/cases/<int:case_id>")
@login_required
@admin_required
def delete_admin_case(case_id):
    case = LegalCase.query.get(case_id)
    if case is None:
        return jsonify({"error": "案例不存在"}), 404
    LegalCaseCategory.query.filter_by(case_id=case.id).delete(synchronize_session=False)
    LegalCaseTag.query.filter_by(case_id=case.id).delete(synchronize_session=False)
    CaseLawReference.query.filter_by(case_id=case.id).delete(synchronize_session=False)
    CaseFavorite.query.filter_by(case_id=case.id).delete(synchronize_session=False)
    CaseRelation.query.filter(
        (CaseRelation.case_id == case.id) | (CaseRelation.related_case_id == case.id)
    ).delete(synchronize_session=False)
    log_admin_action("case_delete", target_type="case", target_id=str(case.id), detail=case.title)
    db.session.delete(case)
    db.session.commit()
    return jsonify({"status": "ok", "message": "案例已删除"})


# ===== 会话审计（仅脱敏数据） =====

@admin_bp.get("/audit/conversations")
@login_required
@admin_required
def audit_conversations():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 20, type=int), 50))
    query = Conversation.query.join(User, Conversation.user_id == User.id)
    user_id = request.args.get("user_id", type=int)
    if user_id:
        query = query.filter(Conversation.user_id == user_id)
    search = request.args.get("q", "").strip()[:120]
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Conversation.title.ilike(term), User.username.ilike(term)))
    pagination = query.order_by(Conversation.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    ids = [row.id for row in pagination.items]
    counts = {}
    if ids:
        counts = dict(
            db.session.query(ConversationMessage.conversation_id, func.count(ConversationMessage.id))
            .filter(ConversationMessage.conversation_id.in_(ids))
            .group_by(ConversationMessage.conversation_id)
            .all()
        )
    return jsonify({
        "conversations": [{
            "id": row.id,
            "username": row.user.username if row.user else "已注销用户",
            "user_id": row.user_id,
            "title": row.title,
            "message_count": int(counts.get(row.id, 0)),
            "created_at": row.created_at.isoformat(timespec="minutes"),
            "updated_at": row.updated_at.isoformat(timespec="minutes"),
        } for row in pagination.items],
        "pagination": {
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
    })


@admin_bp.get("/audit/conversations/<conversation_id>")
@login_required
@admin_required
def audit_conversation_detail(conversation_id):
    conversation = Conversation.query.get(conversation_id)
    if conversation is None:
        return jsonify({"error": "会话不存在"}), 404
    messages = (
        ConversationMessage.query
        .filter_by(conversation_id=conversation.id)
        .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
        .limit(200)
        .all()
    )
    return jsonify({
        "conversation": {
            "id": conversation.id,
            "username": conversation.user.username if conversation.user else "已注销用户",
            "user_id": conversation.user_id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(timespec="minutes"),
            "updated_at": conversation.updated_at.isoformat(timespec="minutes"),
        },
        "messages": [{
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "created_at": row.created_at.isoformat(timespec="minutes"),
        } for row in messages],
        "redacted": True,
        "note": "内容为入库前的脱敏结果，不含原始手机号、身份证、邮箱等个人标识。",
    })


# ===== 系统概览 =====

@admin_bp.get("/system")
@login_required
@admin_required
def system_overview():
    components = {"database": False, "external_model": not is_demo_mode(), "ocr": ocr_available()}
    try:
        db.session.execute(text("SELECT 1"))
        components["database"] = True
    except Exception:
        db.session.rollback()
    return jsonify({
        "version": os.getenv("APP_VERSION", "2026.09-legal-agent"),
        "demo_mode": is_demo_mode(),
        "components": components,
        "counts": {
            "users": User.query.count(),
            "admins": User.query.filter_by(is_admin=True).count(),
            "cases": LegalCase.query.count(),
            "published_cases": LegalCase.query.filter_by(status="published", verification_status="verified").count(),
            "posts": CommunityPost.query.count(),
            "comments": CommunityComment.query.count(),
            "conversations": Conversation.query.count(),
            "messages": ConversationMessage.query.count(),
        },
    })


# ===== 数据概览 =====

def _pagination_payload(pagination):
    return {
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


@admin_bp.get("/dashboard")
@login_required
@admin_required
def admin_dashboard():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=6)
    series = []
    for offset in range(7):
        day_start = week_start + timedelta(days=offset)
        day_end = day_start + timedelta(days=1)
        series.append({
            "date": day_start.date().isoformat(),
            "users": User.query.filter(User.created_at >= day_start, User.created_at < day_end).count(),
            "posts": CommunityPost.query.filter(
                CommunityPost.created_at >= day_start, CommunityPost.created_at < day_end
            ).count(),
        })
    return jsonify({
        "users": {
            "total": User.query.count(),
            "approved": User.query.filter_by(is_approved=True, is_admin=False).count(),
            "pending": User.query.filter_by(approval_requested=True, is_approved=False, is_admin=False).count(),
        },
        "today_posts": CommunityPost.query.filter(CommunityPost.created_at >= today).count(),
        "pending_reports": CommunityReport.query.filter_by(status="pending").count(),
        "pending_reviews": PendingReview.query.filter_by(status="pending").count(),
        "posts_total": CommunityPost.query.count(),
        "comments_total": CommunityComment.query.count(),
        "series": series,
    })


# ===== 用户管理（搜索/筛选/分页） =====

USER_STATUSES = ("all", "approved", "pending", "inactive")


@admin_bp.get("/users")
@login_required
@admin_required
def admin_users():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 20, type=int), 50))
    query = User.query.filter_by(is_admin=False)
    status = request.args.get("status", "all").strip()
    if status == "approved":
        query = query.filter_by(is_approved=True)
    elif status == "pending":
        query = query.filter_by(approval_requested=True, is_approved=False)
    elif status == "inactive":
        query = query.filter_by(is_approved=False, approval_requested=False)
    search = request.args.get("q", "").strip()[:80]
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "users": [user_info(row) for row in pagination.items],
        "pagination": _pagination_payload(pagination),
        "statuses": list(USER_STATUSES),
    })


@admin_bp.post("/reset-quota/<int:user_id>")
@login_required
@admin_required
def reset_user_quota(user_id):
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"error": "用户不存在"}), 404
    user.free_api_used = 0
    log_admin_action("user_reset_quota", target_type="user", target_id=str(user.id), detail=f"重置 {user.username} 额度")
    db.session.commit()
    return jsonify({"status": "ok", "message": f"已重置 {user.username} 的免费额度", "user": user_info(user)})


# ===== 内容审核队列 =====

def _review_target_preview(row):
    empty = {"exists": False, "title": "", "body": "", "author": ""}
    if not row.target_id.isdigit():
        return empty
    target_id = int(row.target_id)
    if row.target_type == "post":
        target = CommunityPost.query.get(target_id)
        if target is None:
            return empty
        return {
            "exists": True,
            "title": target.title,
            "body": target.body,
            "author": target.author.username if target.author else "已注销用户",
        }
    if row.target_type == "comment":
        target = CommunityComment.query.get(target_id)
        if target is None:
            return empty
        return {
            "exists": True,
            "title": f"帖子《{target.post.title}》中的回复",
            "body": target.body,
            "author": target.author.username if target.author else "已注销用户",
        }
    return empty


@admin_bp.get("/review/queue")
@login_required
@admin_required
def review_queue():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 20, type=int), 50))
    pagination = (
        PendingReview.query.filter_by(status="pending")
        .order_by(PendingReview.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    items = []
    for row in pagination.items:
        payload = {
            "id": row.id,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "severity": row.severity,
            "reason": row.reason,
            "created_at": row.created_at.isoformat(timespec="minutes"),
        }
        payload.update(_review_target_preview(row))
        items.append(payload)
    return jsonify({"items": items, "pagination": _pagination_payload(pagination)})


@admin_bp.post("/review/<string:target_type>/<int:target_id>")
@login_required
@admin_required
def review_decision(target_type, target_id):
    if target_type not in {"post", "comment"}:
        return jsonify({"error": "不支持的内容类型"}), 400
    action = _text(_payload(), "action")
    status_for_action = {"approve": "published", "reject": "hidden", "delete": "deleted"}
    if action not in status_for_action:
        return jsonify({"error": "不支持的处理方式"}), 400
    target = CommunityPost.query.get(target_id) if target_type == "post" else CommunityComment.query.get(target_id)
    if target is None:
        return jsonify({"error": "内容不存在"}), 404

    previous_status = target.status
    target.status = status_for_action[action]
    if target_type == "comment" and action == "approve" and previous_status != "published":
        target.post.comment_count += 1
    PendingReview.query.filter_by(
        target_type=target_type, target_id=str(target_id), status="pending"
    ).update(
        {
            "status": "approved" if action == "approve" else "rejected",
            "resolved_by": current_user.id,
            "resolved_at": datetime.utcnow(),
        },
        synchronize_session=False,
    )
    log_admin_action(f"review_{action}", target_type=target_type, target_id=str(target_id))
    db.session.commit()
    if target_type == "post" and action == "approve":
        from core.search.indexing import enqueue_index, process_outbox

        enqueue_index("community_post", target.id, {
            "title": target.title,
            "body": target.body,
            "category": target.category.slug,
            "post_type": target.post_type,
            "status": target.status,
        })
        db.session.commit()
        process_outbox(limit=10)
    return jsonify({"status": "ok", "content_status": target.status})


# ===== 操作日志 =====

@admin_bp.get("/logs")
@login_required
@admin_required
def admin_logs():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 20, type=int), 50))
    query = AdminActionLog.query
    action = request.args.get("action", "").strip()[:48]
    if action:
        query = query.filter(AdminActionLog.action == action)
    search = request.args.get("q", "").strip()[:80]
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            AdminActionLog.actor_username.ilike(term),
            AdminActionLog.action.ilike(term),
            AdminActionLog.detail.ilike(term),
        ))
    pagination = query.order_by(AdminActionLog.created_at.desc(), AdminActionLog.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "logs": [{
            "id": row.id,
            "actor_username": row.actor_username or "系统",
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "detail": row.detail,
            "ip": row.ip,
            "created_at": row.created_at.isoformat(timespec="minutes"),
        } for row in pagination.items],
        "pagination": _pagination_payload(pagination),
    })


# ===== 违禁词库 =====

def _banned_word_payload(row):
    return {
        "id": row.id,
        "word": row.word,
        "severity": row.severity,
        "category": row.category,
        "note": row.note,
        "is_active": row.is_active,
        "updated_at": row.updated_at.isoformat(timespec="minutes"),
    }


@admin_bp.get("/banned-words")
@login_required
@admin_required
def list_banned_words():
    query = BannedWord.query
    search = request.args.get("q", "").strip()[:80]
    if search:
        query = query.filter(BannedWord.word.ilike(f"%{search}%"))
    severity = request.args.get("severity", "").strip()
    if severity in SEVERITY_CHOICES:
        query = query.filter(BannedWord.severity == severity)
    rows = query.order_by(BannedWord.severity.asc(), BannedWord.id.desc()).all()
    return jsonify({"words": [_banned_word_payload(row) for row in rows], "severities": list(SEVERITY_CHOICES)})


@admin_bp.post("/banned-words")
@login_required
@admin_required
def create_banned_word():
    data = _payload()
    word = _text(data, "word", 80)
    severity = _text(data, "severity") or "low"
    if not word:
        return jsonify({"error": "违禁词不能为空"}), 400
    if severity not in SEVERITY_CHOICES:
        return jsonify({"error": "等级取值不合法"}), 400
    if BannedWord.query.filter(func.lower(BannedWord.word) == word.lower()).first():
        return jsonify({"error": "该违禁词已存在"}), 400
    row = BannedWord(
        word=word,
        severity=severity,
        category=_text(data, "category", 40),
        note=_text(data, "note", 240),
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(row)
    log_admin_action("banned_word_create", target_type="banned_word", target_id=word, detail=f"{word}（{severity}）")
    db.session.commit()
    return jsonify({"status": "ok", "message": "已添加违禁词", "word": _banned_word_payload(row)})


@admin_bp.put("/banned-words/<int:word_id>")
@login_required
@admin_required
def update_banned_word(word_id):
    row = BannedWord.query.get(word_id)
    if row is None:
        return jsonify({"error": "违禁词不存在"}), 404
    data = _payload()
    if "severity" in data:
        severity = _text(data, "severity")
        if severity not in SEVERITY_CHOICES:
            return jsonify({"error": "等级取值不合法"}), 400
        row.severity = severity
    if "category" in data:
        row.category = _text(data, "category", 40)
    if "note" in data:
        row.note = _text(data, "note", 240)
    if "is_active" in data:
        row.is_active = bool(data.get("is_active"))
    log_admin_action("banned_word_update", target_type="banned_word", target_id=str(row.id), detail=f"{row.word}（{row.severity}）")
    db.session.commit()
    return jsonify({"status": "ok", "message": "已更新违禁词", "word": _banned_word_payload(row)})


@admin_bp.delete("/banned-words/<int:word_id>")
@login_required
@admin_required
def delete_banned_word(word_id):
    row = BannedWord.query.get(word_id)
    if row is None:
        return jsonify({"error": "违禁词不存在"}), 404
    log_admin_action("banned_word_delete", target_type="banned_word", target_id=str(row.id), detail=row.word)
    db.session.delete(row)
    db.session.commit()
    return jsonify({"status": "ok", "message": "已删除违禁词"})
