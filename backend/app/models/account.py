"""Account model."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # bank, investment
    balance = Column(Numeric(15, 2), nullable=False)
    institution = Column(String(100), nullable=False)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
