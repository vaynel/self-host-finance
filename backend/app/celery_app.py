"""Celery app instance for FinFlow background jobs."""

from __future__ import annotations

from datetime import timedelta

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "finflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    timezone="Asia/Seoul",
    enable_utc=False,
)

# Beat schedule (only when enabled).
if settings.celery_enabled:
    celery_app.conf.beat_schedule = {
        "finflow_sync_investment_holdings": {
            "task": "app.tasks.auto_trade_tasks.sync_all_investment_holdings",
            "schedule": timedelta(seconds=settings.celery_sync_interval_seconds),
        },
    }

celery_app.autodiscover_tasks(["app.tasks"])

