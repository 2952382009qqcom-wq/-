from .models import CaseFavorite, CaseLawReference, CaseTag, LegalCaseCategory, LegalCaseTag


SOURCE_TYPE_LABELS = {
    "official_court": "最高人民法院公开案例",
    "official_court_guiding": "最高人民法院指导性案例",
    "official_court_gazette": "《最高人民法院公报》案例",
    "official_court_typical": "最高人民法院典型案例",
}

LEGACY_LAW_NOTES = {
    "最高人民法院指导性案例列明的关联法条",
    "原裁判文书法院说理中提及；可能适用历史版本，请核对现行法律",
}


def _case_categories(case_id):
    from .models import CaseCategory

    return [
        {"id": row.id, "slug": row.slug, "name": row.name}
        for row in CaseCategory.query.join(LegalCaseCategory, LegalCaseCategory.category_id == CaseCategory.id)
        .filter(LegalCaseCategory.case_id == case_id)
        .order_by(CaseCategory.sort_order.asc())
        .all()
    ]


def _case_tags(case_id):
    return [
        row.name
        for row in CaseTag.query.join(LegalCaseTag, LegalCaseTag.tag_id == CaseTag.id)
        .filter(LegalCaseTag.case_id == case_id)
        .order_by(CaseTag.name.asc())
        .all()
    ]


def serialize_case_card(case, user_id=None, *, recommendation=None):
    favorited = bool(user_id and CaseFavorite.query.filter_by(user_id=user_id, case_id=case.id).first())
    categories = _case_categories(case.id)
    payload = {
        "id": case.id,
        "slug": case.slug,
        "title": case.title,
        "case_number": case.case_number,
        "guiding_case_number": case.guiding_case_number,
        "court_name": case.court_name,
        "cause": case.cause,
        "case_type": case.case_type,
        "legal_domain": case.legal_domain,
        "decision_date": case.decision_date.isoformat() if case.decision_date else "",
        "summary": case.summary[:240] + ("…" if len(case.summary) > 240 else ""),
        "keywords": [item.strip() for item in case.keywords.split(",") if item.strip()],
        "categories": categories,
        "media": {
            "image_url": case.image_url,
            "image_alt": case.image_alt,
            "image_source_url": case.image_source_url,
        },
        "verification_status": case.verification_status,
        "view_count": case.view_count,
        "favorite_count": case.favorite_count,
        "favorited": favorited,
    }
    if recommendation:
        payload["recommendation"] = recommendation
    return payload


def serialize_case_detail(case, user_id=None, *, related_cases=None, discussions=None):
    payload = serialize_case_card(case, user_id)
    payload.update({
        "summary": case.summary,
        "dispute_focus": case.dispute_focus,
        "judgment_result": case.judgment_result,
        "judgment_reasoning": case.judgment_reasoning,
        "ai_plain_language": case.ai_plain_language,
        "tags": _case_tags(case.id),
        "source": {
            "publisher": case.source_publisher,
            "type": case.source_type,
            "type_label": SOURCE_TYPE_LABELS.get(case.source_type, "法院公开案例"),
            "external_id": case.source_external_id,
            "url": case.source_url,
            "checked_at": case.source_checked_at.isoformat(timespec="minutes") if case.source_checked_at else "",
            "hash": case.source_hash,
        },
        "law_references": [
            {"law_name": row.law_name, "article": row.article, "note": "" if row.note in LEGACY_LAW_NOTES else row.note}
            for row in CaseLawReference.query.filter_by(case_id=case.id).all()
            if row.article and row.article.strip()
        ],
        "related_cases": [serialize_case_card(item, user_id) for item in (related_cases or [])],
        "community_discussions": discussions or [],
    })
    return payload
