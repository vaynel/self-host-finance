"""Background scheduler to poll pending orders and collect executions."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.investment_order import InvestmentOrder
from app.services.order_service import collect_executions

logger = logging.getLogger("finflow.order_status_scheduler")

_scheduler_task: asyncio.Task | None = None


async def poll_order_status_once() -> None:
    """Poll pending/partially_filled orders and trigger execution collection."""
    db = SessionLocal()
    try:
        # Cleanup orphan pending orders that have no broker_order_id (stuck rows)
        # Keep it conservative: only very old rows.
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        db.query(InvestmentOrder).filter(
            InvestmentOrder.status.in_(["pending", "partially_filled"]),
            (InvestmentOrder.broker_order_id.is_(None)) | (InvestmentOrder.broker_order_id == ""),
            InvestmentOrder.requested_at < cutoff,
        ).update(
            {"status": "failed", "updated_at": datetime.utcnow()},
            synchronize_session=False,
        )
        db.commit()

        orders = (
            db.query(InvestmentOrder)
            .filter(InvestmentOrder.status.in_(["pending", "partially_filled"]))
            .all()
        )
        for order in orders:
            try:
                collect_executions(db, order.user_id, order.id)
            except Exception:
                logger.exception("Failed to poll order status: order_id=%s", order.id)
    finally:
        db.close()


async def order_status_scheduler_loop() -> None:
    """Run polling loop every minute."""
    interval_seconds = 60
    logger.info("Starting order status scheduler loop interval=%ss", interval_seconds)
    while True:
        try:
            await poll_order_status_once()
        except Exception:
            logger.exception("order status scheduler cycle failed")
        await asyncio.sleep(interval_seconds)


def start_order_status_scheduler_if_needed() -> None:
    """Start scheduler once per process."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = asyncio.create_task(order_status_scheduler_loop())
