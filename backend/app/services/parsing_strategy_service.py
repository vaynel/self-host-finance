"""Parsing strategy service: fingerprinting, LLM inference, DB persistence, and application."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.security import create_txn_id
from app.models.parsing_strategy import ParsingStrategy
from app.services.groq_client import GroqClient


PROMPT_VERSION = "v1"


def compute_fingerprint(headers: list[str], sample_rows: list[list[Any]]) -> str:
    """
    Compute a stable fingerprint for a file format based on headers + a few sample rows.
    We intentionally avoid full-file hashing to make it robust.
    """
    normalized_headers = [str(h or "").strip().lower() for h in headers]
    normalized_samples: list[list[str]] = []
    for r in sample_rows[:5]:
        normalized_samples.append([str(c or "").strip().lower()[:64] for c in r[:12]])

    payload = {"h": normalized_headers, "s": normalized_samples}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _normalize_header(s: str) -> str:
    return str(s or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def mapping_to_index_map(headers: list[str], mapping: dict[str, Any]) -> dict[str, Optional[int]]:
    """
    Convert mapping that uses column names (or indices) into an index mapping compatible with smart parser.
    """
    norm_headers = [_normalize_header(h) for h in headers]

    idx_map: dict[str, Optional[int]] = {
        "date": None,
        "description": None,
        "amount": None,
        "type": None,
        "category": None,
        "account": None,
        "memo": None,
        "balance": None,
        "deposit": None,
        "withdraw": None,
    }

    for key, val in (mapping or {}).items():
        if key not in idx_map:
            continue
        if val is None or val == "":
            idx_map[key] = None
            continue
        if isinstance(val, int):
            idx_map[key] = val if 0 <= val < len(headers) else None
            continue
        # string header name
        n = _normalize_header(str(val))
        if n in norm_headers:
            idx_map[key] = norm_headers.index(n)
        else:
            idx_map[key] = None

    # Post-fixups for common Korean bank exports:
    # - "거래점/지점" is a branch, not an account name. If LLM mapped it to account, move it to memo instead.
    def _hdr_at(i: Optional[int]) -> str:
        if i is None or i < 0 or i >= len(headers):
            return ""
        return _normalize_header(headers[i])

    acc_hdr = _hdr_at(idx_map.get("account"))
    if acc_hdr and ("거래점" in acc_hdr or "지점" in acc_hdr or "branch" in acc_hdr):
        if idx_map.get("memo") is None:
            idx_map["memo"] = idx_map.get("account")
        idx_map["account"] = None

    # If LLM mapped description to "적요"(kind) and memo to "내용"(details), swap them.
    desc_hdr = _hdr_at(idx_map.get("description"))
    memo_hdr = _hdr_at(idx_map.get("memo"))
    if desc_hdr and memo_hdr and ("적요" in desc_hdr) and ("내용" in memo_hdr or "거래내용" in memo_hdr):
        idx_map["description"], idx_map["memo"] = idx_map["memo"], idx_map["description"]

    return idx_map


async def infer_strategy_with_llm(
    headers: list[str],
    sample_rows: list[list[Any]],
) -> dict[str, Any]:
    """
    Ask Groq LLM to produce a JSON parsing strategy.
    Output schema:
    {
      "mapping": {"date": "...", "description": "...", "amount": "...", "deposit": "...", "withdraw": "...", "memo": "..."},
      "rules": {
        "amount": {"mode": "amount|deposit_withdraw", "negate_withdraw": true},
        "date": {"formats": ["%Y-%m-%d", ...]}
      }
    }
    """
    client = GroqClient()
    header_preview = headers[:50]
    sample_preview = [r[:12] for r in sample_rows[:5]]

    system = (
        "You are a data-import expert. Return ONLY valid JSON. "
        "Goal: map an arbitrary bank/card CSV/XLSX export into canonical fields: "
        "date, description, amount, type(optional), category(optional), account(optional), memo(optional), balance(optional). "
        "If amount is split into deposit/withdraw columns, set mapping.deposit and mapping.withdraw and rules.amount.mode='deposit_withdraw'. "
        "If a single amount column exists, set mapping.amount and rules.amount.mode='amount'. "
        "Prefer using header NAMES (strings), not indices."
    )
    user = {
        "headers": header_preview,
        "sample_rows": sample_preview,
        "notes": "Some exports use Korean headers like 거래일자/적요/입금/출금/잔액. "
                 "Return best-effort mapping and reasonable date formats.",
        "output_schema": {
            "mapping": {
                "date": "header name",
                "description": "header name",
                "amount": "header name or null",
                "deposit": "header name or null",
                "withdraw": "header name or null",
                "type": "header name or null",
                "category": "header name or null",
                "account": "header name or null",
                "memo": "header name or null",
                "balance": "header name or null",
            },
            "rules": {
                "amount": {"mode": "amount|deposit_withdraw", "negate_withdraw": True},
                "date": {"formats": ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"]},
            },
        },
    }

    resp = await client.chat_json(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.0,
        max_tokens=1200,
    )
    content = resp["choices"][0]["message"]["content"]
    return GroqClient._loads_json_object_loose(content)


async def get_or_create_strategy(
    db: Session,
    user_id: str,
    headers: list[str],
    sample_rows: list[list[Any]],
) -> ParsingStrategy:
    fingerprint = compute_fingerprint(headers, sample_rows)
    existing = (
        db.query(ParsingStrategy)
        .filter(ParsingStrategy.user_id == user_id, ParsingStrategy.fingerprint == fingerprint)
        .first()
    )
    if existing:
        return existing

    inferred = await infer_strategy_with_llm(headers, sample_rows)
    mapping = inferred.get("mapping") or {}
    rules = inferred.get("rules") or {}

    s = ParsingStrategy(
        id=create_txn_id(),  # reuse id generator
        user_id=user_id,
        fingerprint=fingerprint,
        provider="groq",
        model=GroqClient().model,
        mapping=mapping,
        rules=rules,
        header=headers,
        examples=sample_rows[:5],
        prompt_version=PROMPT_VERSION,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

