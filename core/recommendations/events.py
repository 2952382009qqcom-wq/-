import json
from collections import defaultdict
from datetime import datetime, timedelta

from core.models import db
from core.taxonomy import infer_legal_domain

from .config import EVENT_WEIGHTS
from .models import RecommendationImpression, UserActivityEvent, UserInterestProfile


SAFE_METADATA_KEYS = {"duration_bucket", "origin", "position", "query_terms_count"}


def record_event(
    user_id,
    event_type,
    *,
    entity_type="",
    entity_id="",
    legal_domain="other",
    safe_metadata=None,
    commit=True,
):
    if not user_id or event_type not in EVENT_WEIGHTS:
        return None
    profile = UserInterestProfile.query.filter_by(user_id=int(user_id)).first()
    if profile is not None and not profile.personalization_enabled:
        return None
    domain = legal_domain or "other"
    if domain == "other" and safe_metadata:
        domain = infer_legal_domain(" ".join(map(str, safe_metadata.values())))
    safe_values = {
        key: value for key, value in (safe_metadata or {}).items()
        if key in SAFE_METADATA_KEYS and isinstance(value, (str, int, float, bool))
    }
    event = UserActivityEvent(
        user_id=int(user_id),
        event_type=event_type,
        entity_type=str(entity_type or "")[:20],
        entity_id=str(entity_id or "")[:64],
        legal_domain=domain[:40],
        weight=EVENT_WEIGHTS[event_type],
        safe_metadata_json=json.dumps(safe_values, ensure_ascii=False),
    )
    db.session.add(event)
    if commit:
        db.session.commit()
    return event


def domain_weights_for_user(user_id, days=180):
    profile = UserInterestProfile.query.filter_by(user_id=user_id).first()
    if profile and not profile.personalization_enabled:
        return {}
    since = datetime.utcnow() - timedelta(days=max(7, min(int(days), 365)))
    rows = UserActivityEvent.query.filter(
        UserActivityEvent.user_id == user_id,
        UserActivityEvent.created_at >= since,
    ).all()
    values = defaultdict(float)
    now = datetime.utcnow()
    for row in rows:
        age_days = max(0, (now - row.created_at).days)
        decay = 0.5 ** (age_days / 90)
        values[row.legal_domain or "other"] += float(row.weight or 0) * decay
    positive = {key: max(0.0, value) for key, value in values.items() if value > 0}
    total = sum(positive.values()) or 1.0
    normalized = {key: round(value / total, 4) for key, value in positive.items()}
    if profile is None:
        profile = UserInterestProfile(user_id=user_id)
        db.session.add(profile)
    profile.domain_weights_json = json.dumps(normalized, ensure_ascii=False)
    db.session.commit()
    return normalized


def set_personalization(user_id, enabled):
    profile = UserInterestProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        profile = UserInterestProfile(user_id=user_id)
        db.session.add(profile)
    profile.personalization_enabled = bool(enabled)
    if not enabled:
        profile.domain_weights_json = "{}"
        UserActivityEvent.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        RecommendationImpression.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.commit()
    return profile
