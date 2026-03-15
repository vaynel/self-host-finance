"""Transaction routes."""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from app.schemas.common import success_response, MetaSchema
from app.services.transaction_service import (
    list_transactions,
    get_transaction,
    create_transaction,
    update_transaction,
    delete_transaction,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
def list_txns(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, alias="type"),
    category: Optional[str] = None,
    account: Optional[str] = None,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    search: Optional[str] = None,
):
    """List transactions with filters."""
    items, total = list_transactions(
        db, current_user.id,
        page=page, limit=limit,
        type_filter=type,
        category=category,
        account=account,
        start_date=startDate,
        end_date=endDate,
        search=search,
    )
    meta = {"page": page, "limit": limit, "total": total}
    return success_response(items, meta)


@router.get("/{txn_id}")
def get_txn(txn_id: str, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Get single transaction."""
    t = get_transaction(db, current_user.id, txn_id)
    if not t:
        from app.core.exceptions import raise_404
        raise_404("거래를 찾을 수 없습니다.")
    return success_response(t)


@router.post("")
def create_txn(req: TransactionCreate, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Create transaction."""
    data = req.model_dump()
    t = create_transaction(db, current_user.id, data)
    return success_response(t)


@router.put("/{txn_id}")
def update_txn(txn_id: str, req: TransactionUpdate, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Update transaction."""
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not data:
        t = get_transaction(db, current_user.id, txn_id)
        if not t:
            from app.core.exceptions import raise_404
            raise_404("거래를 찾을 수 없습니다.")
        return success_response(t)
    t = update_transaction(db, current_user.id, txn_id, data)
    return success_response(t)


@router.delete("/{txn_id}")
def delete_txn(txn_id: str, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Delete transaction."""
    delete_transaction(db, current_user.id, txn_id)
    return success_response({"message": "삭제되었습니다."})
