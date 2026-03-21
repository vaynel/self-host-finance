"""Investment snapshot models from broker sync."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Index

from app.database import Base


class InvestmentHoldingSnapshot(Base):
    """Broker-synced holding snapshot."""

    __tablename__ = "investment_holding_snapshot"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False)
    average_price = Column(Numeric(15, 4), nullable=False)
    current_price = Column(Numeric(15, 4), nullable=False)
    valuation = Column(Numeric(18, 2), nullable=False)
    synced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_investment_holding_snapshot_user_account", "user_id", "account_id"),
        Index("ix_investment_holding_snapshot_user_ticker", "user_id", "ticker"),
    )


class InvestmentCashSnapshot(Base):
    """Broker-synced cash snapshot."""

    __tablename__ = "investment_cash_snapshot"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    cash_balance = Column(Numeric(18, 2), nullable=False)
    orderable_cash = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="KRW")
    synced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_investment_cash_snapshot_user_account", "user_id", "account_id"),
    )
