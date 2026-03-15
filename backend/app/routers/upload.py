"""File upload routes."""

from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Optional

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.schemas.common import success_response
from app.services.upload_service import parse_csv, parse_xlsx, import_transactions

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/transactions")
async def upload_transactions(
    file: UploadFile = File(...),
    accountId: str = Form(...),
    format: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Import transactions from CSV or XLSX."""
    content = await file.read()
    ext = (file.filename or "").lower().split(".")[-1] if file.filename else ""
    fmt = format or ext
    if fmt in ("csv", "txt"):
        rows = parse_csv(content)
    elif fmt in ("xlsx", "xls"):
        rows = parse_xlsx(content)
    else:
        # Try by content
        if content[:4] == b"PK\x03\x04":
            rows = parse_xlsx(content)
        else:
            rows = parse_csv(content)
    # Get account name from accountId - for now use a placeholder if account not found
    from app.services.account_service import get_account
    acc = get_account(db, current_user.id, accountId)
    account_name = acc["name"] if acc else accountId
    result = import_transactions(db, current_user.id, rows, account_name)
    return success_response(result)
