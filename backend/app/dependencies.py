"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import decode_token
from app.core.exceptions import raise_401
from app.services.auth_service import get_user_by_id

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: DbSession = ...,
) -> User:
    """Extract and validate JWT from Authorization header, return current user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise_401("토큰이 제공되지 않았습니다.")
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    if not payload:
        raise_401("토큰이 만료되었거나 유효하지 않습니다.")
    if payload.get("type") != "access":
        raise_401("잘못된 토큰 유형입니다.")
    user_id = payload.get("sub")
    if not user_id:
        raise_401("토큰이 유효하지 않습니다.")
    user = get_user_by_id(db, user_id)
    if not user:
        raise_401("사용자를 찾을 수 없습니다.")
    return user
