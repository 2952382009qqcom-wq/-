"""Add community, verified cases, recommendations and direct chat.

Revision ID: 20260927_community_cases_chat
Revises: None
"""

from alembic import op


revision = "20260927_community_cases_chat"
down_revision = None
branch_labels = None
depends_on = None


NEW_TABLES = (
    "community_categories", "case_categories", "legal_cases", "case_tags",
    "community_posts", "community_comments", "community_post_likes",
    "community_comment_likes", "community_post_favorites", "community_reports",
    "moderation_actions", "community_post_origins", "community_post_case_links",
    "notifications", "legal_case_categories", "legal_case_tags",
    "case_law_references", "case_favorites", "case_relations", "chat_threads",
    "chat_participants", "chat_messages", "user_blocks", "user_activity_events",
    "user_interest_profiles", "recommendation_impressions", "search_index_outbox",
)


def _metadata():
    # The first migration is an additive baseline for this previously
    # create_all-managed project. Imports register the versioned table models.
    from core.models import db
    from core.community import models as community_models  # noqa: F401
    from core.cases import models as case_models  # noqa: F401
    from core.chat import models as chat_models  # noqa: F401
    from core.recommendations import models as recommendation_models  # noqa: F401
    return db.metadata


def upgrade():
    bind = op.get_bind()
    metadata = _metadata()
    for table_name in NEW_TABLES:
        metadata.tables[table_name].create(bind=bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    metadata = _metadata()
    for table_name in reversed(NEW_TABLES):
        metadata.tables[table_name].drop(bind=bind, checkfirst=True)
