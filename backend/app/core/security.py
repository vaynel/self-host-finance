"""JWT and password utilities."""

from datetime import datetime, timedelta
from typing import Optional
import uuid

import jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# bcrypt 최대 72바이트 제한 (passlib/bcrypt 제약)
_BCRYPT_MAX_BYTES = 72


def _truncate_for_bcrypt(s: str) -> str:
    """bcrypt 72바이트 제한에 맞게 잘라냄."""
    b = s.encode("utf-8")
    if len(b) <= _BCRYPT_MAX_BYTES:
        return s
    return b[:_BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore") or s[:24]


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return pwd_context.hash(_truncate_for_bcrypt(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(_truncate_for_bcrypt(plain_password), hashed_password)


def create_access_token(user_id: str) -> str:
    """Create JWT access token."""
    expires = datetime.utcnow() + timedelta(hours=1)
    payload = {"sub": user_id, "exp": expires, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token."""
    expires = datetime.utcnow() + timedelta(days=7)
    payload = {"sub": user_id, "exp": expires, "type": "refresh", "jti": str(uuid.uuid4())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.PyJWTError:
        return None


def create_user_id() -> str:
    """Generate prefixed user ID like usr_xxx."""
    return f"usr_{uuid.uuid4().hex[:12]}"


def create_txn_id() -> str:
    """Generate prefixed transaction ID."""
    return f"txn_{uuid.uuid4().hex[:12]}"


def create_account_id() -> str:
    """Generate prefixed account ID."""
    return f"acc_{uuid.uuid4().hex[:12]}"


def create_trade_id() -> str:
    """Generate prefixed investment trade ID."""
    return f"trade_{uuid.uuid4().hex[:12]}"
