"""Duplicate transaction detection service."""

from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.transaction import Transaction


def is_duplicate_transaction(
    db: Session,
    user_id: str,
    txn_date: date,
    amount: Decimal,
    description: str,
    account: str,
    tolerance_days: int = 0,
) -> bool:
    """
    Check if a transaction is duplicate.
    
    Args:
        db: Database session
        user_id: User ID
        txn_date: Transaction date
        amount: Transaction amount
        description: Transaction description (normalized)
        account: Account name
        tolerance_days: Number of days tolerance for date matching (default: 0 = exact match)
    
    Returns:
        True if duplicate found, False otherwise
    """
    # Normalize description (lowercase, strip whitespace)
    normalized_desc = description.lower().strip()
    
    # Build query
    query = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.amount == amount,
        Transaction.account == account,
    )
    
    # Date matching with tolerance
    if tolerance_days == 0:
        query = query.filter(Transaction.date == txn_date)
    else:
        from datetime import timedelta
        start_date = txn_date - timedelta(days=tolerance_days)
        end_date = txn_date + timedelta(days=tolerance_days)
        query = query.filter(
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
    
    # Check for matching transactions
    existing = query.all()
    
    # Check description similarity (exact match or contains)
    for txn in existing:
        existing_desc = txn.description.lower().strip()
        # Exact match or one contains the other (for slight variations)
        if normalized_desc == existing_desc or normalized_desc in existing_desc or existing_desc in normalized_desc:
            return True
    
    return False


def find_duplicate_transactions(
    db: Session,
    user_id: str,
    rows: list[dict],
    account_name: str,
    tolerance_days: int = 0,
) -> list[dict]:
    """
    Find duplicate transactions in the import rows.
    
    Returns list of duplicate row indices and their matching transaction info.
    """
    duplicates = []
    
    for i, row in enumerate(rows):
        if not row.get("date") or not row.get("description"):
            continue
        
        try:
            txn_date = date.fromisoformat(row["date"])
            amount = Decimal(str(row.get("amount", 0)))
            description = row["description"]
            account = row.get("account") or account_name
            
            if is_duplicate_transaction(db, user_id, txn_date, amount, description, account, tolerance_days):
                duplicates.append({
                    "row": i + 1,
                    "date": row["date"],
                    "description": description,
                    "amount": float(amount),
                    "account": account,
                })
        except Exception:
            # Skip invalid rows
            continue
    
    return duplicates
