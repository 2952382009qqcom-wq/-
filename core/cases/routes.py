from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from core.extensions import limiter
from core.models import db
from core.recommendations.events import record_event, set_personalization
from core.recommendations.models import UserInterestProfile
from core.recommendations.ranking import recommend_cases
from core.recommendations.config import ALGORITHM_VERSION, COMPATIBILITY_ALIAS
from core.search.client import search_ids
from core.taxonomy import safe_search_terms

from .models import CaseCategory, CaseFavorite, LegalCase, LegalCaseCategory
from .serializers import serialize_case_card, serialize_case_detail
from .services import related_cases, related_discussions


cases_bp = Blueprint("cases", __name__, url_prefix="/api/cases")


@cases_bp.get("/categories")
@login_required
def categories():
    rows = CaseCategory.query.filter_by(is_active=True).order_by(CaseCategory.sort_order.asc()).all()
    return jsonify({"categories": [
        {"id": row.id, "slug": row.slug, "name": row.name, "description": row.description}
        for row in rows
    ]})


@cases_bp.get("")
@login_required
@limiter.limit("90 per minute")
def list_cases():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 12, type=int), 30))
    query = LegalCase.query.filter_by(status="published", verification_status="verified")
    category = request.args.get("category", "").strip()
    if category:
        query = query.join(LegalCaseCategory, LegalCaseCategory.case_id == LegalCase.id).join(
            CaseCategory, CaseCategory.id == LegalCaseCategory.category_id
        ).filter(CaseCategory.slug == category)
    feed = request.args.get("feed", "latest").strip()
    if feed == "favorites":
        query = query.join(CaseFavorite, CaseFavorite.case_id == LegalCase.id).filter(CaseFavorite.user_id == current_user.id)
    search = request.args.get("q", "").strip()[:120]
    if search:
        ids = search_ids("legal_cases", search, filters="status = published AND verification_status = verified", limit=100)
        if ids is not None:
            integer_ids = [int(value) for value in ids if value.isdigit()]
            query = query.filter(LegalCase.id.in_(integer_ids or [-1]))
        else:
            term = f"%{search}%"
            query = query.filter(or_(
                LegalCase.title.ilike(term), LegalCase.summary.ilike(term), LegalCase.dispute_focus.ilike(term),
                LegalCase.judgment_reasoning.ilike(term), LegalCase.keywords.ilike(term), LegalCase.case_number.ilike(term),
            ))
        for domain in safe_search_terms(search) or ["other"]:
            record_event(current_user.id, "search", entity_type="case", legal_domain=domain, commit=False)
        db.session.commit()
    if feed == "popular":
        query = query.order_by(LegalCase.favorite_count.desc(), LegalCase.view_count.desc())
    else:
        query = query.order_by(LegalCase.published_at.desc(), LegalCase.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "cases": [serialize_case_card(row, current_user.id) for row in pagination.items],
        "pagination": {"page": page, "pages": pagination.pages, "total": pagination.total, "has_next": pagination.has_next},
    })


@cases_bp.get("/recommendations")
@login_required
@limiter.limit("30 per minute")
def recommendations():
    profile = UserInterestProfile.query.filter_by(user_id=current_user.id).first()
    if profile is not None and not profile.personalization_enabled:
        return jsonify({"cases": [], "algorithm": COMPATIBILITY_ALIAS, "algorithm_version": ALGORITHM_VERSION, "personalization_enabled": False})
    ranked = recommend_cases(
        current_user.id,
        request.args.get("limit", 8, type=int),
        context_text=request.args.get("q", "")[:120],
        domain=request.args.get("domain", "")[:40],
    )
    return jsonify({"cases": [
        serialize_case_card(case, current_user.id, recommendation={"score": score, "reasons": reasons})
        for case, score, reasons in ranked
    ], "algorithm": COMPATIBILITY_ALIAS, "algorithm_version": ALGORITHM_VERSION, "personalization_enabled": True})


@cases_bp.post("/<int:case_id>/events")
@login_required
@limiter.limit("120 per minute")
def case_event(case_id):
    case = LegalCase.query.filter_by(id=case_id, status="published", verification_status="verified").first()
    if case is None:
        return jsonify({"error": "案例不存在"}), 404
    data = request.get_json(silent=True) or {}
    event_type = str(data.get("event_type", ""))
    if event_type not in {"impression", "click", "dwell", "dismiss", "open_source", "related_community_click"}:
        return jsonify({"error": "不支持的事件类型"}), 400
    event = record_event(
        current_user.id, event_type, entity_type="case", entity_id=case.id,
        legal_domain=case.legal_domain, safe_metadata=data.get("metadata"),
    )
    return jsonify({"status": "ok", "recorded": event is not None})


@cases_bp.get("/<int:case_id>")
@login_required
@limiter.limit("120 per minute")
def case_detail(case_id):
    case = LegalCase.query.filter_by(id=case_id, status="published", verification_status="verified").first()
    if case is None:
        return jsonify({"error": "案例不存在或尚未完成核验"}), 404
    case.view_count += 1
    record_event(
        current_user.id, "view", entity_type="case", entity_id=case.id,
        legal_domain=case.legal_domain, commit=False,
    )
    db.session.commit()
    return jsonify({"case": serialize_case_detail(
        case,
        current_user.id,
        related_cases=related_cases(case),
        discussions=related_discussions(case, current_user.id),
    )})


@cases_bp.post("/<int:case_id>/favorite")
@login_required
@limiter.limit("60 per minute")
def toggle_favorite(case_id):
    case = LegalCase.query.filter_by(id=case_id, status="published", verification_status="verified").first()
    if case is None:
        return jsonify({"error": "案例不存在"}), 404
    row = CaseFavorite.query.filter_by(user_id=current_user.id, case_id=case.id).first()
    favorited = row is None
    if favorited:
        db.session.add(CaseFavorite(user_id=current_user.id, case_id=case.id))
        case.favorite_count += 1
        record_event(current_user.id, "favorite", entity_type="case", entity_id=case.id, legal_domain=case.legal_domain, commit=False)
    else:
        db.session.delete(row)
        case.favorite_count = max(0, case.favorite_count - 1)
        record_event(current_user.id, "unfavorite", entity_type="case", entity_id=case.id, legal_domain=case.legal_domain, commit=False)
    db.session.commit()
    return jsonify({"status": "ok", "favorited": favorited, "favorite_count": case.favorite_count})


@cases_bp.put("/personalization")
@login_required
def personalization():
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get("enabled"))
    set_personalization(current_user.id, enabled)
    return jsonify({"status": "ok", "enabled": enabled})


@cases_bp.get("/personalization")
@login_required
def personalization_status():
    profile = UserInterestProfile.query.filter_by(user_id=current_user.id).first()
    return jsonify({"enabled": profile is None or profile.personalization_enabled})
