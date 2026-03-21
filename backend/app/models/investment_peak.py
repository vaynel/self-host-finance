"""Track per-account, per-ticker high-water mark (peak) since last buy."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Index

from app.database import Base


class InvestmentPeakTracker(Base):
    """Keeps highest observed price to support trailing-stop style triggers."""

    __tablename__ = "investment_peak_tracker"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(50), nullable=False, index=True)
    peak_price = Column(Numeric(18, 6), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_peak_user_account_ticker", "user_id", "account_id", "ticker", unique=True),
    )

