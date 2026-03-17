"""Parsing strategy management routes (LLM-generated)."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.dependencies import get_current_user, DbSession
from app.models.user import User
from app.models.parsing_strategy import ParsingStrategy
from app.schemas.common import success_response

router = APIRouter(prefix="/parsing-strategies", tags=["parsing-strategies"])


@router.get("")
def list_strategies(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    rows = (
        db.query(ParsingStrategy)
        .filter(ParsingStrategy.user_id == current_user.id)
        .order_by(ParsingStrategy.updated_at.desc())
        .limit(100)
        .all()
    )
    return success_response([
        {
            "id": r.id,
            "fingerprint": r.fingerprint,
            "provider": r.provider,
            "model": r.model,
            "prompt_version": r.prompt_version,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ])


@router.get("/{strategy_id}")
def get_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    r = (
        db.query(ParsingStrategy)
        .filter(ParsingStrategy.id == strategy_id, ParsingStrategy.user_id == current_user.id)
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")
    return success_response(
        {
            "id": r.id,
            "fingerprint": r.fingerprint,
            "provider": r.provider,
            "model": r.model,
            "mapping": r.mapping,
            "rules": r.rules,
            "header": r.header,
            "examples": r.examples,
            "prompt_version": r.prompt_version,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
    )


@router.delete("/{strategy_id}")
def delete_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    r = (
        db.query(ParsingStrategy)
        .filter(ParsingStrategy.id == strategy_id, ParsingStrategy.user_id == current_user.id)
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")
    db.delete(r)
    db.commit()
    return success_response({"message": "전략이 삭제되었습니다."})

