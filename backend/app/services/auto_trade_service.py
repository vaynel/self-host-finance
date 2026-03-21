"""Auto-trade rule service."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import raise_400, raise_404
from app.models.account import Account
from app.models.auto_trade import AutoTradeRule, AutoTradeRunLog
from app.models.auto_trade_global import AutoTradeGlobalRule, AutoTradeGlobalRunLog
from app.models.investment_peak import InvestmentPeakTracker
from app.models.broker_account import BrokerAccount
from app.models.investment_order import InvestmentOrder


def _rule_to_dict(rule: AutoTradeRule) -> dict:
    return {
        "id": rule.id,
        "account_id": rule.account_id,
        "ticker": rule.ticker,
        "side": rule.side,
        "enabled": bool(rule.enabled),
        "target_price": float(rule.target_price) if rule.target_price is not None else None,
        "stop_price": float(rule.stop_price) if rule.stop_price is not None else None,
        "order_type": rule.order_type,
        "quantity": float(rule.quantity),
        "limit_price": float(rule.limit_price) if rule.limit_price is not None else None,
        "cooldown_seconds": int(rule.cooldown_seconds or "300"),
        "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
        "trigger_kind": rule.trigger_kind,
        "trigger_percent": float(rule.trigger_percent or 0),
        "action_mode": rule.action_mode,
    }


def list_rules(db: Session, user_id: str) -> list[dict]:
    rows = db.query(AutoTradeRule).filter(AutoTradeRule.user_id == user_id).order_by(AutoTradeRule.created_at.desc()).all()
    return [_rule_to_dict(r) for r in rows]


def create_rule(db: Session, user_id: str, data: dict) -> dict:
    account_id = data["account_id"]
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise_404("계좌를 찾을 수 없습니다.")
    if account.type != "investment":
        raise_400("투자 계좌에만 자동매매 규칙을 생성할 수 있습니다.")

    side = data["side"]
    if side not in ("buy", "sell"):
        raise_400("side는 buy 또는 sell이어야 합니다.")

    rule = AutoTradeRule(
        id=f"atr_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        account_id=account_id,
        ticker=data["ticker"],
        side=side,
        enabled=bool(data.get("enabled", True)),
        target_price=Decimal(str(data["target_price"])) if data.get("target_price") is not None else None,
        stop_price=Decimal(str(data["stop_price"])) if data.get("stop_price") is not None else None,
        order_type=data.get("order_type", "limit"),
        quantity=Decimal(str(data["quantity"])),
        limit_price=Decimal(str(data["limit_price"])) if data.get("limit_price") is not None else None,
        cooldown_seconds=str(data.get("cooldown_seconds", 300)),
        trigger_kind=data.get("trigger_kind", "cost_drop"),
        trigger_percent=Decimal(str(data.get("trigger_percent", 0))),
        action_mode=data.get("action_mode", "alert_only"),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_dict(rule)


def update_rule(db: Session, user_id: str, rule_id: str, data: dict) -> dict:
    rule = db.query(AutoTradeRule).filter(AutoTradeRule.id == rule_id, AutoTradeRule.user_id == user_id).first()
    if not rule:
        raise_404("규칙을 찾을 수 없습니다.")

    for key in ("ticker", "side", "order_type", "trigger_kind", "action_mode"):
        if key in data and data[key] is not None:
            setattr(rule, key, data[key])
    for key in ("enabled",):
        if key in data and data[key] is not None:
            setattr(rule, key, bool(data[key]))

    if "target_price" in data:
        rule.target_price = Decimal(str(data["target_price"])) if data["target_price"] is not None else None
    if "stop_price" in data:
        rule.stop_price = Decimal(str(data["stop_price"])) if data["stop_price"] is not None else None
    if "quantity" in data and data["quantity"] is not None:
        rule.quantity = Decimal(str(data["quantity"]))
    if "limit_price" in data:
        rule.limit_price = Decimal(str(data["limit_price"])) if data["limit_price"] is not None else None
    if "cooldown_seconds" in data and data["cooldown_seconds"] is not None:
        rule.cooldown_seconds = str(int(data["cooldown_seconds"]))
    if "trigger_percent" in data and data["trigger_percent"] is not None:
        rule.trigger_percent = Decimal(str(data["trigger_percent"]))

    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return _rule_to_dict(rule)


def delete_rule(db: Session, user_id: str, rule_id: str) -> None:
    row = db.query(AutoTradeRule).filter(AutoTradeRule.id == rule_id, AutoTradeRule.user_id == user_id).first()
    if not row:
        raise_404("규칙을 찾을 수 없습니다.")
    db.delete(row)
    db.commit()


# ==================== Global rules ====================

def list_global_rules(db: Session, user_id: str) -> list[dict]:
    rows = (
        db.query(AutoTradeGlobalRule)
        .filter(AutoTradeGlobalRule.user_id == user_id)
        .order_by(AutoTradeGlobalRule.created_at.desc())
        .all()
    )
    items: list[dict] = []
    for r in rows:
        items.append(
            {
                "id": r.id,
                "account_id": r.account_id,
                "enabled": bool(r.enabled),
                "trigger_kind": r.trigger_kind,
                "trigger_percent": float(r.trigger_percent or 0),
                "action_mode": r.action_mode,
                "order_type": r.order_type,
                "sell_quantity_ratio": float(r.sell_quantity_ratio or 1),
                "limit_price": float(r.limit_price) if r.limit_price is not None else None,
                "cooldown_seconds": int(r.cooldown_seconds or "300"),
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
            }
        )
    return items


def create_global_rule(db: Session, user_id: str, data: dict) -> dict:
    account_id = data["account_id"]
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise_404("계좌를 찾을 수 없습니다.")
    if account.type != "investment":
        raise_400("투자 계좌에만 자동매매 규칙을 생성할 수 있습니다.")

    rule = AutoTradeGlobalRule(
        id=f"arg_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        account_id=account_id,
        enabled=bool(data.get("enabled", True)),
        trigger_kind=data.get("trigger_kind", "cost_drop"),
        trigger_percent=Decimal(str(data.get("trigger_percent", 0))),
        action_mode=data.get("action_mode", "alert_only"),
        order_type=data.get("order_type", "market"),
        sell_quantity_ratio=Decimal(str(data.get("sell_quantity_ratio", 1.0))),
        limit_price=Decimal(str(data["limit_price"])) if data.get("limit_price") is not None else None,
        cooldown_seconds=str(data.get("cooldown_seconds", 300)),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {
        "id": rule.id,
        "account_id": rule.account_id,
        "enabled": bool(rule.enabled),
        "trigger_kind": rule.trigger_kind,
        "trigger_percent": float(rule.trigger_percent or 0),
        "action_mode": rule.action_mode,
        "order_type": rule.order_type,
        "sell_quantity_ratio": float(rule.sell_quantity_ratio or 1),
        "limit_price": float(rule.limit_price) if rule.limit_price is not None else None,
        "cooldown_seconds": int(rule.cooldown_seconds or "300"),
        "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
    }


def update_global_rule(db: Session, user_id: str, rule_id: str, data: dict) -> dict:
    rule = db.query(AutoTradeGlobalRule).filter(AutoTradeGlobalRule.id == rule_id, AutoTradeGlobalRule.user_id == user_id).first()
    if not rule:
        raise_404("글로벌 규칙을 찾을 수 없습니다.")

    for key in ("enabled", "action_mode", "trigger_kind", "order_type"):
        if key in data and data[key] is not None:
            setattr(rule, key, data[key])

    if "trigger_percent" in data and data["trigger_percent"] is not None:
        rule.trigger_percent = Decimal(str(data["trigger_percent"]))
    if "sell_quantity_ratio" in data and data["sell_quantity_ratio"] is not None:
        rule.sell_quantity_ratio = Decimal(str(data["sell_quantity_ratio"]))
    if "limit_price" in data:
        rule.limit_price = Decimal(str(data["limit_price"])) if data["limit_price"] is not None else None
    if "cooldown_seconds" in data and data["cooldown_seconds"] is not None:
        rule.cooldown_seconds = str(int(data["cooldown_seconds"]))

    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)

    return {
        "id": rule.id,
        "account_id": rule.account_id,
        "enabled": bool(rule.enabled),
        "trigger_kind": rule.trigger_kind,
        "trigger_percent": float(rule.trigger_percent or 0),
        "action_mode": rule.action_mode,
        "order_type": rule.order_type,
        "sell_quantity_ratio": float(rule.sell_quantity_ratio or 1),
        "limit_price": float(rule.limit_price) if rule.limit_price is not None else None,
        "cooldown_seconds": int(rule.cooldown_seconds or "300"),
        "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
    }


def delete_global_rule(db: Session, user_id: str, rule_id: str) -> None:
    rule = db.query(AutoTradeGlobalRule).filter(AutoTradeGlobalRule.id == rule_id, AutoTradeGlobalRule.user_id == user_id).first()
    if not rule:
        raise_404("글로벌 규칙을 찾을 수 없습니다.")
    db.delete(rule)
    db.commit()


def create_global_run_log(
    db: Session,
    *,
    user_id: str,
    rule_id: str,
    account_id: str,
    ticker: str,
    status: str,
    reason: str | None = None,
    order_id: str | None = None,
) -> None:
    db.add(
        AutoTradeGlobalRunLog(
            id=f"argl_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            rule_id=rule_id,
            account_id=account_id,
            ticker=ticker,
            status=status,
            reason=reason,
            order_id=order_id,
        )
    )
    db.commit()


def list_global_logs(db: Session, user_id: str, limit: int = 50) -> list[dict]:
    rows = (
        db.query(AutoTradeGlobalRunLog)
        .filter(AutoTradeGlobalRunLog.user_id == user_id)
        .order_by(AutoTradeGlobalRunLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "rule_id": r.rule_id,
            "account_id": r.account_id,
            "ticker": r.ticker,
            "status": r.status,
            "reason": r.reason,
            "order_id": r.order_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def set_auto_trade_enabled(db: Session, user_id: str, account_id: str, enabled: bool) -> dict:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise_404("계좌를 찾을 수 없습니다.")

    broker_account = db.query(BrokerAccount).filter(BrokerAccount.account_id == account_id).first()
    if not broker_account:
        raise_404("브로커 계좌 상세를 찾을 수 없습니다.")

    broker_account.auto_trade_enabled = enabled
    broker_account.updated_at = datetime.utcnow()
    db.commit()
    return {
        "account_id": account_id,
        "auto_trade_enabled": bool(broker_account.auto_trade_enabled),
    }


def is_market_open_kst(now_utc: datetime | None = None) -> bool:
    """간단한 한국 장중 체크: 평일 09:00~15:30 KST."""
    now_utc = now_utc or datetime.utcnow()
    now_kst = now_utc + timedelta(hours=9)
    if now_kst.weekday() >= 5:
        return False
    hhmm = now_kst.hour * 100 + now_kst.minute
    return 900 <= hhmm <= 1530


def evaluate_rule_guard(db: Session, rule: AutoTradeRule) -> tuple[bool, str]:
    """장중/쿨다운/중복 주문 방지 검증."""
    if not rule.enabled:
        return False, "rule_disabled"
    if not is_market_open_kst():
        return False, "market_closed"

    cooldown = int(rule.cooldown_seconds or "300")
    if rule.last_triggered_at and datetime.utcnow() < (rule.last_triggered_at + timedelta(seconds=cooldown)):
        return False, "cooldown"

    duplicate_pending = (
        db.query(InvestmentOrder)
        .filter(
            InvestmentOrder.user_id == rule.user_id,
            InvestmentOrder.account_id == rule.account_id,
            InvestmentOrder.ticker == rule.ticker,
            InvestmentOrder.side == rule.side,
            InvestmentOrder.status.in_(["pending", "partially_filled"]),
        )
        .first()
    )
    if duplicate_pending:
        return False, "duplicate_pending_order"
    return True, "ok"


def create_run_log(
    db: Session,
    *,
    user_id: str,
    rule_id: str,
    account_id: str,
    ticker: str,
    status: str,
    reason: str | None = None,
    order_id: str | None = None,
) -> None:
    db.add(
        AutoTradeRunLog(
            id=f"arl_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            rule_id=rule_id,
            account_id=account_id,
            ticker=ticker,
            status=status,
            reason=reason,
            order_id=order_id,
        )
    )
    db.commit()
