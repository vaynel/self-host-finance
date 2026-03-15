"""Auth routes."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, DbSession
from app.schemas.auth import LoginRequest, RegisterRequest, RefreshRequest, UserResponse, LoginResponse
from app.schemas.common import success_response
from app.models.user import User
from app.services.auth_service import (
    register_user,
    authenticate_user,
    store_refresh_token,
    invalidate_refresh_token,
    verify_refresh_token,
)
from app.core.security import create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(req: LoginRequest, db: DbSession):
    """Login and get tokens."""
    user = authenticate_user(db, req.email, req.password)
    if not user:
        return {"success": False, "data": None, "error": {"code": 401, "message": "이메일 또는 비밀번호가 올바르지 않습니다.", "details": []}, "meta": None}
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    store_refresh_token(db, user.id, refresh_token)
    payload = decode_token(access_token)
    expires_in = int((payload["exp"] - datetime.utcnow().timestamp()) if payload else 3600)
    data = {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "expiresIn": expires_in,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }
    return success_response(data)


@router.post("/register")
def register(req: RegisterRequest, db: DbSession):
    """Register new user."""
    user = register_user(db, req.email, req.password, req.name)
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    store_refresh_token(db, user.id, refresh_token)
    data = {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "expiresIn": 3600,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }
    return success_response(data)


@router.post("/refresh")
def refresh(req: RefreshRequest, db: DbSession):
    """Refresh access token."""
    user = verify_refresh_token(db, req.refreshToken)
    if not user:
        return {"success": False, "data": None, "error": {"code": 401, "message": "리프레시 토큰이 유효하지 않습니다.", "details": []}, "meta": None}
    access_token = create_access_token(user.id)
    payload = decode_token(access_token)
    expires_in = int((payload["exp"] - datetime.utcnow().timestamp()) if payload else 3600)
    data = {
        "accessToken": access_token,
        "refreshToken": req.refreshToken,
        "expiresIn": expires_in,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }
    return success_response(data)


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: DbSession = None,
):
    """Logout - client should discard tokens locally."""
    return success_response({"message": "로그아웃되었습니다."})
