"""Investment trade model."""

from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Numeric, ForeignKey

from app.database import Base


class InvestmentTrade(Base):
    __tablename__ = "investment_trades"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    type = Column(String(20), nullable=False, default="stock")  # stock, etf
    action = Column(String(10), nullable=False)  # buy, sell
    date = Column(Date, nullable=False)
    shares = Column(Numeric(18, 4), nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    fee = Column(Numeric(15, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
