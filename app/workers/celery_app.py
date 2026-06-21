"""Celery application + Beat schedule.

A SINGLE Beat entry runs the lightweight ``sweep`` task every 15 minutes; the
sweep fans out idempotent per-user tasks. No per-user Beat entries.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "grit",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "sweep-every-15-minutes": {
            "task": "app.workers.tasks.sweep",
            "schedule": crontab(minute="*/15"),
        },
    },
)
