"""Broker token model for storing encrypted API tokens."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text

from app.database import Base


class BrokerToken(Base):
    """브로커 API 토큰을 암호화하여 저장하는 모델."""
    __tablename__ = "broker_tokens"

    id = Column(String(50), primary_key=True)
    broker_account_id = Column(
        String(50),
        ForeignKey("broker_accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    # 암호화된 토큰 저장
    # Fernet(encrypt_token) 결과가 토큰 길이에 따라 커질 수 있어 충분히 크게 저장해야 합니다.
    encrypted_access_token = Column(Text, nullable=False)  # 암호화된 access token
    encrypted_refresh_token = Column(Text, nullable=True)  # 암호화된 refresh token
    token_type = Column(String(20), nullable=False, default="Bearer")
    expires_at = Column(DateTime, nullable=True)  # access token 만료 시각
    refresh_expires_at = Column(DateTime, nullable=True)  # refresh token 만료 시각
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_broker_tokens_broker_account_id", "broker_account_id"),
    )
