"""Investment business logic."""

from datetime import date
from decimal import Decimal
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app.models.investment import InvestmentTrade
from app.core.security import create_trade_id
from app.core.exceptions import raise_404


def _trade_to_dict(t: InvestmentTrade) -> dict:
    return {
        "id": t.id,
        "ticker": t.ticker,
        "name": t.name,
        "type": t.type,
        "action": t.action,
        "date": t.date.isoformat() if t.date else "",
        "shares": float(t.shares),
        "price": float(t.price),
        "fee": float(t.fee) if t.fee else None,
    }


def get_holdings(db: Session, user_id: str) -> list[dict]:
    """Aggregate holdings by ticker (simplified: no external price API)."""
    trades = db.query(InvestmentTrade).filter(InvestmentTrade.user_id == user_id).order_by(InvestmentTrade.date).all()
    by_ticker = defaultdict(lambda: {"shares": 0, "cost": Decimal("0"), "name": "", "type": "stock"})
    for t in trades:
        s = float(t.shares)
        p = float(t.price)
        if t.action == "buy":
            by_ticker[t.ticker]["shares"] += s
            by_ticker[t.ticker]["cost"] += Decimal(str(s * p))
            by_ticker[t.ticker]["name"] = t.name or t.ticker
            by_ticker[t.ticker]["type"] = t.type or "stock"
        else:
            by_ticker[t.ticker]["shares"] -= s
            if by_ticker[t.ticker]["shares"] <= 0:
                del by_ticker[t.ticker]
    result = []
    for ticker, h in by_ticker.items():
        if h["shares"] <= 0:
            continue
        avg = float(h["cost"]) / h["shares"] if h["shares"] else 0
        current_price = avg  # Mock: use avg as current price (no external API)
        total_value = h["shares"] * current_price
        pl = total_value - float(h["cost"])
        pl_rate = (pl / float(h["cost"]) * 100) if h["cost"] else 0
        result.append({
            "ticker": ticker,
            "name": h["name"],
            "type": h["type"],
            "shares": h["shares"],
            "avgPrice": round(avg, 2),
            "currentPrice": round(current_price, 2),
            "totalValue": round(total_value, 2),
            "profitLoss": round(pl, 2),
            "profitLossRate": round(pl_rate, 2),
        })
    return result


def list_trades(
    db: Session,
    user_id: str,
    ticker: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict]:
    """List investment trades with filters."""
    q = db.query(InvestmentTrade).filter(InvestmentTrade.user_id == user_id)
    if ticker:
        q = q.filter(InvestmentTrade.ticker == ticker)
    if action:
        q = q.filter(InvestmentTrade.action == action)
    if start_date:
        q = q.filter(InvestmentTrade.date >= date.fromisoformat(start_date))
    if end_date:
        q = q.filter(InvestmentTrade.date <= date.fromisoformat(end_date))
    rows = q.order_by(InvestmentTrade.date.desc()).all()
    return [_trade_to_dict(t) for t in rows]


def create_trade(db: Session, user_id: str, data: dict) -> dict:
    """Create investment trade."""
    t = InvestmentTrade(
        id=create_trade_id(),
        user_id=user_id,
        ticker=data["ticker"],
        name=data.get("name"),
        type=data.get("type", "stock"),
        action=data["action"],
        date=date.fromisoformat(data["date"]),
        shares=Decimal(str(data["shares"])),
        price=Decimal(str(data["price"])),
        fee=Decimal(str(data.get("fee", 0))) if data.get("fee") else None,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _trade_to_dict(t)
