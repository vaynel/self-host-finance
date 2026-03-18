"""Investment business logic."""

from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app.models.investment import InvestmentTrade
from app.models.investment_price import InvestmentPriceLatest, InvestmentPriceDaily
from app.core.security import create_trade_id
from app.core.exceptions import raise_404
from app.core.security import create_txn_id
from app.models.account import Account
from app.models.transaction import Transaction


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
    by_ticker = defaultdict(lambda: {"shares": 0.0, "cost": Decimal("0"), "name": "", "type": "stock"})
    for t in trades:
        s = float(t.shares)
        p = float(t.price)
        if t.action == "buy":
            by_ticker[t.ticker]["shares"] += s
            by_ticker[t.ticker]["cost"] += Decimal(str(s * p))
            by_ticker[t.ticker]["name"] = t.name or t.ticker
            by_ticker[t.ticker]["type"] = t.type or "stock"
        else:
            # Average-cost basis: reduce cost proportionally when selling.
            cur_shares = float(by_ticker[t.ticker]["shares"])
            if cur_shares <= 0:
                continue
            avg_cost = float(by_ticker[t.ticker]["cost"]) / cur_shares if cur_shares else 0.0
            by_ticker[t.ticker]["shares"] -= s
            by_ticker[t.ticker]["cost"] -= Decimal(str(avg_cost * s))
            if by_ticker[t.ticker]["shares"] <= 0:
                del by_ticker[t.ticker]

    tickers = list(by_ticker.keys())
    # latest price per ticker (if missing -> fallback to avg price computed from cost basis)
    latest_price_map: dict[str, float] = {}
    for ticker in tickers:
        lp = (
            db.query(InvestmentPriceLatest)
            .filter(InvestmentPriceLatest.user_id == user_id, InvestmentPriceLatest.ticker == ticker)
            .order_by(InvestmentPriceLatest.updated_at.desc())
            .first()
        )
        if lp and lp.price is not None:
            latest_price_map[ticker] = float(lp.price)
    result = []
    for ticker, h in by_ticker.items():
        if h["shares"] <= 0:
            continue
        avg = float(h["cost"]) / h["shares"] if h["shares"] else 0
        current_price = latest_price_map.get(ticker, avg)
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


def list_price_history(db: Session, user_id: str, ticker: str, *, period: str | None = None) -> list[dict]:
    """Return daily price history for chart.

    The frontend expects fields: date/open/high/low/close/volume.
    Currently we only store daily close; other fields are duplicated for compatibility.
    """
    days = 30
    if period:
        p = period.strip().lower()
        if p.endswith("d"):
            try:
                days = int(p[:-1])
            except Exception:
                days = 30
        elif p.endswith("w"):
            try:
                days = int(p[:-1]) * 7
            except Exception:
                days = 30

    cutoff = date.today() - timedelta(days=days)
    rows = (
        db.query(InvestmentPriceDaily)
        .filter(
            InvestmentPriceDaily.user_id == user_id,
            InvestmentPriceDaily.ticker == ticker,
            InvestmentPriceDaily.trade_date >= cutoff,
        )
        .order_by(InvestmentPriceDaily.trade_date.asc())
        .all()
    )

    return [
        {
            "ticker": ticker,
            "date": r.trade_date.isoformat(),
            "open": float(r.close),
            "high": float(r.close),
            "low": float(r.close),
            "close": float(r.close),
            "volume": 0,
        }
        for r in rows
    ]


def create_trade(db: Session, user_id: str, data: dict) -> dict:
    """Create investment trade and settle cash account (transaction + account.balance)."""
    account_id = data.get("accountId")
    cash_account: Account | None = None
    if account_id:
        cash_account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not cash_account:
        # Fallback: use first investment account, then first bank account.
        cash_account = db.query(Account).filter(Account.user_id == user_id, Account.type == "investment").first()
    if not cash_account:
        cash_account = db.query(Account).filter(Account.user_id == user_id, Account.type == "bank").first()
    if not cash_account:
        raise_404("정산할 계좌를 찾을 수 없습니다.")

    # Settles cash ledger into `transactions` and updates `accounts.balance`.
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
    # cash delta for settlement
    shares = Decimal(str(data["shares"]))
    price = Decimal(str(data["price"]))
    fee = Decimal(str(data.get("fee", 0))) if data.get("fee") else Decimal("0")
    trade_value = shares * price
    if data["action"] == "buy":
        cash_delta = -(trade_value + fee)  # cash decreases
        txn_type = "expense"
    else:
        # sell proceeds: decrease fee from proceeds
        cash_delta = trade_value - fee
        txn_type = "income"

    # Create corresponding transaction ledger
    txn = Transaction(
        id=create_txn_id(),
        user_id=user_id,
        date=date.fromisoformat(data["date"]),
        description=f"{(data.get('name') or data['ticker'])} {data['action']}",
        amount=cash_delta,
        type=txn_type,
        category="투자",
        account=cash_account.name,
        memo=f"{data['ticker']} {data['action']} {shares}주",
    )
    db.add(txn)

    # Update account balance
    cash_account.balance = cash_account.balance + cash_delta

    db.commit()
    db.refresh(t)
    return _trade_to_dict(t)
