"""Investment price models (latest intraday + daily history)."""

from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Numeric, ForeignKey, Index

from app.database import Base


class InvestmentPriceLatest(Base):
    """Stores the latest fetched price for a ticker."""

    __tablename__ = "investment_price_latest"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    price = Column(Numeric(15, 4), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_investment_price_latest_user_ticker", "user_id", "ticker"),
    )


class InvestmentPriceDaily(Base):
    """Stores one daily close price per ticker (for charts)."""

    __tablename__ = "investment_price_daily"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    close = Column(Numeric(15, 4), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_investment_price_daily_user_ticker_date", "user_id", "ticker", "trade_date"),
    )

