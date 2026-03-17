"""LLM-assisted category enrichment during upload/preview.

Rules:
- If row has a category already and it's registered -> keep it (no LLM).
- Else try keyword-based classifier.
- If still not confident/registered -> ask LLM.
- If LLM returns a new category -> store it and use it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.category_classifier import auto_classify_category
from app.services.category_registry import list_registered_categories, ensure_category
from app.services.groq_client import GroqClient


def _norm(s: str | None) -> str:
    return (s or "").strip()


async def enrich_categories_for_rows(
    db: Session,
    user_id: str,
    rows: list[dict[str, Any]],
    *,
    groq: GroqClient | None = None,
) -> tuple[int, int]:
    """
    Mutates rows in-place, setting row["category"].
    Returns (llm_calls, new_categories_created).
    """
    groq = groq or GroqClient()

    registered = list_registered_categories(db, user_id)
    registered_lc = {c.lower(): c for c in registered}

    llm_calls = 0
    created = 0

    # simple per-request cache to avoid repeated LLM calls
    cache: dict[str, str] = {}

    for row in rows:
        desc = _norm(row.get("description"))
        amount = float(row.get("amount") or 0)
        current = _norm(row.get("category"))

        # 1) already has registered category -> keep
        if current and current.lower() in registered_lc:
            row["category"] = registered_lc[current.lower()]
            continue

        # 2) keyword-based
        kw_cat = _norm(auto_classify_category(db, user_id, desc, amount)) if desc else ""
        if kw_cat and kw_cat.lower() in registered_lc:
            row["category"] = registered_lc[kw_cat.lower()]
            continue
        if kw_cat and kw_cat.lower() not in registered_lc and kw_cat != "기타":
            # keyword-based produced a category that wasn't registered yet -> register it
            if ensure_category(db, user_id, kw_cat):
                created += 1
            registered_lc.setdefault(kw_cat.lower(), kw_cat)
            row["category"] = kw_cat
            continue

        # 3) LLM
        if not desc:
            row["category"] = "기타"
            continue

        cache_key = f"{desc.lower()}|{amount}"
        if cache_key in cache:
            row["category"] = cache[cache_key]
            continue

        llm_calls += 1

        # Ask LLM. Prefer existing categories, but allow suggesting a new short category if nothing fits.
        categories_list = list(registered_lc.values())
        system = (
            "너는 개인 재무 거래내역을 카테고리로 분류하는 도우미다. "
            "가능하면 제공된 카테고리 목록 중 하나를 선택하되, "
            "정말 적절한 게 없으면 새로운 카테고리명을 짧게 제안해도 된다."
        )
        user = (
            f"거래 설명: {desc}\n"
            f"금액: {amount}\n"
            f"카테고리 목록: {categories_list}\n\n"
            '다음 JSON만 출력해: {"category": "카테고리명"}'
        )
        cat = "기타"
        try:
            resp = await groq.chat_json(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0,
                max_tokens=200,
            )
            content = resp["choices"][0]["message"]["content"]
            import json

            data = json.loads(content)
            proposed = _norm(str(data.get("category") or ""))
            if proposed:
                # normalize to existing if matches case-insensitively
                if proposed.lower() in registered_lc:
                    cat = registered_lc[proposed.lower()]
                else:
                    # guardrails for new categories
                    if 1 <= len(proposed) <= 12 and "\n" not in proposed and "\r" not in proposed:
                        cat = proposed
        except Exception:
            cat = "기타"

        # If it looks like a new category, register it.
        if cat.lower() not in registered_lc and cat != "기타":
            if ensure_category(db, user_id, cat):
                created += 1
            registered_lc[cat.lower()] = cat

        cache[cache_key] = cat
        row["category"] = cat

    return llm_calls, created

