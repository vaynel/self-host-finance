"""Smart parser for CSV/Excel files with flexible column mapping."""

import csv
import io
import re
from typing import Any, Optional
from datetime import datetime


def extract_csv_headers_and_samples(content: bytes, encoding: str = "utf-8-sig", sample_n: int = 5) -> tuple[list[str], list[list[Any]]]:
    """Extract CSV headers and a few raw sample rows (as lists)."""
    text = content.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(text))
    headers = next(reader, [])
    samples: list[list[Any]] = []
    for _ in range(sample_n):
        r = next(reader, None)
        if r is None:
            break
        samples.append(r)
    return [str(h).strip() for h in headers], samples


def extract_xlsx_headers_and_samples(content: bytes, sample_n: int = 5) -> tuple[list[str], list[list[Any]]]:
    """Extract XLSX headers and a few raw sample rows (as lists) from the first sheet."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
    samples: list[list[Any]] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row is None:
            continue
        samples.append(list(row))
        if len(samples) >= sample_n:
            break
    wb.close()
    return headers, samples


def detect_column_mapping(headers: list[str]) -> dict[str, Optional[int]]:
    """Detect column mapping from headers for various bank formats."""
    mapping: dict[str, Optional[int]] = {
        "date": None,
        "description": None,
        "amount": None,
        "type": None,
        "category": None,
        "account": None,
        "memo": None,
        "balance": None,  # 잔액 (optional)
    }
    
    # Normalize headers (lowercase, strip, remove special chars)
    normalized_headers = []
    for i, h in enumerate(headers):
        if h:
            normalized = str(h).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
            normalized_headers.append((i, normalized, h))
    
    # Date column detection
    date_patterns = ["날짜", "date", "거래일자", "거래일", "일자", "일시", "거래시각"]
    for idx, norm, orig in normalized_headers:
        if any(pattern in norm for pattern in date_patterns):
            mapping["date"] = idx
            break
    
    # Description column detection
    desc_patterns = ["내역", "거래내역", "description", "적요", "거래적요", "내용", "거래내용", "메모", "비고", "적요명"]
    for idx, norm, orig in normalized_headers:
        if any(pattern in norm for pattern in desc_patterns):
            mapping["description"] = idx
            break
    
    # Amount column detection
    amount_patterns = ["금액", "amount", "거래금액", "입금", "출금", "수입", "지출", "변동금액"]
    for idx, norm, orig in normalized_headers:
        if any(pattern in norm for pattern in amount_patterns):
            mapping["amount"] = idx
            break
    
    # Balance column detection (optional)
    balance_patterns = ["잔액", "balance", "거래후잔액", "잔고"]
    for idx, norm, orig in normalized_headers:
        if any(pattern in norm for pattern in balance_patterns):
            mapping["balance"] = idx
            break
    
    # Type column detection (optional)
    type_patterns = ["구분", "type", "유형", "거래구분", "입출금"]
    for idx, norm, orig in normalized_headers:
        if any(pattern in norm for pattern in type_patterns):
            mapping["type"] = idx
            break
    
    # Category column detection (optional)
    category_patterns = ["카테고리", "category", "분류", "항목"]
    for idx, norm, orig in normalized_headers:
        if any(pattern in norm for pattern in category_patterns):
            mapping["category"] = idx
            break
    
    # Account column detection (optional)
    account_patterns = ["계좌", "account", "계좌번호", "계좌명", "은행"]
    for idx, norm, orig in normalized_headers:
        if any(pattern in norm for pattern in account_patterns):
            mapping["account"] = idx
            break
    
    # Memo column detection (optional)
    memo_patterns = ["메모", "memo", "비고", "참고", "기타"]
    for idx, norm, orig in normalized_headers:
        if any(pattern in norm for pattern in memo_patterns):
            mapping["memo"] = idx
            break
    
    return mapping


def apply_index_mapping(base: dict[str, Optional[int]], override: dict[str, Optional[int]] | None) -> dict[str, Optional[int]]:
    """
    Merge an override index mapping into the base mapping.
    """
    if not override:
        return base
    merged = dict(base)
    for k, v in override.items():
        if k in merged and v is not None:
            merged[k] = v
    return merged


def parse_amount(value: Any) -> float:
    """Parse amount from various formats."""
    if value is None:
        return 0.0
    
    # Convert to string
    str_value = str(value).strip()
    
    # Remove currency symbols and spaces
    str_value = re.sub(r'[₩$€£,\s]', '', str_value)
    
    # Handle negative amounts (parentheses, minus sign)
    is_negative = False
    if str_value.startswith('(') and str_value.endswith(')'):
        is_negative = True
        str_value = str_value[1:-1]
    elif str_value.startswith('-'):
        is_negative = True
        str_value = str_value[1:]
    
    try:
        amount = float(str_value)
        return -amount if is_negative else amount
    except (ValueError, TypeError):
        return 0.0


def parse_date(value: Any) -> Optional[str]:
    """Parse date from various formats."""
    if value is None:
        return None
    
    # If it's already a datetime object
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d')
    
    str_value = str(value).strip()
    
    # Try common date formats
    date_formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y.%m.%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y%m%d',
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(str_value, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # If all formats fail, try to extract YYYY-MM-DD pattern
    match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', str_value)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return None


def parse_csv_smart(
    content: bytes,
    encoding: str = "utf-8-sig",
    *,
    index_mapping_override: dict[str, Optional[int]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Optional[int]]]:
    """Parse CSV with smart column detection. Returns (rows, column_mapping)."""
    text = content.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(text))
    
    # Read first row as headers
    headers = next(reader, [])
    if not headers:
        return [], {}
    
    # Detect column mapping
    mapping = apply_index_mapping(detect_column_mapping(headers), index_mapping_override)
    
    rows = []
    for row in reader:
        if not row or all(not cell or str(cell).strip() == "" for cell in row):
            continue
        
        # Extract values using mapping
        date_val = parse_date(row[mapping["date"]]) if mapping["date"] is not None and mapping["date"] < len(row) else None
        description = str(row[mapping["description"]]).strip() if mapping["description"] is not None and mapping["description"] < len(row) else ""
        amount_val = parse_amount(row[mapping["amount"]]) if mapping.get("amount") is not None and mapping["amount"] < len(row) else 0.0
        type_val = str(row[mapping["type"]]).strip().lower() if mapping["type"] is not None and mapping["type"] < len(row) else None
        category_val = str(row[mapping["category"]]).strip() if mapping["category"] is not None and mapping["category"] < len(row) else None
        account_val = str(row[mapping["account"]]).strip() if mapping["account"] is not None and mapping["account"] < len(row) else None
        memo_val = str(row[mapping["memo"]]).strip() if mapping["memo"] is not None and mapping["memo"] < len(row) else None
        
        # Skip if essential fields are missing
        if not date_val or not description:
            continue
        
        rows.append({
            "date": date_val,
            "description": description,
            "amount": amount_val,
            "type": type_val,
            "category": category_val,
            "account": account_val,
            "memo": memo_val or "",
        })
    
    return rows, mapping


def parse_xlsx_smart(
    content: bytes,
    *,
    index_mapping_override: dict[str, Optional[int]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Optional[int]]]:
    """Parse XLSX with smart column detection. Returns (rows, column_mapping)."""
    import openpyxl
    
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    
    # Read first row as headers
    headers = []
    for cell in ws[1]:
        headers.append(str(cell.value).strip() if cell.value else "")
    
    if not headers:
        wb.close()
        return [], {}
    
    # Detect column mapping
    mapping = apply_index_mapping(detect_column_mapping(headers), index_mapping_override)
    
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or all(cell is None or (isinstance(cell, str) and cell.strip() == "") for cell in row):
            continue
        
        # Extract values using mapping
        date_val = parse_date(row[mapping["date"]]) if mapping["date"] is not None and mapping["date"] < len(row) else None
        description = str(row[mapping["description"]]).strip() if mapping["description"] is not None and mapping["description"] < len(row) else ""
        amount_val = parse_amount(row[mapping["amount"]]) if mapping["amount"] is not None and mapping["amount"] < len(row) else 0.0
        type_val = str(row[mapping["type"]]).strip().lower() if mapping["type"] is not None and mapping["type"] < len(row) else None
        category_val = str(row[mapping["category"]]).strip() if mapping["category"] is not None and mapping["category"] < len(row) else None
        account_val = str(row[mapping["account"]]).strip() if mapping["account"] is not None and mapping["account"] < len(row) else None
        memo_val = str(row[mapping["memo"]]).strip() if mapping["memo"] is not None and mapping["memo"] < len(row) else None
        
        # Skip if essential fields are missing
        if not date_val or not description:
            continue
        
        rows.append({
            "date": date_val,
            "description": description,
            "amount": amount_val,
            "type": type_val,
            "category": category_val,
            "account": account_val,
            "memo": memo_val or "",
        })
    
    wb.close()
    return rows, mapping
