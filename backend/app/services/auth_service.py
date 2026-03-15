"""Auth business logic."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User, RefreshToken
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    create_user_id,
)
from app.core.exceptions import raise_400, raise_401


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get user by email."""
    return db.query(User).filter(User.email == email.lower()).first()


def register_user(db: Session, email: str, password: str, name: str) -> User:
    """Register new user."""
    if get_user_by_email(db, email):
        raise_400("이미 등록된 이메일입니다.")
    user = User(
        id=create_user_id(),
        email=email.lower(),
        name=name,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Verify credentials and return user."""
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def store_refresh_token(db: Session, user_id: str, token: str) -> None:
    """Store refresh token."""
    import uuid
    rt = RefreshToken(
        id=f"rt_{user_id[:8]}_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(rt)
    db.commit()


def invalidate_refresh_token(db: Session, token: str) -> None:
    """Remove refresh token from DB (logout)."""
    db.query(RefreshToken).filter(RefreshToken.token == token).delete()
    db.commit()


def verify_refresh_token(db: Session, token: str) -> User | None:
    """Verify refresh token and return user."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    rt = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if not rt or rt.user_id != user_id:
        return None
    user = get_user_by_id(db, user_id)
    return user
