"""Auto-trade rule models."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String

from app.database import Base


class AutoTradeRule(Base):
    """자동매매 규칙."""

    __tablename__ = "auto_trade_rules"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # buy, sell
    enabled = Column(Boolean, nullable=False, default=True)

    # Trigger condition
    target_price = Column(Numeric(15, 2), nullable=True)
    stop_price = Column(Numeric(15, 2), nullable=True)

    # Order params
    order_type = Column(String(20), nullable=False, default="limit")
    quantity = Column(Numeric(18, 4), nullable=False)
    limit_price = Column(Numeric(15, 2), nullable=True)

    # Risk/cooldown
    cooldown_seconds = Column(String(20), nullable=False, default="300")
    last_triggered_at = Column(DateTime, nullable=True)

    # New trigger fields
    # - kind: cost_drop | peak_drop
    # - percent: threshold percent for drop triggers
    trigger_kind = Column(String(20), nullable=False, default="cost_drop")
    trigger_percent = Column(Numeric(6, 2), nullable=False, default=0)

    # Action mode: alert_only | auto_sell
    action_mode = Column(String(20), nullable=False, default="alert_only")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_auto_trade_rules_user_account_enabled", "user_id", "account_id", "enabled"),
    )


class AutoTradeRunLog(Base):
    """자동매매 실행 로그."""

    __tablename__ = "auto_trade_run_logs"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(50), ForeignKey("auto_trade_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # skipped, triggered, failed
    reason = Column(String(255), nullable=True)
    order_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_auto_trade_run_logs_rule_created", "rule_id", "created_at"),
    )
