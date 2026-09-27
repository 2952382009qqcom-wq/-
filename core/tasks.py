"""Background workloads. Never call these implementations inside a web request."""

from datetime import datetime

from worker import celery

from core.models import db
from core.notifications.models import NotificationOutbox
from core.notifications.services import process_outbox_item


@celery.task(name="mingjian.process_notification_outbox", autoretry_for=(OSError,), retry_backoff=True, max_retries=5)
def process_notification_outbox(batch_size=100):
    rows = NotificationOutbox.query.filter(
        NotificationOutbox.status.in_(("pending", "retry", "processing")),
        NotificationOutbox.next_attempt_at <= datetime.utcnow(),
    ).order_by(NotificationOutbox.next_attempt_at.asc()).limit(min(int(batch_size), 500)).all()
    for row in rows:
        process_outbox_item(row.id)
    return len(rows)


@celery.task(name="mingjian.rebuild_search_index")
def rebuild_search_index():
    from core.search.indexing import process_outbox
    return process_outbox(limit=500)


@celery.task(name="mingjian.publish_recommender_artifact")
def publish_recommender_artifact(version):
    # Training lives in an offline pipeline. This task only records an explicit
    # version switch after validation, making rollback possible and auditable.
    return {"version": str(version), "status": "validation_required"}


@celery.task(name="mingjian.rebuild_conversation_summary")
def rebuild_conversation_summary(conversation_id):
    from core.memory.services import rebuild_summary
    return rebuild_summary(conversation_id)


@celery.task(name="mingjian.rebuild_due_summaries")
def rebuild_due_summaries(batch_size=50):
    from sqlalchemy import func
    from core.models import Conversation, ConversationMessage
    from core.memory.services import rebuild_summary
    rows = db.session.query(Conversation.id).join(
        ConversationMessage, ConversationMessage.conversation_id == Conversation.id
    ).group_by(Conversation.id).having(func.count(ConversationMessage.id) >= 10).limit(min(int(batch_size), 200)).all()
    return [rebuild_summary(row[0]) for row in rows]


@celery.task(name="mingjian.build_memory_embeddings")
def build_memory_embeddings(batch_size=200):
    from core.memory.services import build_missing_embeddings
    return build_missing_embeddings(batch_size)
