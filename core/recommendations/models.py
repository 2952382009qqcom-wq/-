from datetime import datetime

from sqlalchemy import CheckConstraint, Index

from core.models import db


class UserActivityEvent(db.Model):
    __tablename__ = "user_activity_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('impression', 'click', 'dwell', 'view', 'search', 'favorite', 'unfavorite', 'dismiss', 'open_source', 'related_community_click', 'like', 'post', 'comment', 'consult')",
            name="ck_user_activity_event_type",
        ),
        Index("ix_user_events_user_created", "user_id", "created_at"),
        Index("ix_user_events_user_domain", "user_id", "legal_domain"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(20), nullable=False, index=True)
    entity_type = db.Column(db.String(20), nullable=False, default="")
    entity_id = db.Column(db.String(64), nullable=False, default="")
    legal_domain = db.Column(db.String(40), nullable=False, default="other", index=True)
    weight = db.Column(db.Float, nullable=False, default=1.0)
    safe_metadata_json = db.Column(db.Text, nullable=False, default="{}")
    # Deliberately stores only coarse duration buckets or UI origin; never raw
    # consultation text, chat content, names, addresses or device identifiers.
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class UserInterestProfile(db.Model):
    __tablename__ = "user_interest_profiles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    domain_weights_json = db.Column(db.Text, nullable=False, default="{}")
    profile_version = db.Column(db.String(32), nullable=False, default="hybrid-v1")
    personalization_enabled = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RecommendationImpression(db.Model):
    __tablename__ = "recommendation_impressions"
    __table_args__ = (Index("ix_recommendation_user_created", "user_id", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    reason_codes_json = db.Column(db.Text, nullable=False, default="[]")
    algorithm_version = db.Column(db.String(32), nullable=False, default="layered-v2")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SearchIndexOutbox(db.Model):
    __tablename__ = "search_index_outbox"
    __table_args__ = (Index("ix_search_outbox_pending", "processed_at", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(20), nullable=False)
    entity_id = db.Column(db.String(64), nullable=False)
    operation = db.Column(db.String(16), nullable=False, default="upsert")
    payload_json = db.Column(db.Text, nullable=False, default="{}")
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
