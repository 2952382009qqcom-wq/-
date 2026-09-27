# Database migrations

This migration directory starts with the additive community, verified-case,
recommendation and direct-chat schema. Existing ChatLaw installations already
have the legacy `users`, `analysis_records`, `conversations` and
`conversation_messages` tables.

For a controlled production deployment, set `AUTO_INIT_DB=0`, back up the
database, and run `flask db upgrade`. Fresh development databases may keep
`AUTO_INIT_DB=1`; `db.create_all()` creates the same additive schema.
