"""Query helpers for auto-trade: compute current triggers without side effects."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.auto_trade import AutoTradeRule
from app.models.auto_trade_global import AutoTradeGlobalRule
from app.models.investment_snapshot import InvestmentHoldingSnapshot
from app.models.investment_peak import InvestmentPeakTracker


def list_current_triggers(db: Session, user_id: str) -> list[dict]:
    """Return current trigger candidates for enabled rules, without placing orders."""
    results: list[dict] = []
    rules = db.query(AutoTradeRule).filter(AutoTradeRule.enabled.is_(True), AutoTradeRule.user_id == user_id).all()
    for rule in rules:
        holdings = (
            db.query(InvestmentHoldingSnapshot)
            .filter(
                InvestmentHoldingSnapshot.user_id == user_id,
                InvestmentHoldingSnapshot.account_id == rule.account_id,
            )
            .all()
        )
        for h in holdings:
            if h.ticker != rule.ticker:
                continue
            current_price = Decimal(str(h.current_price or 0))
            if current_price <= 0:
                continue
            threshold = Decimal(str(rule.trigger_percent or 0))
            actual = Decimal("0")
            hit = False
            if rule.trigger_kind == "cost_drop":
                avg = Decimal(str(h.average_price or 0))
                if avg > 0:
                    actual = (avg - current_price) / avg * Decimal("100")
                    hit = actual >= threshold
            else:  # peak_drop
                peak_row = (
                    db.query(InvestmentPeakTracker)
                    .filter(
                        InvestmentPeakTracker.user_id == user_id,
                        InvestmentPeakTracker.account_id == rule.account_id,
                        InvestmentPeakTracker.ticker == rule.ticker,
                    )
                    .first()
                )
                peak = Decimal(str(peak_row.peak_price)) if peak_row else current_price
                if peak > 0:
                    actual = (peak - current_price) / peak * Decimal("100")
                    hit = actual >= threshold
            if hit:
                results.append(
                    {
                        "rule": {
                            "id": rule.id,
                            "account_id": rule.account_id,
                            "ticker": rule.ticker,
                            "trigger_kind": rule.trigger_kind,
                            "trigger_percent": float(threshold),
                            "action_mode": rule.action_mode,
                        },
                        "ticker": h.ticker,
                        "name": h.name,
                        "currentPrice": float(current_price),
                        "shares": float(h.quantity or 0),
                        "threshold": float(threshold),
                        "actual": float(actual),
                    }
                )

    # Global rules: apply to all tickers in the account
    global_rules = db.query(AutoTradeGlobalRule).filter(AutoTradeGlobalRule.enabled.is_(True), AutoTradeGlobalRule.user_id == user_id).all()
    for gr in global_rules:
        holdings = (
            db.query(InvestmentHoldingSnapshot)
            .filter(
                InvestmentHoldingSnapshot.user_id == user_id,
                InvestmentHoldingSnapshot.account_id == gr.account_id,
            )
            .all()
        )
        for h in holdings:
            current_price = Decimal(str(h.current_price or 0))
            if h.ticker is None or current_price <= 0:
                continue

            threshold = Decimal(str(gr.trigger_percent or 0))
            actual = Decimal("0")
            hit = False

            if gr.trigger_kind == "cost_drop":
                avg = Decimal(str(h.average_price or 0))
                if avg > 0:
                    actual = (avg - current_price) / avg * Decimal("100")
                    hit = actual >= threshold
            else:  # peak_drop
                peak_row = (
                    db.query(InvestmentPeakTracker)
                    .filter(
                        InvestmentPeakTracker.user_id == user_id,
                        InvestmentPeakTracker.account_id == gr.account_id,
                        InvestmentPeakTracker.ticker == h.ticker,
                    )
                    .first()
                )
                peak = Decimal(str(peak_row.peak_price)) if peak_row else current_price
                if peak > 0:
                    actual = (peak - current_price) / peak * Decimal("100")
                    hit = actual >= threshold

            if not hit:
                continue

            results.append(
                {
                    "rule": {
                        "id": gr.id,
                        "account_id": gr.account_id,
                        "ticker": h.ticker,
                        "trigger_kind": gr.trigger_kind,
                        "trigger_percent": float(threshold),
                        "action_mode": gr.action_mode,
                    },
                    "ticker": h.ticker,
                    "name": h.name,
                    "currentPrice": float(current_price),
                    "shares": float(h.quantity or 0),
                    "threshold": float(threshold),
                    "actual": float(actual),
                }
            )
    return results

