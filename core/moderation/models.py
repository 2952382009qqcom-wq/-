"""违禁词库、待审队列与管理员操作日志。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, Index

from core.models import db


class BannedWord(db.Model):
    __tablename__ = "banned_words"
    __table_args__ = (
        CheckConstraint("severity IN ('high', 'medium', 'low')", name="ck_banned_word_severity"),
    )

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(80), unique=True, nullable=False, index=True)
    severity = db.Column(db.String(16), nullable=False, default="low", index=True)
    category = db.Column(db.String(40), nullable=False, default="")
    note = db.Column(db.String(240), nullable=False, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PendingReview(db.Model):
    __tablename__ = "pending_reviews"
    __table_args__ = (
        CheckConstraint("target_type IN ('post', 'comment')", name="ck_pending_review_target"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_pending_review_status"),
        Index("ix_pending_reviews_status_created", "status", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(16), nullable=False, index=True)
    target_id = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(16), nullable=False, default="medium")
    reason = db.Column(db.String(240), nullable=False, default="")
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)


class AdminActionLog(db.Model):
    __tablename__ = "admin_action_logs"
    __table_args__ = (Index("ix_admin_action_logs_created", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_username = db.Column(db.String(80), nullable=False, default="")
    action = db.Column(db.String(48), nullable=False, index=True)
    target_type = db.Column(db.String(32), nullable=False, default="")
    target_id = db.Column(db.String(64), nullable=False, default="")
    detail = db.Column(db.String(500), nullable=False, default="")
    ip = db.Column(db.String(64), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
