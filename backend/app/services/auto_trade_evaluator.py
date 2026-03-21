"""Background evaluator to compute drop triggers and act (alert_only | auto_sell)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.auto_trade import AutoTradeRule, AutoTradeRunLog
from app.models.auto_trade_global import AutoTradeGlobalRule
from app.models.investment_peak import InvestmentPeakTracker
from app.models.investment_snapshot import InvestmentHoldingSnapshot
from app.models.investment_order import InvestmentOrder
from app.services.auto_trade_service import (
    evaluate_rule_guard,
    create_run_log,
    create_global_run_log,
    is_market_open_kst,
)
from app.services.order_service import create_order
from app.services.discord_notify import notify_rule_triggered

logger = logging.getLogger("finflow.debug")

_task: asyncio.Task | None = None


def _get_latest_holdings(db: Session, user_id: str, account_id: str):
    # Use latest snapshot (by synced_at) - simplified: read all current rows for account
    return (
        db.query(InvestmentHoldingSnapshot)
        .filter(InvestmentHoldingSnapshot.user_id == user_id, InvestmentHoldingSnapshot.account_id == account_id)
        .all()
    )


async def evaluate_once() -> None:
    db = SessionLocal()
    try:
        rules = db.query(AutoTradeRule).filter(AutoTradeRule.enabled.is_(True)).all()
        now = datetime.utcnow()
        any_global_triggered = False
        for rule in rules:
            ok, reason = evaluate_rule_guard(db, rule)
            if not ok:
                continue

            holdings = _get_latest_holdings(db, rule.user_id, rule.account_id)
            target = next((h for h in holdings if h.ticker == rule.ticker), None)
            if not target:
                continue

            current_price = Decimal(str(target.current_price or 0))
            if current_price <= 0:
                continue

            trigger = False
            if rule.trigger_kind == "cost_drop":
                avg = Decimal(str(target.average_price or 0))
                if avg > 0:
                    drop = (avg - current_price) / avg * Decimal("100")
                    trigger = drop >= (rule.trigger_percent or 0)
            elif rule.trigger_kind == "peak_drop":
                peak_row = (
                    db.query(InvestmentPeakTracker)
                    .filter(
                        InvestmentPeakTracker.user_id == rule.user_id,
                        InvestmentPeakTracker.account_id == rule.account_id,
                        InvestmentPeakTracker.ticker == rule.ticker,
                    )
                    .first()
                )
                peak_price = Decimal(str(peak_row.peak_price)) if peak_row else current_price
                if current_price > peak_price:
                    # keep peak updated opportunistically
                    if peak_row:
                        peak_row.peak_price = current_price
                        peak_row.updated_at = now
                    else:
                        db.add(
                            InvestmentPeakTracker(
                                id=f"ipt_{now.timestamp():.0f}",
                                user_id=rule.user_id,
                                account_id=rule.account_id,
                                ticker=rule.ticker,
                                peak_price=current_price,
                            )
                        )
                else:
                    drop = (peak_price - current_price) / peak_price * Decimal("100") if peak_price > 0 else Decimal("0")
                    trigger = drop >= (rule.trigger_percent or 0)

            if not trigger:
                continue

            if rule.action_mode == "alert_only":
                create_run_log(
                    db,
                    user_id=rule.user_id,
                    rule_id=rule.id,
                    account_id=rule.account_id,
                    ticker=rule.ticker,
                    status="triggered",
                    reason=f"{rule.trigger_kind} {float(rule.trigger_percent)}%",
                )
                notify_rule_triggered(
                    db,
                    user_id=rule.user_id,
                    scope="ticker",
                    rule_id=rule.id,
                    account_id=rule.account_id,
                    ticker=rule.ticker,
                    stock_name=getattr(target, "name", None),
                    trigger_kind=rule.trigger_kind,
                    trigger_percent=float(rule.trigger_percent or 0),
                    action_mode=rule.action_mode,
                    detail="조건 충족 (알림만)",
                )
                rule.last_triggered_at = now
                db.commit()
                continue

            # auto_sell
            try:
                order = create_order(
                    db=db,
                    user_id=rule.user_id,
                    account_id=rule.account_id,
                    ticker=rule.ticker,
                    side="sell",
                    quantity=Decimal(str(rule.quantity)),
                    price=Decimal(str(rule.limit_price)) if rule.order_type == "limit" and rule.limit_price else None,
                    order_type=rule.order_type,
                )
                create_run_log(
                    db,
                    user_id=rule.user_id,
                    rule_id=rule.id,
                    account_id=rule.account_id,
                    ticker=rule.ticker,
                    status="triggered",
                    reason=f"auto_sell {rule.trigger_kind} {float(rule.trigger_percent)}%",
                    order_id=order["id"],
                )
                notify_rule_triggered(
                    db,
                    user_id=rule.user_id,
                    scope="ticker",
                    rule_id=rule.id,
                    account_id=rule.account_id,
                    ticker=rule.ticker,
                    stock_name=getattr(target, "name", None),
                    trigger_kind=rule.trigger_kind,
                    trigger_percent=float(rule.trigger_percent or 0),
                    action_mode=rule.action_mode,
                    detail="매도 주문 접수",
                    order_id=order["id"],
                )
                rule.last_triggered_at = now
                db.commit()
            except Exception as e:
                logger.exception("auto_sell failed: rule_id=%s", rule.id)
                create_run_log(
                    db,
                    user_id=rule.user_id,
                    rule_id=rule.id,
                    account_id=rule.account_id,
                    ticker=rule.ticker,
                    status="failed",
                    reason=str(e),
                )
                db.commit()

        # Global rules evaluation (applies to all tickers in an account)
        global_rules = db.query(AutoTradeGlobalRule).filter(AutoTradeGlobalRule.enabled.is_(True)).all()
        for gr in global_rules:
            # global cooldown (per rule)
            if not is_market_open_kst():
                continue
            cooldown = int(gr.cooldown_seconds or "300")
            if gr.last_triggered_at and datetime.utcnow() < (gr.last_triggered_at + timedelta(seconds=cooldown)):
                continue

            holdings = _get_latest_holdings(db, gr.user_id, gr.account_id)
            triggered_any_for_rule = False
            for h in holdings:
                if not h.ticker:
                    continue

                current_price = Decimal(str(h.current_price or 0))
                if current_price <= 0:
                    continue

                threshold = Decimal(str(gr.trigger_percent or 0))
                trigger = False
                if gr.trigger_kind == "cost_drop":
                    avg = Decimal(str(h.average_price or 0))
                    if avg > 0:
                        drop = (avg - current_price) / avg * Decimal("100")
                        trigger = drop >= threshold
                else:  # peak_drop
                    peak_row = (
                        db.query(InvestmentPeakTracker)
                        .filter(
                            InvestmentPeakTracker.user_id == gr.user_id,
                            InvestmentPeakTracker.account_id == gr.account_id,
                            InvestmentPeakTracker.ticker == h.ticker,
                        )
                        .first()
                    )
                    peak_price = Decimal(str(peak_row.peak_price)) if peak_row else current_price
                    if peak_price > 0:
                        drop = (peak_price - current_price) / peak_price * Decimal("100")
                        # keep peak updated opportunistically
                        if current_price > peak_price and peak_row:
                            peak_row.peak_price = current_price
                            peak_row.updated_at = now
                        trigger = drop >= threshold

                if not trigger:
                    continue

                if gr.action_mode == "alert_only":
                    create_global_run_log(
                        db,
                        user_id=gr.user_id,
                        rule_id=gr.id,
                        account_id=gr.account_id,
                        ticker=h.ticker,
                        status="triggered",
                        reason=f"{gr.trigger_kind} {float(threshold)}%",
                    )
                    notify_rule_triggered(
                        db,
                        user_id=gr.user_id,
                        scope="global",
                        rule_id=gr.id,
                        account_id=gr.account_id,
                        ticker=h.ticker,
                        stock_name=getattr(h, "name", None),
                        trigger_kind=gr.trigger_kind,
                        trigger_percent=float(threshold),
                        action_mode=gr.action_mode,
                        detail="글로벌 룰 조건 충족 (알림만)",
                    )
                    triggered_any_for_rule = True
                    continue

                # auto_sell: avoid duplicate pending sell orders for this ticker
                duplicate_pending = (
                    db.query(InvestmentOrder)
                    .filter(
                        InvestmentOrder.user_id == gr.user_id,
                        InvestmentOrder.account_id == gr.account_id,
                        InvestmentOrder.ticker == h.ticker,
                        InvestmentOrder.side == "sell",
                        InvestmentOrder.status.in_(["pending", "partially_filled"]),
                    )
                    .first()
                )
                if duplicate_pending:
                    create_global_run_log(
                        db,
                        user_id=gr.user_id,
                        rule_id=gr.id,
                        account_id=gr.account_id,
                        ticker=h.ticker,
                        status="skipped",
                        reason="duplicate_pending_order",
                    )
                    continue

                qty = Decimal(str(h.quantity or 0)) * Decimal(str(gr.sell_quantity_ratio or 1))
                if qty <= 0:
                    continue

                price = None
                if gr.order_type == "limit" and gr.limit_price is not None:
                    price = Decimal(str(gr.limit_price))
                try:
                    order = create_order(
                        db=db,
                        user_id=gr.user_id,
                        account_id=gr.account_id,
                        ticker=h.ticker,
                        side="sell",
                        quantity=qty,
                        price=price,
                        order_type=gr.order_type,
                    )
                    create_global_run_log(
                        db,
                        user_id=gr.user_id,
                        rule_id=gr.id,
                        account_id=gr.account_id,
                        ticker=h.ticker,
                        status="triggered",
                        reason=f"auto_sell {gr.trigger_kind} {float(threshold)}%",
                        order_id=order["id"],
                    )
                    notify_rule_triggered(
                        db,
                        user_id=gr.user_id,
                        scope="global",
                        rule_id=gr.id,
                        account_id=gr.account_id,
                        ticker=h.ticker,
                        stock_name=getattr(h, "name", None),
                        trigger_kind=gr.trigger_kind,
                        trigger_percent=float(threshold),
                        action_mode=gr.action_mode,
                        detail="글로벌 룰 매도 주문 접수",
                        order_id=order["id"],
                    )
                    triggered_any_for_rule = True
                except Exception as e:
                    logger.exception("global auto_sell failed: rule_id=%s ticker=%s", gr.id, h.ticker)
                    create_global_run_log(
                        db,
                        user_id=gr.user_id,
                        rule_id=gr.id,
                        account_id=gr.account_id,
                        ticker=h.ticker,
                        status="failed",
                        reason=str(e),
                    )

            if triggered_any_for_rule:
                gr.last_triggered_at = now
                any_global_triggered = True
        if any_global_triggered:
            db.commit()
    finally:
        db.close()


async def loop() -> None:
    logger.info("Starting auto-trade evaluator loop interval=60s")
    while True:
        try:
            await evaluate_once()
        except Exception:
            logger.exception("auto-trade evaluator cycle failed")
        await asyncio.sleep(60)


def start_auto_trade_evaluator_if_needed() -> None:
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(loop())

