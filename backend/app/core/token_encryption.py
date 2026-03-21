"""Token encryption utilities for broker tokens."""

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import get_settings

settings = get_settings()


def _get_encryption_key() -> bytes:
    """환경변수 또는 JWT secret을 기반으로 암호화 키 생성."""
    # 환경변수에서 암호화 키를 가져오거나, JWT secret을 사용
    secret_key = getattr(settings, "token_encryption_key", None) or settings.jwt_secret
    
    # PBKDF2를 사용하여 Fernet 키 생성
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"finflow_broker_token_salt",  # 실제 운영에서는 랜덤 salt 사용 권장
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return key


_fernet = None


def _get_fernet() -> Fernet:
    """Fernet 인스턴스를 싱글톤으로 반환."""
    global _fernet
    if _fernet is None:
        key = _get_encryption_key()
        _fernet = Fernet(key)
    return _fernet


def encrypt_token(token: str) -> str:
    """토큰을 암호화하여 반환."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """암호화된 토큰을 복호화하여 반환."""
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()
