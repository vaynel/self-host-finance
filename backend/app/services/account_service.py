"""Account business logic."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.account import Account
from app.models.transaction import Transaction
from app.core.security import create_account_id
from app.core.exceptions import raise_404


def _acc_to_dict(a: Account) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "type": a.type,
        "balance": float(a.balance),
        "institution": a.institution,
        "lastSync": a.last_sync.isoformat() if a.last_sync else None,
    }


def list_accounts(db: Session, user_id: str) -> list[dict]:
    """List user accounts."""
    rows = db.query(Account).filter(Account.user_id == user_id).all()
    return [_acc_to_dict(a) for a in rows]


def get_account(db: Session, user_id: str, account_id: str) -> dict | None:
    """Get single account."""
    a = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not a:
        return None
    return _acc_to_dict(a)


def create_account(db: Session, user_id: str, data: dict) -> dict:
    """Create account."""
    a = Account(
        id=create_account_id(),
        user_id=user_id,
        name=data["name"],
        type=data["type"],
        balance=Decimal(str(data["balance"])),
        institution=data["institution"],
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _acc_to_dict(a)


def update_account(db: Session, user_id: str, account_id: str, data: dict) -> dict:
    """Update account."""
    a = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not a:
        raise_404("계좌를 찾을 수 없습니다.")
    for k, v in data.items():
        if v is not None:
            if k == "balance":
                a.balance = Decimal(str(v))
            else:
                setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _acc_to_dict(a)


def delete_account(db: Session, user_id: str, account_id: str) -> None:
    """Delete account."""
    a = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not a:
        raise_404("계좌를 찾을 수 없습니다.")
    db.delete(a)
    db.commit()


def get_account_flow(db: Session, user_id: str, account_id: str, period: str = "30d") -> dict:
    """Get balance flow for account over period."""
    a = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not a:
        raise_404("계좌를 찾을 수 없습니다.")
    days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period, 30)
    end = date.today()
    start = end - timedelta(days=days)
    txns = (
        db.query(Transaction.date, func.sum(Transaction.amount).label("delta"))
        .filter(
            Transaction.user_id == user_id,
            Transaction.account == a.name,
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .group_by(Transaction.date)
        .order_by(Transaction.date)
        .all()
    )
    balance_map = {}
    running = float(a.balance)
    for d, delta in reversed(list(txns)):
        balance_map[d.isoformat()] = running
        running -= float(delta)
    chart_data = [{"date": k, "balance": v} for k, v in sorted(balance_map.items())]
    if not chart_data and a.balance:
        chart_data = [{"date": end.isoformat(), "balance": float(a.balance)}]
    return {"accountId": account_id, "chartData": chart_data}
