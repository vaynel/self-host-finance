"""File upload and transaction import logic."""

import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from app.services.transaction_service import create_transaction
from app.services.smart_upload_parser import parse_csv_smart, parse_xlsx_smart
from app.services.category_classifier import auto_classify_category, auto_detect_type
from app.services.duplicate_detector import is_duplicate_transaction
from app.core.security import create_txn_id
from datetime import date
from decimal import Decimal


def parse_csv(content: bytes, encoding: str = "utf-8-sig") -> list[dict[str, Any]]:
    """Parse CSV to list of row dicts. Expects headers: date, description, amount, type, category, account."""
    text = content.decode(encoding, errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for r in reader:
        if not r.get("date") or not r.get("description"):
            continue
        try:
            amount = float(r.get("amount", 0).replace(",", ""))
        except (ValueError, TypeError):
            amount = 0
        rows.append({
            "date": r.get("date", "").strip()[:10],
            "description": r.get("description", "").strip(),
            "amount": amount,
            "type": (r.get("type") or "expense").strip().lower(),
            "category": (r.get("category") or "기타").strip(),
            "account": (r.get("account") or "").strip(),
            "memo": (r.get("memo") or "").strip(),
        })
    return rows


def parse_xlsx(content: bytes) -> list[dict[str, Any]]:
    """Parse XLSX to list of row dicts using openpyxl."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = []
    headers = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            headers = [str(c).strip().lower() if c else "" for c in row]
            col_map = {h: idx for idx, h in enumerate(headers) if h}
            continue
        if not row:
            continue
        date_val = row[col_map.get("date", 0)] if "date" in col_map else ""
        desc = row[col_map.get("description", 1)] if "description" in col_map else ""
        if not date_val or not desc:
            continue
        try:
            if hasattr(date_val, "strftime"):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                date_str = str(date_val)[:10]
        except Exception:
            date_str = str(date_val)[:10]
        try:
            amount = float(row[col_map.get("amount", 2)] or 0)
        except (ValueError, TypeError):
            amount = 0
        def _cell(i: int, default: str = "") -> str:
            return str(row[i]) if i < len(row) and row[i] is not None else default

        type_val = _cell(col_map.get("type", 3), "expense").strip().lower() or "expense"
        rows.append({
            "date": date_str,
            "description": str(desc).strip(),
            "amount": amount,
            "type": type_val,
            "category": _cell(col_map.get("category", 4), "기타").strip(),
            "account": _cell(col_map.get("account", 5)).strip(),
            "memo": _cell(col_map.get("memo", 6)).strip(),
        })
    wb.close()
    return rows


def import_transactions(
    db: Session,
    user_id: str,
    rows: list[dict],
    account_name: str,
    auto_classify: bool = True,
    skip_duplicates: bool = True,
    tolerance_days: int = 0,
) -> dict:
    """
    Import transactions with auto-classification and duplicate detection.
    
    Args:
        db: Database session
        user_id: User ID
        rows: List of transaction rows to import
        account_name: Default account name
        auto_classify: Whether to auto-classify type and category
        skip_duplicates: Whether to skip duplicate transactions
        tolerance_days: Number of days tolerance for duplicate date matching
    
    Returns:
        {imported, skipped, errors, duplicates}
    """
    imported = 0
    skipped = 0
    duplicates = 0
    errors = []
    
    for i, row in enumerate(rows):
        if not row.get("date") or not row.get("description"):
            skipped += 1
            continue
        
        account = row.get("account") or account_name
        amount = row.get("amount", 0)
        description = row.get("description", "")
        
        # Auto-detect type if not provided
        if not row.get("type") or auto_classify:
            row["type"] = auto_detect_type(amount, description)
        
        # Auto-classify category if not provided
        if not row.get("category") or auto_classify:
            row["category"] = auto_classify_category(db, user_id, description, amount)
        
        row["account"] = account
        
        # Check for duplicates
        if skip_duplicates:
            try:
                txn_date = date.fromisoformat(row["date"])
                amount_decimal = Decimal(str(amount))
                if is_duplicate_transaction(db, user_id, txn_date, amount_decimal, description, account, tolerance_days):
                    duplicates += 1
                    skipped += 1
                    continue
            except Exception:
                # If date parsing fails, continue to try creating (will fail with proper error)
                pass
        
        try:
            create_transaction(db, user_id, row)
            imported += 1
        except Exception as e:
            errors.append({"row": i + 1, "message": str(e)})
    
    return {
        "imported": imported,
        "skipped": skipped,
        "duplicates": duplicates,
        "errors": errors,
    }
