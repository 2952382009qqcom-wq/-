import uuid
from datetime import datetime

from sqlalchemy import Index, UniqueConstraint

from core.models import db


class ConversationSummary(db.Model):
    __tablename__ = "conversation_summaries"
    __table_args__ = (UniqueConstraint("conversation_id", "source_start_message_id", "source_end_message_id", name="uq_summary_source_range"),)

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    summary = db.Column(db.Text, nullable=False)
    source_start_message_id = db.Column(db.Integer, nullable=False)
    source_end_message_id = db.Column(db.Integer, nullable=False)
    conflicts_json = db.Column(db.Text, nullable=False, default="[]")
    version = db.Column(db.String(24), nullable=False, default="extractive-v1")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class UserMemorySetting(db.Model):
    __tablename__ = "user_memory_settings"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserMemoryItem(db.Model):
    __tablename__ = "user_memory_items"
    __table_args__ = (Index("ix_memory_user_domain_active", "user_id", "legal_domain", "deleted_at"),)

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_type = db.Column(db.String(24), nullable=False)
    legal_domain = db.Column(db.String(40), nullable=False, default="other")
    content = db.Column(db.Text, nullable=False)
    source_conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    source_message_id = db.Column(db.Integer, db.ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True)
    confidence = db.Column(db.Float, nullable=False, default=1.0)
    reason = db.Column(db.String(240), nullable=False, default="用户主动保存")
    confirmed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class UserMemoryEmbedding(db.Model):
    __tablename__ = "user_memory_embeddings"

    id = db.Column(db.Integer, primary_key=True)
    memory_id = db.Column(db.String(36), db.ForeignKey("user_memory_items.id", ondelete="CASCADE"), nullable=False, unique=True)
    model = db.Column(db.String(80), nullable=False)
    vector_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class UserMemoryAudit(db.Model):
    __tablename__ = "user_memory_audit"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_id = db.Column(db.String(36), nullable=True, index=True)
    action = db.Column(db.String(24), nullable=False)
    reason = db.Column(db.String(240), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
