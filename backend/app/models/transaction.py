"""Transaction model."""

from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Numeric, Text, ForeignKey, Index

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    type = Column(String(20), nullable=False)  # income, expense, transfer
    category = Column(String(100), nullable=False, index=True)
    account = Column(String(100), nullable=False, index=True)
    memo = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_transactions_user_date", "user_id", "date"),)
