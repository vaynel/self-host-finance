"""Parsing strategy model for bank/export formats (LLM-generated or manual)."""

from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
try:
    # Prefer JSONB on Postgres
    from sqlalchemy.dialects.postgresql import JSONB  # type: ignore
except Exception:  # pragma: no cover
    # Fallback for non-Postgres backends
    from sqlalchemy import JSON as JSONB  # type: ignore

from app.database import Base


class ParsingStrategy(Base):
    """
    Stores a reusable parsing strategy keyed by a fingerprint of a file format.

    - fingerprint: stable identifier derived from header + sample rows
    - mapping: JSON describing how to map columns to our canonical fields
    - rules: JSON for transformations (e.g., amount sign, debit/credit columns, date formats)
    """

    __tablename__ = "parsing_strategies"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    fingerprint = Column(String(128), nullable=False, index=True)  # sha256 hex
    provider = Column(String(32), nullable=False, default="groq")  # groq|manual
    model = Column(String(64), nullable=True)  # e.g., llama3-8b-8192

    # strategy payload
    mapping = Column(JSONB(), nullable=False)  # {"date": "...", "description": "...", "amount": "...", ...}
    rules = Column(JSONB(), nullable=False, default=dict)  # {"amount": {...}, "date": {...}, ...}

    # optional metadata for debugging / evolution
    header = Column(JSONB(), nullable=True)  # original header list
    examples = Column(JSONB(), nullable=True)  # sample rows used to infer
    prompt_version = Column(String(32), nullable=False, default="v1")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_parsing_strategies_user_fingerprint", "user_id", "fingerprint", unique=True),
    )

