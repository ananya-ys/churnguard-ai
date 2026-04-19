"""app/tasks/worker.py — Celery configuration + beat schedules."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "churnguard",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.batch_predict",
        "app.tasks.retrain",
        "app.tasks.drift_check",   # Phase 4
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    result_expires=3600,
)

# ── Beat schedule ──────────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Phase 1: Weekly auto-retrain (Sunday 02:00 UTC)
    "weekly-retrain": {
        "task": "app.tasks.retrain.scheduled_retrain",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
    },

    # Phase 4: Daily drift check (03:00 UTC every day)
    "daily-drift-check": {
        "task": "app.tasks.drift_check.run_daily_drift_check",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"lookback_hours": 24},
    },
}
