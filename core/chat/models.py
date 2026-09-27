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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)


class ChatParticipant(db.Model):
    __tablename__ = "chat_participants"
    __table_args__ = (UniqueConstraint("thread_id", "user_id", name="uq_chat_participant"),)

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(36), db.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    last_read_message_id = db.Column(db.String(36), nullable=True)
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User")
    thread = db.relationship("ChatThread")


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("status IN ('sent', 'recalled', 'deleted')", name="ck_chat_message_status"),
        Index("ix_chat_messages_thread_created", "thread_id", "created_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    thread_id = db.Column(db.String(36), db.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="sent")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    edited_at = db.Column(db.DateTime, nullable=True)
    recalled_at = db.Column(db.DateTime, nullable=True)

    sender = db.relationship("User")


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
