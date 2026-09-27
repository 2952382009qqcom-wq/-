"""Celery entry point. Run: celery -A worker.celery worker --loglevel=INFO."""

import os

from celery import Celery, Task

# A worker never owns schema creation or reference-data seeding. Deployment
# runs Alembic explicitly before web/worker processes start.
os.environ.setdefault("AUTO_INIT_DB", "0")
os.environ.setdefault("AUTO_SEED_REFERENCE_DATA", "0")

from app import app


class FlaskTask(Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


celery = Celery(
    "mingjian",
    task_cls=FlaskTask,
    broker=os.getenv("CELERY_BROKER_URL", os.getenv("SOCKETIO_REDIS_URL", "redis://localhost:6379/1")),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["core.tasks"],
)
celery.conf.update(
    task_serializer="json", result_serializer="json", accept_content=["json"],
    timezone="Asia/Shanghai", enable_utc=True, task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "notification-outbox-every-minute": {"task": "mingjian.process_notification_outbox", "schedule": 60.0},
        "conversation-summary-every-five-minutes": {"task": "mingjian.rebuild_due_summaries", "schedule": 300.0},
        "memory-embeddings-every-five-minutes": {"task": "mingjian.build_memory_embeddings", "schedule": 300.0},
    },
)
