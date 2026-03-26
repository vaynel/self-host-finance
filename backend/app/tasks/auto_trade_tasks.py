"""Celery tasks for syncing broker holdings and evaluating auto-trade rules."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.account import Account
from app.models.broker_account import BrokerAccount
from app.services.investment_service import sync_holdings_snapshot
from app.services.auto_trade_evaluator import evaluate_once

logger = get_task_logger(__name__)


def _sync_targets() -> list[tuple[str, str]]:
    """Return (user_id, account_id) targets for holding sync."""
    db = SessionLocal()
    try:
        rows = (
            db.query(Account.user_id, Account.id)
            .join(BrokerAccount, BrokerAccount.account_id == Account.id)
            .filter(
                Account.type == "investment",
                BrokerAccount.broker_type == "KIS",
                BrokerAccount.api_enabled.is_(True),
                BrokerAccount.auto_trade_enabled.is_(True),
            )
            .all()
        )
        return [(str(r[0]), str(r[1])) for r in rows]
    finally:
        db.close()


@celery_app.task(name="app.tasks.auto_trade_tasks.sync_all_investment_holdings", bind=True, autoretry_for=())
def sync_all_investment_holdings(self) -> dict[str, Any]:
    """Sync KIS holdings snapshot for all auto-trade enabled investment accounts."""
    targets = _sync_targets()
    if not targets:
        logger.info("sync_all_investment_holdings: no targets")
        return {"synced": 0, "targets": 0}

    db = SessionLocal()
    synced = 0
    try:
        for user_id, account_id in targets:
            try:
                sync_holdings_snapshot(db, user_id=user_id, account_id=account_id)
                synced += 1
            except Exception as e:
                logger.exception("sync_all_investment_holdings failed: user_id=%s account_id=%s err=%s", user_id, account_id, e)
    finally:
        db.close()

    # After snapshots are updated, evaluate rules once and (if enabled) place orders.
    try:
        asyncio.run(evaluate_once())
    except RuntimeError:
        # asyncio loop may already exist in some Celery runtimes.
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(evaluate_once())
        finally:
            loop.close()

    return {"synced": synced, "targets": len(targets)}


@celery_app.task(name="app.tasks.auto_trade_tasks.evaluate_auto_trade_once", bind=True, autoretry_for=())
def evaluate_auto_trade_once(self) -> dict[str, Any]:
    """Evaluate auto-trade rules once and (if enabled) place orders."""
    try:
        asyncio.run(evaluate_once())
        return {"ok": True}
    except RuntimeError as e:
        # In case Celery is running with an event loop already.
        logger.warning("evaluate_auto_trade_once runtime error (trying fallback): %s", e)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(evaluate_once())
            return {"ok": True}
        finally:
            loop.close()

