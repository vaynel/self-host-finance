"""Transaction business logic."""

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.transaction import Transaction
from app.models.account import Account
from app.models.user import User
from app.core.security import create_txn_id
from app.core.exceptions import raise_404, raise_403


def _txn_to_dict(t: Transaction) -> dict:
    return {
        "id": t.id,
        "date": t.date.isoformat() if t.date else "",
        "description": t.description,
        "amount": float(t.amount),
        "type": t.type,
        "category": t.category,
        "account": t.account,
        "memo": t.memo or "",
    }


def list_transactions(
    db: Session,
    user_id: str,
    page: int = 1,
    limit: int = 20,
    type_filter: Optional[str] = None,
    category: Optional[str] = None,
    account: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[dict], int]:
    """List transactions with filters and pagination."""
    q = db.query(Transaction).filter(Transaction.user_id == user_id)
    if type_filter:
        q = q.filter(Transaction.type == type_filter)
    if category:
        q = q.filter(Transaction.category == category)
    if account:
        q = q.filter(Transaction.account == account)
    if start_date:
        q = q.filter(Transaction.date >= date.fromisoformat(start_date))
    if end_date:
        q = q.filter(Transaction.date <= date.fromisoformat(end_date))
    if search:
        q = q.filter(Transaction.description.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(Transaction.date.desc()).offset((page - 1) * limit).limit(min(limit, 100)).all()
    return [_txn_to_dict(t) for t in items], total


def get_transaction(db: Session, user_id: str, txn_id: str) -> Optional[dict]:
    """Get single transaction."""
    t = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == user_id).first()
    if not t:
        return None
    return _txn_to_dict(t)


def create_transaction(db: Session, user_id: str, data: dict) -> dict:
    """Create transaction."""
    amount = Decimal(str(data["amount"]))
    t = Transaction(
        id=create_txn_id(),
        user_id=user_id,
        date=date.fromisoformat(data["date"]),
        description=data["description"],
        amount=amount,
        type=data["type"],
        category=data["category"],
        account=data["account"],
        memo=data.get("memo") or "",
    )
    db.add(t)

    # Keep account balance in sync with transaction ledger.
    # (income:+, expense:-, transfer can be +/- depending on direction)
    account = db.query(Account).filter(Account.user_id == user_id, Account.name == data["account"]).first()
    if account:
        account.balance = account.balance + amount

    db.commit()
    db.refresh(t)
    return _txn_to_dict(t)


def update_transaction(db: Session, user_id: str, txn_id: str, data: dict) -> dict:
    """Update transaction."""
    t = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == user_id).first()
    if not t:
        raise_404("거래를 찾을 수 없습니다.")

    old_amount = Decimal(str(t.amount))
    old_account_name = t.account

    for k, v in data.items():
        if v is not None:
            if k == "date":
                t.date = date.fromisoformat(v)
            elif k == "amount":
                t.amount = Decimal(str(v))
            else:
                setattr(t, k, v)

    new_amount = Decimal(str(t.amount))
    new_account_name = t.account

    # Reconcile account balances: revert old impact, then apply new impact.
    old_account = db.query(Account).filter(Account.user_id == user_id, Account.name == old_account_name).first()
    if old_account:
        old_account.balance = old_account.balance - old_amount

    new_account = db.query(Account).filter(Account.user_id == user_id, Account.name == new_account_name).first()
    if new_account:
        new_account.balance = new_account.balance + new_amount

    db.commit()
    db.refresh(t)
    return _txn_to_dict(t)


def delete_transaction(db: Session, user_id: str, txn_id: str) -> None:
    """Delete transaction."""
    t = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == user_id).first()
    if not t:
        raise_404("거래를 찾을 수 없습니다.")

    # Revert account balance impact before deletion.
    account = db.query(Account).filter(Account.user_id == user_id, Account.name == t.account).first()
    if account:
        account.balance = account.balance - Decimal(str(t.amount))

    db.delete(t)
    db.commit()
