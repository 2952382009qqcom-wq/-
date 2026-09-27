"""Frozen additive schema for community, cases, recommendations, chat and platform foundations.

Revision ID: 20260927_community_cases_chat
Revises: None

This file is a static Alembic snapshot.  It deliberately does not import
application models or runtime SQLAlchemy metadata.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260927_community_cases_chat"
down_revision = None
branch_labels = None
depends_on = None


CREATED_TABLES = [
    'case_categories',
    'case_tags',
    'chat_threads',
    'community_categories',
    'search_index_outbox',
    'chat_audit_logs',
    'chat_messages',
    'chat_participants',
    'chat_user_sanctions',
    'community_posts',
    'community_reports',
    'legal_cases',
    'moderation_actions',
    'notification_outbox',
    'notification_preferences',
    'notifications',
    'push_devices',
    'user_activity_events',
    'user_blocks',
    'user_interest_profiles',
    'user_memory_audit',
    'user_memory_settings',
    'case_favorites',
    'case_law_references',
    'case_relations',
    'chat_attachments',
    'chat_message_hidden',
    'chat_reports',
    'community_comments',
    'community_post_case_links',
    'community_post_favorites',
    'community_post_likes',
    'conversation_summaries',
    'legal_case_categories',
    'legal_case_tags',
    'notification_deliveries',
    'recommendation_impressions',
    'community_comment_likes',
    'community_post_origins',
    'user_memory_items',
    'user_memory_embeddings'
]


def upgrade():
    op.create_table('case_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=40), nullable=False),
    sa.Column('description', sa.String(length=240), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_categories_slug'), 'case_categories', ['slug'], unique=True)
    op.create_table('case_tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('name', sa.String(length=60), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('chat_threads',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('thread_type', sa.String(length=16), nullable=False),
    sa.Column('pair_key', sa.String(length=64), nullable=False),
    sa.Column('next_sequence', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('pair_key', name='uq_chat_direct_pair')
    )
    op.create_index(op.f('ix_chat_threads_pair_key'), 'chat_threads', ['pair_key'], unique=False)
    op.create_index(op.f('ix_chat_threads_updated_at'), 'chat_threads', ['updated_at'], unique=False)
    op.create_table('community_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=40), nullable=False),
    sa.Column('description', sa.String(length=240), nullable=False),
    sa.Column('icon', sa.String(length=16), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_categories_slug'), 'community_categories', ['slug'], unique=True)
    op.create_table('search_index_outbox',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entity_type', sa.String(length=20), nullable=False),
    sa.Column('entity_id', sa.String(length=64), nullable=False),
    sa.Column('operation', sa.String(length=16), nullable=False),
    sa.Column('payload_json', sa.Text(), nullable=False),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('processed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_outbox_pending', 'search_index_outbox', ['processed_at', 'created_at'], unique=False)
    op.create_table('chat_audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=40), nullable=False),
    sa.Column('target_type', sa.String(length=20), nullable=False),
    sa.Column('target_id', sa.String(length=64), nullable=False),
    sa.Column('metadata_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_audit_logs_action'), 'chat_audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_chat_audit_logs_actor_id'), 'chat_audit_logs', ['actor_id'], unique=False)
    op.create_index(op.f('ix_chat_audit_logs_created_at'), 'chat_audit_logs', ['created_at'], unique=False)
    op.create_table('chat_messages',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('thread_id', sa.String(length=36), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=True),
    sa.Column('client_message_id', sa.String(length=64), nullable=True),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('message_type', sa.String(length=16), nullable=False),
    sa.Column('reply_to_id', sa.String(length=36), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('edited_at', sa.DateTime(), nullable=True),
    sa.Column('recalled_at', sa.DateTime(), nullable=True),
    sa.Column('delivered_at', sa.DateTime(), nullable=True),
    sa.Column('moderation_reason', sa.String(length=240), nullable=False),
    sa.CheckConstraint("message_type IN ('text', 'image', 'attachment', 'system')", name='ck_chat_message_type'),
    sa.CheckConstraint("status IN ('sent', 'delivered', 'recalled', 'deleted', 'moderated')", name='ck_chat_message_status'),
    sa.ForeignKeyConstraint(['reply_to_id'], ['chat_messages.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sender_id', 'client_message_id', name='uq_chat_sender_client_message'),
    sa.UniqueConstraint('thread_id', 'sequence', name='uq_chat_message_sequence')
    )
    op.create_index(op.f('ix_chat_messages_created_at'), 'chat_messages', ['created_at'], unique=False)
    op.create_index(op.f('ix_chat_messages_sender_id'), 'chat_messages', ['sender_id'], unique=False)
    op.create_index('ix_chat_messages_thread_created', 'chat_messages', ['thread_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_chat_messages_thread_id'), 'chat_messages', ['thread_id'], unique=False)
    op.create_index('ix_chat_messages_thread_sequence', 'chat_messages', ['thread_id', 'sequence'], unique=False)
    op.create_table('chat_participants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('thread_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('last_read_message_id', sa.String(length=36), nullable=True),
    sa.Column('last_read_sequence', sa.Integer(), nullable=False),
    sa.Column('muted_until', sa.DateTime(), nullable=True),
    sa.Column('joined_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('thread_id', 'user_id', name='uq_chat_participant')
    )
    op.create_index(op.f('ix_chat_participants_thread_id'), 'chat_participants', ['thread_id'], unique=False)
    op.create_index(op.f('ix_chat_participants_user_id'), 'chat_participants', ['user_id'], unique=False)
    op.create_table('chat_user_sanctions',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('muted_until', sa.DateTime(), nullable=True),
    sa.Column('banned_at', sa.DateTime(), nullable=True),
    sa.Column('reason', sa.String(length=240), nullable=False),
    sa.Column('moderator_id', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['moderator_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('community_posts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.Column('post_type', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('is_anonymous', sa.Boolean(), nullable=False),
    sa.Column('help_status', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('view_count', sa.Integer(), nullable=False),
    sa.Column('like_count', sa.Integer(), nullable=False),
    sa.Column('comment_count', sa.Integer(), nullable=False),
    sa.Column('favorite_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("help_status IN ('open', 'answered', 'resolved')", name='ck_community_help_status'),
    sa.CheckConstraint("post_type IN ('discussion', 'legal_help')", name='ck_community_post_type'),
    sa.CheckConstraint("status IN ('published', 'hidden', 'deleted')", name='ck_community_post_status'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['category_id'], ['community_categories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_community_posts_author_created', 'community_posts', ['author_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_community_posts_author_id'), 'community_posts', ['author_id'], unique=False)
    op.create_index(op.f('ix_community_posts_category_id'), 'community_posts', ['category_id'], unique=False)
    op.create_index(op.f('ix_community_posts_created_at'), 'community_posts', ['created_at'], unique=False)
    op.create_index('ix_community_posts_feed', 'community_posts', ['status', 'category_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_community_posts_post_type'), 'community_posts', ['post_type'], unique=False)
    op.create_index(op.f('ix_community_posts_status'), 'community_posts', ['status'], unique=False)
    op.create_table('community_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reporter_id', sa.Integer(), nullable=False),
    sa.Column('target_type', sa.String(length=16), nullable=False),
    sa.Column('target_id', sa.String(length=64), nullable=False),
    sa.Column('reason', sa.String(length=80), nullable=False),
    sa.Column('detail', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("status IN ('pending', 'resolved', 'dismissed')", name='ck_community_report_status'),
    sa.CheckConstraint("target_type IN ('post', 'comment', 'message')", name='ck_community_report_target'),
    sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_reports_reporter_id'), 'community_reports', ['reporter_id'], unique=False)
    op.create_index('ix_community_reports_status_created', 'community_reports', ['status', 'created_at'], unique=False)
    op.create_table('legal_cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=180), nullable=False),
    sa.Column('title', sa.String(length=320), nullable=False),
    sa.Column('case_number', sa.String(length=120), nullable=False),
    sa.Column('guiding_case_number', sa.String(length=80), nullable=False),
    sa.Column('court_name', sa.String(length=160), nullable=False),
    sa.Column('case_type', sa.String(length=40), nullable=False),
    sa.Column('cause', sa.String(length=160), nullable=False),
    sa.Column('legal_domain', sa.String(length=40), nullable=False),
    sa.Column('decision_date', sa.Date(), nullable=True),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('dispute_focus', sa.Text(), nullable=False),
    sa.Column('judgment_result', sa.Text(), nullable=False),
    sa.Column('judgment_reasoning', sa.Text(), nullable=False),
    sa.Column('ai_plain_language', sa.Text(), nullable=False),
    sa.Column('keywords', sa.String(length=500), nullable=False),
    sa.Column('source_publisher', sa.String(length=160), nullable=False),
    sa.Column('source_type', sa.String(length=40), nullable=False),
    sa.Column('source_external_id', sa.String(length=160), nullable=False),
    sa.Column('source_url', sa.String(length=1000), nullable=False),
    sa.Column('source_hash', sa.String(length=64), nullable=False),
    sa.Column('source_checked_at', sa.DateTime(), nullable=True),
    sa.Column('verification_status', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('view_count', sa.Integer(), nullable=False),
    sa.Column('favorite_count', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'published', 'hidden')", name='ck_legal_case_status'),
    sa.CheckConstraint("verification_status IN ('pending', 'verified', 'stale', 'rejected')", name='ck_legal_case_verification'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_legal_cases_case_number'), 'legal_cases', ['case_number'], unique=False)
    op.create_index(op.f('ix_legal_cases_cause'), 'legal_cases', ['cause'], unique=False)
    op.create_index(op.f('ix_legal_cases_decision_date'), 'legal_cases', ['decision_date'], unique=False)
    op.create_index('ix_legal_cases_domain', 'legal_cases', ['legal_domain', 'case_type'], unique=False)
    op.create_index(op.f('ix_legal_cases_guiding_case_number'), 'legal_cases', ['guiding_case_number'], unique=False)
    op.create_index(op.f('ix_legal_cases_legal_domain'), 'legal_cases', ['legal_domain'], unique=False)
    op.create_index('ix_legal_cases_public', 'legal_cases', ['verification_status', 'status', 'decision_date'], unique=False)
    op.create_index(op.f('ix_legal_cases_slug'), 'legal_cases', ['slug'], unique=True)
    op.create_index(op.f('ix_legal_cases_source_external_id'), 'legal_cases', ['source_external_id'], unique=False)
    op.create_index(op.f('ix_legal_cases_status'), 'legal_cases', ['status'], unique=False)
    op.create_index(op.f('ix_legal_cases_verification_status'), 'legal_cases', ['verification_status'], unique=False)
    op.create_table('moderation_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('moderator_id', sa.Integer(), nullable=True),
    sa.Column('target_type', sa.String(length=24), nullable=False),
    sa.Column('target_id', sa.String(length=64), nullable=False),
    sa.Column('action', sa.String(length=32), nullable=False),
    sa.Column('reason', sa.String(length=240), nullable=False),
    sa.Column('metadata_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['moderator_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_moderation_actions_created_at'), 'moderation_actions', ['created_at'], unique=False)
    op.create_table('notification_outbox',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('body', sa.String(length=500), nullable=False),
    sa.Column('route', sa.String(length=255), nullable=False),
    sa.Column('payload_json', sa.Text(), nullable=False),
    sa.Column('idempotency_key', sa.String(length=120), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('max_retries', sa.Integer(), nullable=False),
    sa.Column('next_attempt_at', sa.DateTime(), nullable=False),
    sa.Column('last_error', sa.String(length=240), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('processed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idempotency_key', name='uq_notification_outbox_idempotency')
    )
    op.create_index('ix_notification_outbox_pending', 'notification_outbox', ['status', 'next_attempt_at'], unique=False)
    op.create_index(op.f('ix_notification_outbox_status'), 'notification_outbox', ['status'], unique=False)
    op.create_index(op.f('ix_notification_outbox_user_id'), 'notification_outbox', ['user_id'], unique=False)
    op.create_table('notification_preferences',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('in_app_enabled', sa.Boolean(), nullable=False),
    sa.Column('push_enabled', sa.Boolean(), nullable=False),
    sa.Column('generic_lock_screen', sa.Boolean(), nullable=False),
    sa.Column('quiet_start', sa.String(length=5), nullable=True),
    sa.Column('quiet_end', sa.String(length=5), nullable=True),
    sa.Column('timezone', sa.String(length=40), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('notification_type', sa.String(length=32), nullable=False),
    sa.Column('target_type', sa.String(length=24), nullable=False),
    sa.Column('target_id', sa.String(length=64), nullable=False),
    sa.Column('summary', sa.String(length=240), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_user_read_created', 'notifications', ['user_id', 'is_read', 'created_at'], unique=False)
    op.create_table('push_devices',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('platform', sa.String(length=16), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('encrypted_token', sa.Text(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'token_hash', name='uq_push_device_token')
    )
    op.create_index(op.f('ix_push_devices_token_hash'), 'push_devices', ['token_hash'], unique=False)
    op.create_index(op.f('ix_push_devices_user_id'), 'push_devices', ['user_id'], unique=False)
    op.create_table('user_activity_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=20), nullable=False),
    sa.Column('entity_type', sa.String(length=20), nullable=False),
    sa.Column('entity_id', sa.String(length=64), nullable=False),
    sa.Column('legal_domain', sa.String(length=40), nullable=False),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.Column('safe_metadata_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("event_type IN ('impression', 'click', 'dwell', 'view', 'search', 'favorite', 'unfavorite', 'dismiss', 'open_source', 'related_community_click', 'like', 'post', 'comment', 'consult')", name='ck_user_activity_event_type'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_activity_events_created_at'), 'user_activity_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_user_activity_events_event_type'), 'user_activity_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_user_activity_events_legal_domain'), 'user_activity_events', ['legal_domain'], unique=False)
    op.create_index(op.f('ix_user_activity_events_user_id'), 'user_activity_events', ['user_id'], unique=False)
    op.create_index('ix_user_events_user_created', 'user_activity_events', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_user_events_user_domain', 'user_activity_events', ['user_id', 'legal_domain'], unique=False)
    op.create_table('user_blocks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('blocker_id', sa.Integer(), nullable=False),
    sa.Column('blocked_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('blocker_id <> blocked_id', name='ck_user_block_self'),
    sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('blocker_id', 'blocked_id', name='uq_user_block')
    )
    op.create_index(op.f('ix_user_blocks_blocked_id'), 'user_blocks', ['blocked_id'], unique=False)
    op.create_index(op.f('ix_user_blocks_blocker_id'), 'user_blocks', ['blocker_id'], unique=False)
    op.create_table('user_interest_profiles',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('domain_weights_json', sa.Text(), nullable=False),
    sa.Column('profile_version', sa.String(length=32), nullable=False),
    sa.Column('personalization_enabled', sa.Boolean(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('user_memory_audit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('memory_id', sa.String(length=36), nullable=True),
    sa.Column('action', sa.String(length=24), nullable=False),
    sa.Column('reason', sa.String(length=240), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_memory_audit_created_at'), 'user_memory_audit', ['created_at'], unique=False)
    op.create_index(op.f('ix_user_memory_audit_memory_id'), 'user_memory_audit', ['memory_id'], unique=False)
    op.create_index(op.f('ix_user_memory_audit_user_id'), 'user_memory_audit', ['user_id'], unique=False)
    op.create_table('user_memory_settings',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('case_favorites',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['legal_cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'case_id', name='uq_case_favorite')
    )
    op.create_index(op.f('ix_case_favorites_case_id'), 'case_favorites', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_favorites_user_id'), 'case_favorites', ['user_id'], unique=False)
    op.create_table('case_law_references',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('law_name', sa.String(length=200), nullable=False),
    sa.Column('article', sa.String(length=80), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['legal_cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_law_references_case_id'), 'case_law_references', ['case_id'], unique=False)
    op.create_table('case_relations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('related_case_id', sa.Integer(), nullable=False),
    sa.Column('relevance_score', sa.Float(), nullable=False),
    sa.Column('reason', sa.String(length=240), nullable=False),
    sa.Column('algorithm_version', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['legal_cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['related_case_id'], ['legal_cases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'related_case_id', name='uq_case_relation')
    )
    op.create_index(op.f('ix_case_relations_case_id'), 'case_relations', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_relations_related_case_id'), 'case_relations', ['related_case_id'], unique=False)
    op.create_table('chat_attachments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('message_id', sa.String(length=36), nullable=False),
    sa.Column('storage_key', sa.String(length=255), nullable=False),
    sa.Column('original_name', sa.String(length=255), nullable=False),
    sa.Column('mime_type', sa.String(length=120), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('storage_key')
    )
    op.create_index(op.f('ix_chat_attachments_message_id'), 'chat_attachments', ['message_id'], unique=False)
    op.create_table('chat_message_hidden',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('message_id', 'user_id', name='uq_chat_message_hidden')
    )
    op.create_index(op.f('ix_chat_message_hidden_message_id'), 'chat_message_hidden', ['message_id'], unique=False)
    op.create_index(op.f('ix_chat_message_hidden_user_id'), 'chat_message_hidden', ['user_id'], unique=False)
    op.create_table('chat_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.String(length=36), nullable=False),
    sa.Column('reporter_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=240), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_reports_message_id'), 'chat_reports', ['message_id'], unique=False)
    op.create_index(op.f('ix_chat_reports_reporter_id'), 'chat_reports', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_chat_reports_status'), 'chat_reports', ['status'], unique=False)
    op.create_table('community_comments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('reply_to_user_id', sa.Integer(), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('like_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('published', 'hidden', 'deleted')", name='ck_community_comment_status'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['parent_id'], ['community_comments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['post_id'], ['community_posts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reply_to_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_comments_author_id'), 'community_comments', ['author_id'], unique=False)
    op.create_index(op.f('ix_community_comments_created_at'), 'community_comments', ['created_at'], unique=False)
    op.create_index(op.f('ix_community_comments_parent_id'), 'community_comments', ['parent_id'], unique=False)
    op.create_index('ix_community_comments_post_created', 'community_comments', ['post_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_community_comments_post_id'), 'community_comments', ['post_id'], unique=False)
    op.create_index(op.f('ix_community_comments_status'), 'community_comments', ['status'], unique=False)
    op.create_table('community_post_case_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('relevance_score', sa.Float(), nullable=False),
    sa.Column('reason', sa.String(length=240), nullable=False),
    sa.Column('link_source', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['legal_cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['post_id'], ['community_posts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('post_id', 'case_id', name='uq_community_post_case_link')
    )
    op.create_index(op.f('ix_community_post_case_links_case_id'), 'community_post_case_links', ['case_id'], unique=False)
    op.create_index(op.f('ix_community_post_case_links_post_id'), 'community_post_case_links', ['post_id'], unique=False)
    op.create_table('community_post_favorites',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['community_posts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'post_id', name='uq_community_post_favorite')
    )
    op.create_index(op.f('ix_community_post_favorites_post_id'), 'community_post_favorites', ['post_id'], unique=False)
    op.create_index(op.f('ix_community_post_favorites_user_id'), 'community_post_favorites', ['user_id'], unique=False)
    op.create_table('community_post_likes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['community_posts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'post_id', name='uq_community_post_like')
    )
    op.create_index(op.f('ix_community_post_likes_post_id'), 'community_post_likes', ['post_id'], unique=False)
    op.create_index(op.f('ix_community_post_likes_user_id'), 'community_post_likes', ['user_id'], unique=False)
    op.create_table('conversation_summaries',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('conversation_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('source_start_message_id', sa.Integer(), nullable=False),
    sa.Column('source_end_message_id', sa.Integer(), nullable=False),
    sa.Column('conflicts_json', sa.Text(), nullable=False),
    sa.Column('version', sa.String(length=24), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('conversation_id', 'source_start_message_id', 'source_end_message_id', name='uq_summary_source_range')
    )
    op.create_index(op.f('ix_conversation_summaries_conversation_id'), 'conversation_summaries', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_summaries_user_id'), 'conversation_summaries', ['user_id'], unique=False)
    op.create_table('legal_case_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['legal_cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['category_id'], ['case_categories.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'category_id', name='uq_legal_case_category')
    )
    op.create_index(op.f('ix_legal_case_categories_case_id'), 'legal_case_categories', ['case_id'], unique=False)
    op.create_index(op.f('ix_legal_case_categories_category_id'), 'legal_case_categories', ['category_id'], unique=False)
    op.create_table('legal_case_tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['legal_cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['case_tags.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_id', 'tag_id', name='uq_legal_case_tag')
    )
    op.create_index(op.f('ix_legal_case_tags_case_id'), 'legal_case_tags', ['case_id'], unique=False)
    op.create_index(op.f('ix_legal_case_tags_tag_id'), 'legal_case_tags', ['tag_id'], unique=False)
    op.create_table('notification_deliveries',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('outbox_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('channel', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('provider_message_id', sa.String(length=160), nullable=False),
    sa.Column('error_code', sa.String(length=80), nullable=False),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('delivered_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['outbox_id'], ['notification_outbox.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_deliveries_outbox_id'), 'notification_deliveries', ['outbox_id'], unique=False)
    op.create_index(op.f('ix_notification_deliveries_user_id'), 'notification_deliveries', ['user_id'], unique=False)
    op.create_index('ix_notification_delivery_user_created', 'notification_deliveries', ['user_id', 'created_at'], unique=False)
    op.create_table('recommendation_impressions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('reason_codes_json', sa.Text(), nullable=False),
    sa.Column('algorithm_version', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['legal_cases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recommendation_user_created', 'recommendation_impressions', ['user_id', 'created_at'], unique=False)
    op.create_table('community_comment_likes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('comment_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['comment_id'], ['community_comments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'comment_id', name='uq_community_comment_like')
    )
    op.create_index(op.f('ix_community_comment_likes_comment_id'), 'community_comment_likes', ['comment_id'], unique=False)
    op.create_index(op.f('ix_community_comment_likes_user_id'), 'community_comment_likes', ['user_id'], unique=False)
    op.create_table('community_post_origins',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('source_type', sa.String(length=24), nullable=False),
    sa.Column('source_conversation_id', sa.String(length=36), nullable=True),
    sa.Column('source_message_id', sa.Integer(), nullable=True),
    sa.Column('redaction_summary_json', sa.Text(), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['community_posts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_conversation_id'], ['conversations.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_message_id'], ['conversation_messages.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('post_id', name='uq_community_post_origin')
    )
    op.create_table('user_memory_items',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('memory_type', sa.String(length=24), nullable=False),
    sa.Column('legal_domain', sa.String(length=40), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('source_conversation_id', sa.String(length=36), nullable=True),
    sa.Column('source_message_id', sa.Integer(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('reason', sa.String(length=240), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(), nullable=False),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['source_conversation_id'], ['conversations.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_message_id'], ['conversation_messages.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_memory_user_domain_active', 'user_memory_items', ['user_id', 'legal_domain', 'deleted_at'], unique=False)
    op.create_index(op.f('ix_user_memory_items_user_id'), 'user_memory_items', ['user_id'], unique=False)
    op.create_table('user_memory_embeddings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('memory_id', sa.String(length=36), nullable=False),
    sa.Column('model', sa.String(length=80), nullable=False),
    sa.Column('vector_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['memory_id'], ['user_memory_items.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('memory_id')
    )


def downgrade():
    for table_name in reversed(CREATED_TABLES):
        op.drop_table(table_name)
