"""Category registry service (stored categories + helpers)."""

from __future__ import annotations

import uuid
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.category_keyword import CategoryKeyword


DEFAULT_CATEGORIES: list[str] = [
    "식료품",
    "카페",
    "교통",
    "쇼핑",
    "구독",
    "주거",
    "의료",
    "교육",
    "운동",
    "배달",
    "편의점",
    "기타",
]


def _norm(name: str) -> str:
    return (name or "").strip()


def list_registered_categories(db: Session, user_id: str) -> list[str]:
    """Return categories registered for a user (DB categories + keyword categories)."""
    cats = [c[0] for c in db.query(Category.name).filter(Category.user_id == user_id).all()]
    kw_cats = [c[0] for c in db.query(CategoryKeyword.category).filter(CategoryKeyword.user_id == user_id).distinct().all()]

    merged: list[str] = []
    seen: set[str] = set()
    for name in cats + kw_cats + DEFAULT_CATEGORIES:
        nn = _norm(name)
        if not nn:
            continue
        key = nn.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(nn)
    return merged


def ensure_category(db: Session, user_id: str, name: str) -> bool:
    """
    Ensure a category exists in DB. Returns True if created, False if already existed.
    """
    name = _norm(name)
    if not name:
        return False

    exists = (
        db.query(Category.id)
        .filter(Category.user_id == user_id, func.lower(Category.name) == func.lower(name))
        .first()
    )
    if exists:
        return False

    db.add(
        Category(
            id=f"cat_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            name=name,
        )
    )
    db.commit()
    return True

