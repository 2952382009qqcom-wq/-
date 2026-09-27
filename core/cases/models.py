from datetime import datetime

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from core.models import db


class CaseCategory(db.Model):
    __tablename__ = "case_categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), nullable=False, unique=True, index=True)
    name = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(240), nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class LegalCase(db.Model):
    __tablename__ = "legal_cases"
    __table_args__ = (
        CheckConstraint("verification_status IN ('pending', 'verified', 'stale', 'rejected')", name="ck_legal_case_verification"),
        CheckConstraint("status IN ('draft', 'published', 'hidden')", name="ck_legal_case_status"),
        Index("ix_legal_cases_public", "verification_status", "status", "decision_date"),
        Index("ix_legal_cases_domain", "legal_domain", "case_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    title = db.Column(db.String(320), nullable=False)
    case_number = db.Column(db.String(120), nullable=False, default="", index=True)
    guiding_case_number = db.Column(db.String(80), nullable=False, default="", index=True)
    court_name = db.Column(db.String(160), nullable=False, default="")
    case_type = db.Column(db.String(40), nullable=False, default="民事")
    cause = db.Column(db.String(160), nullable=False, default="", index=True)
    legal_domain = db.Column(db.String(40), nullable=False, default="other", index=True)
    decision_date = db.Column(db.Date, nullable=True, index=True)
    published_at = db.Column(db.DateTime, nullable=True)
    summary = db.Column(db.Text, nullable=False)
    dispute_focus = db.Column(db.Text, nullable=False)
    judgment_result = db.Column(db.Text, nullable=False)
    judgment_reasoning = db.Column(db.Text, nullable=False)
    ai_plain_language = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.String(500), nullable=False, default="")
    source_publisher = db.Column(db.String(160), nullable=False)
    source_type = db.Column(db.String(40), nullable=False, default="official_court")
    source_external_id = db.Column(db.String(160), nullable=False, default="", index=True)
    source_url = db.Column(db.String(1000), nullable=False)
    image_url = db.Column(db.String(1000), nullable=False, default="")
    image_alt = db.Column(db.String(320), nullable=False, default="")
    image_source_url = db.Column(db.String(1000), nullable=False, default="")
    source_hash = db.Column(db.String(64), nullable=False, default="")
    source_checked_at = db.Column(db.DateTime, nullable=True)
    verification_status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    status = db.Column(db.String(16), nullable=False, default="draft", index=True)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    favorite_count = db.Column(db.Integer, nullable=False, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class CaseTag(db.Model):
    __tablename__ = "case_tags"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), nullable=False, unique=True)
    name = db.Column(db.String(60), nullable=False, unique=True)


class LegalCaseCategory(db.Model):
    __tablename__ = "legal_case_categories"
    __table_args__ = (UniqueConstraint("case_id", "category_id", name="uq_legal_case_category"),)

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("case_categories.id", ondelete="CASCADE"), nullable=False, index=True)


class LegalCaseTag(db.Model):
    __tablename__ = "legal_case_tags"
    __table_args__ = (UniqueConstraint("case_id", "tag_id", name="uq_legal_case_tag"),)

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("case_tags.id", ondelete="CASCADE"), nullable=False, index=True)


class CaseLawReference(db.Model):
    __tablename__ = "case_law_references"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    law_name = db.Column(db.String(200), nullable=False)
    article = db.Column(db.String(80), nullable=False, default="")
    note = db.Column(db.String(500), nullable=False, default="")


class CaseFavorite(db.Model):
    __tablename__ = "case_favorites"
    __table_args__ = (UniqueConstraint("user_id", "case_id", name="uq_case_favorite"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CaseRelation(db.Model):
    __tablename__ = "case_relations"
    __table_args__ = (UniqueConstraint("case_id", "related_case_id", name="uq_case_relation"),)

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    related_case_id = db.Column(db.Integer, db.ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    relevance_score = db.Column(db.Float, nullable=False, default=0.0)
    reason = db.Column(db.String(240), nullable=False, default="")
    algorithm_version = db.Column(db.String(32), nullable=False, default="content-v1")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
