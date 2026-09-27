# Database migrations

This migration directory starts with a frozen, additive schema snapshot for
community, verified cases, recommendations, direct chat, notifications and AI
memory. It never imports application models at migration runtime. Existing
ChatLaw installations already have the legacy `users`, `analysis_records`,
`conversations` and `conversation_messages` tables.

For a controlled production deployment, set `AUTO_INIT_DB=0`, back up the
database, and run `flask db upgrade`. Fresh development databases may keep
`AUTO_INIT_DB=1`; `db.create_all()` creates the same additive schema.

The v2 migration is intentionally non-destructive and idempotent so it also
works for installations that previously applied the old runtime-metadata
baseline. Application rollback keeps the additive columns/tables to preserve
messages, notification history and user-confirmed memories.
