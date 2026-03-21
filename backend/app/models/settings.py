"""User settings model."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    currency = Column(String(3), nullable=False, default="KRW")
    language = Column(String(5), nullable=False, default="ko")
    notifications = Column(JSONB, nullable=True)
    discord_webhook_encrypted = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
