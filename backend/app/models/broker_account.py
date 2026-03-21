"""Broker account detail model for investment accounts."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index

from app.database import Base


class BrokerAccount(Base):
    """투자계좌의 브로커 연동 상세 정보를 저장하는 모델."""
    __tablename__ = "broker_accounts"

    id = Column(String(50), primary_key=True)
    account_id = Column(
        String(50),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    broker_type = Column(String(20), nullable=False, default="MANUAL")  # KIS, MANUAL, OTHER
    broker_account_no_masked = Column(String(100), nullable=True)  # 마스킹된 계좌번호
    product_code = Column(String(50), nullable=True)  # 상품코드 (KIS용)
    is_mock = Column(Boolean, nullable=False, default=False)  # 모의투자 여부
    api_enabled = Column(Boolean, nullable=False, default=False)  # API 연동 가능 여부
    order_enabled = Column(Boolean, nullable=False, default=False)  # 주문 가능 여부
    auto_trade_enabled = Column(Boolean, nullable=False, default=False)  # 자동매매 활성화 여부
    last_balance_sync_at = Column(DateTime, nullable=True)  # 마지막 잔고 동기화 시각
    last_price_sync_at = Column(DateTime, nullable=True)  # 마지막 가격 동기화 시각
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_broker_accounts_account_id", "account_id"),
        Index("ix_broker_accounts_broker_type", "broker_type"),
    )
