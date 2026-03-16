"""Category keyword model for auto-classification."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index

from app.database import Base


class CategoryKeyword(Base):
    __tablename__ = "category_keywords"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    keyword = Column(String(200), nullable=False)
    priority = Column(String(20), default="normal")  # high, normal, low
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_category_keywords_user_category", "user_id", "category"),
        Index("ix_category_keywords_keyword", "keyword"),
    )
