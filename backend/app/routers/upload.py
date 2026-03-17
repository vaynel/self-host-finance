"""File upload routes."""

from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Optional
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.schemas.common import success_response
from app.services.upload_service import import_transactions
from app.services.smart_upload_parser import (
    parse_csv_smart,
    parse_xlsx_smart,
    extract_csv_headers_and_samples,
    extract_xlsx_headers_and_samples,
)
from app.services.category_classifier import auto_classify_category, auto_detect_type
from app.services.parsing_strategy_service import get_or_create_strategy, mapping_to_index_map

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/preview")
async def preview_transactions(
    file: UploadFile = File(...),
    format: Optional[str] = Form(None),
    accountId: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """
    Preview transactions from CSV or XLSX without importing.
    Returns parsed rows with auto-classification applied.
    """
    content = await file.read()
    ext = (file.filename or "").lower().split(".")[-1] if file.filename else ""
    fmt = format or ext

    # Strategy: match or infer via LLM (if key available). Fall back to heuristic on failure.
    index_override = None
    try:
        if fmt in ("csv", "txt"):
            headers, samples = extract_csv_headers_and_samples(content)
        else:
            headers, samples = extract_xlsx_headers_and_samples(content)
        if db and headers:
            strat = await get_or_create_strategy(db, current_user.id, headers, samples)
            index_override = mapping_to_index_map(headers, strat.mapping)
    except Exception:
        index_override = None
    
    # Use smart parser
    if fmt in ("csv", "txt"):
        rows, column_mapping = parse_csv_smart(content, index_mapping_override=index_override)
    elif fmt in ("xlsx", "xls"):
        rows, column_mapping = parse_xlsx_smart(content, index_mapping_override=index_override)
    else:
        # Try by content
        if content[:4] == b"PK\x03\x04":
            rows, column_mapping = parse_xlsx_smart(content, index_mapping_override=index_override)
        else:
            rows, column_mapping = parse_csv_smart(content, index_mapping_override=index_override)
    
    # Get account name if accountId provided
    account_name = None
    if accountId and db:
        from app.services.account_service import get_account
        acc = get_account(db, current_user.id, accountId)
        account_name = acc["name"] if acc else accountId
    
    # Apply auto-classification to preview
    preview_rows = []
    for i, row in enumerate(rows):
        if not row.get("date") or not row.get("description"):
            continue
        
        amount = row.get("amount", 0)
        description = row.get("description", "")
        account = row.get("account") or account_name or ""
        
        # Auto-detect type if not provided
        if not row.get("type"):
            row["type"] = auto_detect_type(amount, description)
        
        # Auto-classify category if not provided
        if not row.get("category") and db:
            row["category"] = auto_classify_category(db, current_user.id, description, amount)
        
        row["account"] = account
        
        preview_rows.append({
            "row": i + 1,
            "date": row.get("date"),
            "description": row.get("description"),
            "amount": row.get("amount", 0),
            "type": row.get("type", "expense"),
            "category": row.get("category", "기타"),
            "account": row.get("account", ""),
            "memo": row.get("memo", ""),
        })
    
    return success_response({
        "rows": preview_rows,
        "column_mapping": column_mapping,
        "total": len(preview_rows),
    })


@router.post("/transactions")
async def upload_transactions(
    file: UploadFile = File(...),
    accountId: str = Form(...),
    format: Optional[str] = Form(None),
    skipDuplicates: Optional[bool] = Form(True),
    toleranceDays: Optional[int] = Form(0),
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """
    Import transactions from CSV or XLSX with smart parsing and auto-classification.
    
    Args:
        file: CSV or XLSX file
        accountId: Account ID to associate transactions with
        format: File format (csv, xlsx) - auto-detected if not provided
        skipDuplicates: Whether to skip duplicate transactions (default: True)
        toleranceDays: Number of days tolerance for duplicate date matching (default: 0)
    """
    content = await file.read()
    ext = (file.filename or "").lower().split(".")[-1] if file.filename else ""
    fmt = format or ext

    # Strategy: match or infer via LLM (if key available). Fall back to heuristic on failure.
    index_override = None
    try:
        if fmt in ("csv", "txt"):
            headers, samples = extract_csv_headers_and_samples(content)
        else:
            headers, samples = extract_xlsx_headers_and_samples(content)
        if db and headers:
            strat = await get_or_create_strategy(db, current_user.id, headers, samples)
            index_override = mapping_to_index_map(headers, strat.mapping)
    except Exception:
        index_override = None
    
    # Use smart parser
    if fmt in ("csv", "txt"):
        rows, column_mapping = parse_csv_smart(content, index_mapping_override=index_override)
    elif fmt in ("xlsx", "xls"):
        rows, column_mapping = parse_xlsx_smart(content, index_mapping_override=index_override)
    else:
        # Try by content
        if content[:4] == b"PK\x03\x04":
            rows, column_mapping = parse_xlsx_smart(content, index_mapping_override=index_override)
        else:
            rows, column_mapping = parse_csv_smart(content, index_mapping_override=index_override)
    
    # Get account name from accountId
    from app.services.account_service import get_account
    acc = get_account(db, current_user.id, accountId)
    account_name = acc["name"] if acc else accountId
    
    # Import with auto-classification and duplicate detection
    result = import_transactions(
        db,
        current_user.id,
        rows,
        account_name,
        auto_classify=True,
        skip_duplicates=skipDuplicates if skipDuplicates is not None else True,
        tolerance_days=toleranceDays if toleranceDays is not None else 0,
    )
    result["column_mapping"] = column_mapping  # Return mapping info for debugging
    return success_response(result)
