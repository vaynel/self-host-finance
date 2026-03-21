"""Investment business logic."""

from datetime import date, timedelta, datetime
from decimal import Decimal
from collections import defaultdict
from typing import Optional
import uuid

import requests

from sqlalchemy.orm import Session

from app.models.investment import InvestmentTrade
from app.models.investment_price import InvestmentPriceLatest, InvestmentPriceDaily
from app.models.investment_snapshot import InvestmentHoldingSnapshot, InvestmentCashSnapshot
from app.models.investment_peak import InvestmentPeakTracker
from app.models.broker_account import BrokerAccount
from app.core.security import create_trade_id
from app.core.exceptions import raise_404, raise_400
from app.core.security import create_txn_id
from app.models.account import Account
from app.models.transaction import Transaction
from app.brokers.kis import KISAdapter


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
    """Return holdings from latest snapshot first, fallback to trade aggregation."""
    snapshot_rows = (
        db.query(InvestmentHoldingSnapshot)
        .filter(InvestmentHoldingSnapshot.user_id == user_id)
        .order_by(InvestmentHoldingSnapshot.synced_at.desc())
        .all()
    )
    if snapshot_rows:
        # Keep only latest sync batch per (account_id, ticker)
        latest: dict[tuple[str, str], InvestmentHoldingSnapshot] = {}
        for row in snapshot_rows:
            key = (row.account_id, row.ticker)
            if key not in latest:
                latest[key] = row

        result: list[dict] = []
        for row in latest.values():
            qty = float(row.quantity)
            avg_price = float(row.average_price)
            cur_price = float(row.current_price)
            valuation = float(row.valuation)
            cost = qty * avg_price
            pl = valuation - cost
            pl_rate = (pl / cost * 100) if cost else 0.0
            result.append(
                {
                    "ticker": row.ticker,
                    "name": row.name or row.ticker,
                    "type": "stock",
                    "shares": qty,
                    "avgPrice": round(avg_price, 2),
                    "currentPrice": round(cur_price, 2),
                    "totalValue": round(valuation, 2),
                    "profitLoss": round(pl, 2),
                    "profitLossRate": round(pl_rate, 2),
                    "source": "snapshot",
                    "accountId": row.account_id,
                }
            )
        return result

    return _get_holdings_from_trades(db, user_id)


def _get_holdings_from_trades(db: Session, user_id: str) -> list[dict]:
    """Aggregate holdings by ticker from local trade ledger."""
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
        result.append(
            {
                "ticker": ticker,
                "name": h["name"],
                "type": h["type"],
                "shares": h["shares"],
                "avgPrice": round(avg, 2),
                "currentPrice": round(current_price, 2),
                "totalValue": round(total_value, 2),
                "profitLoss": round(pl, 2),
                "profitLossRate": round(pl_rate, 2),
                "source": "trade_fallback",
            }
        )
    return result


def sync_holdings_snapshot(db: Session, user_id: str, account_id: str) -> dict:
    """Sync holdings/cash from KIS and store snapshots."""
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not account:
        raise_404("계좌를 찾을 수 없습니다.")

    broker_account = (
        db.query(BrokerAccount)
        .filter(
            BrokerAccount.account_id == account_id,
            BrokerAccount.broker_type == "KIS",
        )
        .first()
    )
    if not broker_account:
        raise_404(
            "한국투자증권(KIS) OpenAPI 연동이 없습니다. "
            "먼저 해당 계좌에서 「KIS 연동」으로 CANO·상품코드를 등록하고 토큰 발급을 완료한 뒤 동기화하세요.",
        )
    if not broker_account.api_enabled:
        raise_400(
            "KIS 연동(connect) 및 토큰 발급이 완료되어야 동기화가 가능합니다.",
            details=[{"account_id": account_id}],
        )

    adapter = KISAdapter(db, broker_account)
    synced_at = datetime.utcnow()

    try:
        holdings = adapter.get_holdings()
        cash = adapter.get_balance()
    except ValueError as e:
        raise_400(
            str(e),
            details=[
                {
                    "hint": "연동 시 상품코드는 자동 설정됩니다. 계속 실패하면 「KIS 연동」에서 계좌번호(연속계좌 앞 8자리)와 모의/실전 여부를 다시 확인하세요.",
                }
            ],
        )
    except requests.RequestException as e:
        raise_400(f"한국투자증권 API 연결 실패: {e}")

    # Remove previous snapshots for this account, then write the latest full snapshot.
    db.query(InvestmentHoldingSnapshot).filter(
        InvestmentHoldingSnapshot.user_id == user_id,
        InvestmentHoldingSnapshot.account_id == account_id,
    ).delete()
    db.query(InvestmentCashSnapshot).filter(
        InvestmentCashSnapshot.user_id == user_id,
        InvestmentCashSnapshot.account_id == account_id,
    ).delete()

    for item in holdings:
        # peak tracker upsert: max(existing, current_price)
        try:
            ticker = item.get("ticker", "")
            current_price = Decimal(str(item.get("current_price", 0)))
            if ticker and current_price > 0:
                existing_peak = (
                    db.query(InvestmentPeakTracker)
                    .filter(
                        InvestmentPeakTracker.user_id == user_id,
                        InvestmentPeakTracker.account_id == account_id,
                        InvestmentPeakTracker.ticker == ticker,
                    )
                    .first()
                )
                if existing_peak:
                    if current_price > existing_peak.peak_price:
                        existing_peak.peak_price = current_price
                        existing_peak.updated_at = datetime.utcnow()
                else:
                    db.add(
                        InvestmentPeakTracker(
                            id=f"ipt_{uuid.uuid4().hex[:12]}",
                            user_id=user_id,
                            account_id=account_id,
                            ticker=ticker,
                            peak_price=current_price,
                        )
                    )
        except Exception:
            # peak 저장 실패는 동기화를 막지 않음
            pass
        db.add(
            InvestmentHoldingSnapshot(
                id=f"ihs_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                account_id=account_id,
                ticker=item.get("ticker", ""),
                name=item.get("name"),
                quantity=Decimal(str(item.get("quantity", 0))),
                average_price=Decimal(str(item.get("average_price", 0))),
                current_price=Decimal(str(item.get("current_price", 0))),
                valuation=Decimal(str(item.get("valuation", 0))),
                synced_at=synced_at,
            )
        )

    db.add(
        InvestmentCashSnapshot(
            id=f"ics_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            account_id=account_id,
            cash_balance=Decimal(str(cash.get("cash_balance", 0))),
            orderable_cash=Decimal(str(cash.get("orderable_cash", 0))),
            currency=cash.get("currency", "KRW"),
            synced_at=synced_at,
        )
    )

    broker_account.last_balance_sync_at = synced_at
    db.commit()

    return {
        "accountId": account_id,
        "holdingsCount": len(holdings),
        "cashBalance": float(Decimal(str(cash.get("cash_balance", 0)))),
        "orderableCash": float(Decimal(str(cash.get("orderable_cash", 0)))),
        "syncedAt": synced_at.isoformat(),
    }


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
