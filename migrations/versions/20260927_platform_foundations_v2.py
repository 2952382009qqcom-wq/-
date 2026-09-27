"""Add platform foundation columns and tables for installations that ran the old baseline.

Revision ID: 20260927_platform_foundations_v2
Revises: 20260927_community_cases_chat

The migration is additive and idempotent because the frozen baseline was also
updated for fresh installations. Existing rows are preserved.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260927_platform_foundations_v2"
down_revision = "20260927_community_cases_chat"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name):
    return name in _inspector().get_table_names()


def _columns(table):
    return {column["name"] for column in _inspector().get_columns(table)}


def _indexes(table):
    return {index["name"] for index in _inspector().get_indexes(table)}


def upgrade():
    if _has_table("chat_threads") and "next_sequence" not in _columns("chat_threads"):
        op.add_column("chat_threads", sa.Column("next_sequence", sa.Integer(), nullable=False, server_default="1"))

    if _has_table("chat_participants"):
        columns = _columns("chat_participants")
        if "last_read_sequence" not in columns:
            op.add_column("chat_participants", sa.Column("last_read_sequence", sa.Integer(), nullable=False, server_default="0"))
        if "muted_until" not in columns:
            op.add_column("chat_participants", sa.Column("muted_until", sa.DateTime(), nullable=True))

    if _has_table("chat_messages"):
        columns = _columns("chat_messages")
        additions = (
            ("client_message_id", sa.Column("client_message_id", sa.String(length=64), nullable=True)),
            ("sequence", sa.Column("sequence", sa.Integer(), nullable=False, server_default="0")),
            ("message_type", sa.Column("message_type", sa.String(length=16), nullable=False, server_default="text")),
            ("reply_to_id", sa.Column("reply_to_id", sa.String(length=36), nullable=True)),
            ("delivered_at", sa.Column("delivered_at", sa.DateTime(), nullable=True)),
            ("moderation_reason", sa.Column("moderation_reason", sa.String(length=240), nullable=False, server_default="")),
        )
        for name, column in additions:
            if name not in columns:
                op.add_column("chat_messages", column)
        if op.get_bind().dialect.name == "mysql":
            op.execute(sa.text("""UPDATE chat_messages AS target
                JOIN (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY thread_id ORDER BY created_at, id) AS new_sequence
                    FROM chat_messages
                ) AS ranked ON ranked.id = target.id
                SET target.sequence = ranked.new_sequence
                WHERE target.sequence = 0"""))
        else:
            op.execute(sa.text("""UPDATE chat_messages SET sequence = (
                SELECT COUNT(*) FROM chat_messages AS older
                WHERE older.thread_id = chat_messages.thread_id
                  AND (older.created_at < chat_messages.created_at
                       OR (older.created_at = chat_messages.created_at AND older.id <= chat_messages.id))
            ) WHERE sequence = 0"""))
        op.execute(sa.text("""UPDATE chat_threads SET next_sequence = COALESCE(
            (SELECT MAX(chat_messages.sequence) + 1 FROM chat_messages WHERE chat_messages.thread_id = chat_threads.id), 1
        )"""))
        # Preserve read state from the v1 message-id cursor after assigning the
        # new per-thread sequence numbers. Without this backfill, every old
        # conversation would appear unread immediately after deployment.
        if _has_table("chat_participants"):
            op.execute(sa.text("""UPDATE chat_participants SET last_read_sequence = COALESCE(
                (SELECT chat_messages.sequence FROM chat_messages
                 WHERE chat_messages.id = chat_participants.last_read_message_id
                   AND chat_messages.thread_id = chat_participants.thread_id), 0
            ) WHERE last_read_sequence = 0 AND last_read_message_id IS NOT NULL"""))
        indexes = _indexes("chat_messages")
        if "ix_chat_messages_thread_sequence" not in indexes:
            op.create_index("ix_chat_messages_thread_sequence", "chat_messages", ["thread_id", "sequence"], unique=False)
        unique_names = {item.get("name") for item in _inspector().get_unique_constraints("chat_messages")}
        chat_checks = {item.get("name"): item.get("sqltext", "") for item in _inspector().get_check_constraints("chat_messages")}
        with op.batch_alter_table("chat_messages") as batch:
            if "uq_chat_message_sequence" not in unique_names:
                batch.create_unique_constraint("uq_chat_message_sequence", ["thread_id", "sequence"])
            if "uq_chat_sender_client_message" not in unique_names:
                batch.create_unique_constraint("uq_chat_sender_client_message", ["sender_id", "client_message_id"])
            if not any(item.get("constrained_columns") == ["reply_to_id"] for item in _inspector().get_foreign_keys("chat_messages")):
                batch.create_foreign_key("fk_chat_message_reply", "chat_messages", ["reply_to_id"], ["id"], ondelete="SET NULL")
            if "message_type" not in chat_checks.get("ck_chat_message_type", ""):
                if "ck_chat_message_type" in chat_checks:
                    batch.drop_constraint("ck_chat_message_type", type_="check")
                batch.create_check_constraint("ck_chat_message_type", "message_type IN ('text', 'image', 'attachment', 'system')")
            if "delivered" not in chat_checks.get("ck_chat_message_status", ""):
                if "ck_chat_message_status" in chat_checks:
                    batch.drop_constraint("ck_chat_message_status", type_="check")
                batch.create_check_constraint("ck_chat_message_status", "status IN ('sent', 'delivered', 'recalled', 'deleted', 'moderated')")

    if _has_table("user_activity_events"):
        checks = {item.get("name"): item.get("sqltext", "") for item in _inspector().get_check_constraints("user_activity_events")}
        if "dwell" not in checks.get("ck_user_activity_event_type", ""):
            with op.batch_alter_table("user_activity_events") as batch:
                if "ck_user_activity_event_type" in checks:
                    batch.drop_constraint("ck_user_activity_event_type", type_="check")
                batch.create_check_constraint("ck_user_activity_event_type", "event_type IN ('impression', 'click', 'dwell', 'view', 'search', 'favorite', 'unfavorite', 'dismiss', 'open_source', 'related_community_click', 'like', 'post', 'comment', 'consult')")

    if not _has_table('chat_audit_logs'):
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

    if not _has_table('notification_outbox'):
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

    if not _has_table('notification_preferences'):
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

    if not _has_table('push_devices'):
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

    if not _has_table('user_memory_audit'):
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

    if not _has_table('user_memory_settings'):
        op.create_table('user_memory_settings',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
        )

    if not _has_table('chat_attachments'):
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

    if not _has_table('chat_message_hidden'):
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

    if not _has_table('chat_reports'):
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

    if not _has_table('conversation_summaries'):
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

    if not _has_table('notification_deliveries'):
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

    if not _has_table('user_memory_items'):
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

    if not _has_table('user_memory_embeddings'):
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


    if not _has_table('chat_user_sanctions'):
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


def downgrade():
    # Deliberately non-destructive. Roll back application code first; the added
    # columns/tables remain compatible and preserve user messages, notifications
    # and explicitly saved memories.
    pass

