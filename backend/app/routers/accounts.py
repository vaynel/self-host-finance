"""Account routes."""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.common import success_response
from app.services.account_service import (
    list_accounts,
    get_account,
    create_account,
    update_account,
    delete_account,
    get_account_flow,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accs(current_user: User = Depends(get_current_user), db: DbSession = None):
    """List accounts."""
    items = list_accounts(db, current_user.id)
    return success_response(items)


@router.get("/{account_id}")
def get_acc(account_id: str, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Get single account."""
    a = get_account(db, current_user.id, account_id)
    if not a:
        from app.core.exceptions import raise_404
        raise_404("계좌를 찾을 수 없습니다.")
    return success_response(a)


@router.get("/{account_id}/flow")
def flow(account_id: str, period: str = Query("30d"), current_user: User = Depends(get_current_user), db: DbSession = None):
    """Get account balance flow."""
    data = get_account_flow(db, current_user.id, account_id, period)
    return success_response(data)


@router.post("")
def create_acc(req: AccountCreate, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Create account."""
    data = req.model_dump()
    a = create_account(db, current_user.id, data)
    return success_response(a)


@router.put("/{account_id}")
def update_acc(account_id: str, req: AccountUpdate, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Update account."""
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not data:
        a = get_account(db, current_user.id, account_id)
        if not a:
            from app.core.exceptions import raise_404
            raise_404("계좌를 찾을 수 없습니다.")
        return success_response(a)
    a = update_account(db, current_user.id, account_id, data)
    return success_response(a)


@router.delete("/{account_id}")
def delete_acc(account_id: str, current_user: User = Depends(get_current_user), db: DbSession = None):
    """Delete account."""
    delete_account(db, current_user.id, account_id)
    return success_response({"message": "삭제되었습니다."})
