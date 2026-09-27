"""Layered candidate recall. Each layer is bounded and has a safe fallback."""

from collections import OrderedDict
from datetime import datetime, timedelta

from core.cases.models import CaseFavorite, LegalCase
from core.search.client import search_ids

from .models import UserActivityEvent


def _published_query():
    return LegalCase.query.filter_by(status="published", verification_status="verified")


def recall_candidates(user_id, *, domain_weights=None, context_text="", domain="", limit=120):
    """Return unique cases and the recall layers that selected them."""
    domain_weights = domain_weights or {}
    pool = OrderedDict()

    def add(rows, layer):
        for row in rows:
            entry = pool.setdefault(row.id, {"case": row, "layers": []})
            if layer not in entry["layers"]:
                entry["layers"].append(layer)
            if len(pool) >= limit:
                return

    domains = [domain] if domain else []
    domains += [key for key, _ in sorted(domain_weights.items(), key=lambda pair: pair[1], reverse=True)[:3]]
    domains = list(dict.fromkeys(value for value in domains if value and value != "other"))
    if domains:
        add(_published_query().filter(LegalCase.legal_domain.in_(domains)).limit(40).all(), "domain_profile")

    if user_id:
        favorites = LegalCase.query.join(CaseFavorite, CaseFavorite.case_id == LegalCase.id).filter(
            CaseFavorite.user_id == user_id,
            LegalCase.status == "published",
            LegalCase.verification_status == "verified",
        ).limit(20).all()
        favorite_domains = {row.legal_domain for row in favorites}
        if favorite_domains:
            add(_published_query().filter(LegalCase.legal_domain.in_(favorite_domains)).limit(30).all(), "favorite_similar")

        since = datetime.utcnow() - timedelta(days=45)
        event_domains = [row[0] for row in UserActivityEvent.query.with_entities(UserActivityEvent.legal_domain).filter(
            UserActivityEvent.user_id == user_id,
            UserActivityEvent.created_at >= since,
            UserActivityEvent.event_type.in_(("view", "click", "dwell", "related_community_click", "consult")),
        ).distinct().limit(5).all()]
        if event_domains:
            add(_published_query().filter(LegalCase.legal_domain.in_(event_domains)).limit(35).all(), "recent_activity")

    # Keyword recall stays database-safe; Meilisearch remains the primary search API.
    terms = [term for term in str(context_text or "").split() if len(term) >= 2][:5]
    if terms:
        ids = search_ids(
            "legal_cases", " ".join(terms),
            filters="status = published AND verification_status = verified", limit=40,
        )
        if ids is not None:
            integer_ids = [int(value) for value in ids if str(value).isdigit()]
            if integer_ids:
                add(_published_query().filter(LegalCase.id.in_(integer_ids)).all(), "meilisearch_keyword")
        from sqlalchemy import or_
        patterns = []
        for term in terms:
            escaped = term.replace("%", "\\%").replace("_", "\\_")
            patterns.extend((LegalCase.title.ilike(f"%{escaped}%"), LegalCase.keywords.ilike(f"%{escaped}%")))
        add(_published_query().filter(or_(*patterns)).limit(30).all(), "keyword")

    add(_published_query().order_by(LegalCase.favorite_count.desc(), LegalCase.view_count.desc()).limit(30).all(), "popular_fallback")
    add(_published_query().order_by(LegalCase.published_at.desc(), LegalCase.id.desc()).limit(30).all(), "fresh_fallback")
    return list(pool.values())[:limit]
