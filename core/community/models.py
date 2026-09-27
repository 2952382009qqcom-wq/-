from datetime import datetime

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from core.models import db


class CommunityCategory(db.Model):
    __tablename__ = "community_categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(240), nullable=False, default="")
    icon = db.Column(db.String(16), nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class CommunityPost(db.Model):
    __tablename__ = "community_posts"
    __table_args__ = (
        CheckConstraint("post_type IN ('discussion', 'legal_help')", name="ck_community_post_type"),
        CheckConstraint("status IN ('published', 'hidden', 'deleted')", name="ck_community_post_status"),
        CheckConstraint("help_status IN ('open', 'answered', 'resolved')", name="ck_community_help_status"),
        Index("ix_community_posts_feed", "status", "category_id", "created_at"),
        Index("ix_community_posts_author_created", "author_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("community_categories.id"), nullable=False, index=True)
    post_type = db.Column(db.String(20), nullable=False, default="discussion", index=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, nullable=False, default=False)
    help_status = db.Column(db.String(16), nullable=False, default="open")
    status = db.Column(db.String(16), nullable=False, default="published", index=True)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    comment_count = db.Column(db.Integer, nullable=False, default=0)
    favorite_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship("User", foreign_keys=[author_id])
    category = db.relationship("CommunityCategory")
    comments = db.relationship(
        "CommunityComment",
        backref="post",
        lazy="dynamic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CommunityComment(db.Model):
    __tablename__ = "community_comments"
    __table_args__ = (
        CheckConstraint("status IN ('published', 'hidden', 'deleted')", name="ck_community_comment_status"),
        Index("ix_community_comments_post_created", "post_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    reply_to_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="published", index=True)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship("User", foreign_keys=[author_id])
    reply_to_user = db.relationship("User", foreign_keys=[reply_to_user_id])
    parent = db.relationship("CommunityComment", remote_side=[id], backref="replies")


class CommunityPostLike(db.Model):
    __tablename__ = "community_post_likes"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_community_post_like"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CommunityCommentLike(db.Model):
    __tablename__ = "community_comment_likes"
    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="uq_community_comment_like"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CommunityPostFavorite(db.Model):
    __tablename__ = "community_post_favorites"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_community_post_favorite"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CommunityReport(db.Model):
    __tablename__ = "community_reports"
    __table_args__ = (
        CheckConstraint("target_type IN ('post', 'comment', 'message')", name="ck_community_report_target"),
        CheckConstraint("status IN ('pending', 'resolved', 'dismissed')", name="ck_community_report_status"),
        Index("ix_community_reports_status_created", "status", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = db.Column(db.String(16), nullable=False)
    target_id = db.Column(db.String(64), nullable=False)
    reason = db.Column(db.String(80), nullable=False)
    detail = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(16), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)


class ModerationAction(db.Model):
    __tablename__ = "moderation_actions"

    id = db.Column(db.Integer, primary_key=True)
    moderator_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_type = db.Column(db.String(24), nullable=False)
    target_id = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(32), nullable=False)
    reason = db.Column(db.String(240), nullable=False, default="")
    metadata_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class CommunityPostOrigin(db.Model):
    __tablename__ = "community_post_origins"
    __table_args__ = (UniqueConstraint("post_id", name="uq_community_post_origin"),)

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False)
    source_type = db.Column(db.String(24), nullable=False, default="ai_conversation")
    source_conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    source_message_id = db.Column(db.Integer, db.ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True)
    redaction_summary_json = db.Column(db.Text, nullable=False, default="{}")
    confirmed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CommunityPostCaseLink(db.Model):
    __tablename__ = "community_post_case_links"
    __table_args__ = (UniqueConstraint("post_id", "case_id", name="uq_community_post_case_link"),)

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    relevance_score = db.Column(db.Float, nullable=False, default=0.0)
    reason = db.Column(db.String(240), nullable=False, default="")
    link_source = db.Column(db.String(16), nullable=False, default="algorithm")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notification_type = db.Column(db.String(32), nullable=False)
    target_type = db.Column(db.String(24), nullable=False)
    target_id = db.Column(db.String(64), nullable=False)
    summary = db.Column(db.String(240), nullable=False, default="")
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
