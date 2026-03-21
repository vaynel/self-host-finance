"""Investment order and execution models."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class OrderStatus(str, enum.Enum):
    """주문 상태."""
    PENDING = "pending"  # 접수됨
    PARTIALLY_FILLED = "partially_filled"  # 부분체결
    FILLED = "filled"  # 전량체결
    CANCELLED = "cancelled"  # 취소됨
    REJECTED = "rejected"  # 거부됨


class OrderType(str, enum.Enum):
    """주문 유형."""
    LIMIT = "limit"  # 지정가
    MARKET = "market"  # 시장가


class InvestmentOrder(Base):
    """투자 주문 요청 모델."""
    __tablename__ = "investment_orders"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(50), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_account_id = Column(String(50), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # 주문 정보
    ticker = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    side = Column(String(10), nullable=False)  # "buy" or "sell"
    quantity = Column(Numeric(18, 4), nullable=False)  # 주문 수량
    price = Column(Numeric(15, 2), nullable=True)  # 지정가 (시장가 주문 시 NULL)
    order_type = Column(String(20), nullable=False, default="limit")  # "limit" or "market"
    
    # 브로커 연동 정보
    broker_order_id = Column(String(100), nullable=True, index=True)  # 브로커 주문번호
    status = Column(String(20), nullable=False, default="pending")  # pending, partially_filled, filled, cancelled, rejected
    
    # 타임스탬프
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)  # 전량 체결 시각
    cancelled_at = Column(DateTime, nullable=True)  # 취소 시각
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    executions = relationship("InvestmentExecution", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_investment_orders_user_account", "user_id", "account_id"),
        Index("ix_investment_orders_broker_order_id", "broker_order_id"),
        Index("ix_investment_orders_status", "status"),
    )


class InvestmentExecution(Base):
    """투자 체결 모델."""
    __tablename__ = "investment_executions"

    id = Column(String(50), primary_key=True)
    order_id = Column(String(50), ForeignKey("investment_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 체결 정보
    broker_execution_id = Column(String(100), nullable=True, unique=True, index=True)  # 브로커 체결번호 (중복 방지)
    executed_quantity = Column(Numeric(18, 4), nullable=False)  # 체결 수량
    executed_price = Column(Numeric(15, 2), nullable=False)  # 체결 가격
    fee = Column(Numeric(15, 2), nullable=True)  # 수수료
    executed_at = Column(DateTime, nullable=False)  # 체결 시각
    
    # 정산 반영 여부
    settled = Column(String(10), nullable=False, default="no")  # "no", "yes", "error"
    settled_at = Column(DateTime, nullable=True)  # 정산 반영 시각
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    order = relationship("InvestmentOrder", back_populates="executions")

    __table_args__ = (
        Index("ix_investment_executions_order_id", "order_id"),
        Index("ix_investment_executions_broker_execution_id", "broker_execution_id"),
        Index("ix_investment_executions_settled", "settled"),
    )
