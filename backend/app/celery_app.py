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

# Celery autodiscovery looks for "<package>.tasks" modules.
# Our tasks live in "app.tasks.*", so we should pass ["app"] here.
celery_app.autodiscover_tasks(["app"])

# Ensure tasks module is importable even if autodiscovery is misconfigured.
celery_app.conf.include = ["app.tasks.auto_trade_tasks"]

