"""Global auto-trade rule models (applies to all tickers in an investment account)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String

from app.database import Base


class AutoTradeGlobalRule(Base):
    """자동매매 글로벌 규칙(계좌 내 전 종목에 적용)."""

    __tablename__ = "auto_trade_global_rules"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True)

    # Trigger condition
    trigger_kind = Column(String(20), nullable=False, default="cost_drop")  # cost_drop | peak_drop
    trigger_percent = Column(Numeric(6, 2), nullable=False, default=0)

    # Action mode
    action_mode = Column(String(20), nullable=False, default="alert_only")  # alert_only | auto_sell

    # Order params (for auto_sell)
    order_type = Column(String(20), nullable=False, default="limit")
    sell_quantity_ratio = Column(Numeric(10, 4), nullable=False, default=1)  # 1.0 = 전량 매도
    limit_price = Column(Numeric(15, 2), nullable=True)

    # Risk/cooldown
    cooldown_seconds = Column(String(20), nullable=False, default="300")
    last_triggered_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_auto_trade_global_rules_user_account_enabled", "user_id", "account_id", "enabled"),
    )


class AutoTradeGlobalRunLog(Base):
    """자동매매 글로벌 실행 로그."""

    __tablename__ = "auto_trade_global_run_logs"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(50), ForeignKey("auto_trade_global_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # skipped, triggered, failed
    reason = Column(String(255), nullable=True)
    order_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_auto_trade_global_run_logs_rule_created", "rule_id", "created_at"),
    )

