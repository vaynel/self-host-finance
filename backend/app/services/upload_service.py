"""File upload and transaction import logic."""

import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from app.services.transaction_service import create_transaction
from app.core.security import create_txn_id


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
) -> dict:
    """Import transactions. Returns {imported, skipped, errors}."""
    imported = 0
    skipped = 0
    errors = []
    for i, row in enumerate(rows):
        if not row.get("date") or not row.get("description"):
            skipped += 1
            continue
        account = row.get("account") or account_name
        row["account"] = account
        try:
            create_transaction(db, user_id, row)
            imported += 1
        except Exception as e:
            errors.append({"row": i + 1, "message": str(e)})
    return {"imported": imported, "skipped": skipped, "errors": errors}
