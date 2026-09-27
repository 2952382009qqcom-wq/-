import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from core.models import db


def new_uuid():
    return str(uuid.uuid4())


class ChatThread(db.Model):
    __tablename__ = "chat_threads"
    __table_args__ = (UniqueConstraint("pair_key", name="uq_chat_direct_pair"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    thread_type = db.Column(db.String(16), nullable=False, default="direct")
    pair_key = db.Column(db.String(64), nullable=False, index=True)
    next_sequence = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)


class ChatParticipant(db.Model):
    __tablename__ = "chat_participants"
    __table_args__ = (UniqueConstraint("thread_id", "user_id", name="uq_chat_participant"),)

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(36), db.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    last_read_message_id = db.Column(db.String(36), nullable=True)
    last_read_sequence = db.Column(db.Integer, nullable=False, default=0)
    muted_until = db.Column(db.DateTime, nullable=True)
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User")
    thread = db.relationship("ChatThread")


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("status IN ('sent', 'delivered', 'recalled', 'deleted', 'moderated')", name="ck_chat_message_status"),
        CheckConstraint("message_type IN ('text', 'image', 'attachment', 'system')", name="ck_chat_message_type"),
        UniqueConstraint("thread_id", "sequence", name="uq_chat_message_sequence"),
        UniqueConstraint("sender_id", "client_message_id", name="uq_chat_sender_client_message"),
        Index("ix_chat_messages_thread_created", "thread_id", "created_at"),
        Index("ix_chat_messages_thread_sequence", "thread_id", "sequence"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    thread_id = db.Column(db.String(36), db.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    client_message_id = db.Column(db.String(64), nullable=True)
    sequence = db.Column(db.Integer, nullable=False, default=0)
    message_type = db.Column(db.String(16), nullable=False, default="text")
    reply_to_id = db.Column(db.String(36), db.ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="sent")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    edited_at = db.Column(db.DateTime, nullable=True)
    recalled_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    moderation_reason = db.Column(db.String(240), nullable=False, default="")

    sender = db.relationship("User")
    reply_to = db.relationship("ChatMessage", remote_side=[id], uselist=False)


class ChatAttachment(db.Model):
    __tablename__ = "chat_attachments"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    message_id = db.Column(db.String(36), db.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key = db.Column(db.String(255), nullable=False, unique=True)
    original_name = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(120), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ChatMessageHidden(db.Model):
    __tablename__ = "chat_message_hidden"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_chat_message_hidden"),)

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(36), db.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ChatReport(db.Model):
    __tablename__ = "chat_reports"

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(36), db.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = db.Column(db.String(240), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ChatAuditLog(db.Model):
    __tablename__ = "chat_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(40), nullable=False, index=True)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.String(64), nullable=False)
    metadata_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class ChatUserSanction(db.Model):
    __tablename__ = "chat_user_sanctions"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    muted_until = db.Column(db.DateTime, nullable=True)
    banned_at = db.Column(db.DateTime, nullable=True)
    reason = db.Column(db.String(240), nullable=False, default="")
    moderator_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserBlock(db.Model):
    __tablename__ = "user_blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),
        CheckConstraint("blocker_id <> blocked_id", name="ck_user_block_self"),
    )

    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
