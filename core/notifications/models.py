import uuid
from datetime import datetime

from sqlalchemy import Index, UniqueConstraint

from core.models import db


class PushDevice(db.Model):
    __tablename__ = "push_devices"
    __table_args__ = (UniqueConstraint("user_id", "token_hash", name="uq_push_device_token"),)

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = db.Column(db.String(16), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, index=True)
    encrypted_token = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    in_app_enabled = db.Column(db.Boolean, nullable=False, default=True)
    push_enabled = db.Column(db.Boolean, nullable=False, default=True)
    generic_lock_screen = db.Column(db.Boolean, nullable=False, default=True)
    quiet_start = db.Column(db.String(5), nullable=True)
    quiet_end = db.Column(db.String(5), nullable=True)
    timezone = db.Column(db.String(40), nullable=False, default="Asia/Shanghai")
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationOutbox(db.Model):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_notification_outbox_idempotency"),
        Index("ix_notification_outbox_pending", "status", "next_attempt_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.String(500), nullable=False)
    route = db.Column(db.String(255), nullable=False, default="/")
    payload_json = db.Column(db.Text, nullable=False, default="{}")
    idempotency_key = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    max_retries = db.Column(db.Integer, nullable=False, default=5)
    next_attempt_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_error = db.Column(db.String(240), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)


class NotificationDelivery(db.Model):
    __tablename__ = "notification_deliveries"
    __table_args__ = (Index("ix_notification_delivery_user_created", "user_id", "created_at"),)

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    outbox_id = db.Column(db.String(36), db.ForeignKey("notification_outbox.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending")
    provider_message_id = db.Column(db.String(160), nullable=False, default="")
    error_code = db.Column(db.String(80), nullable=False, default="")
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime, nullable=True)
