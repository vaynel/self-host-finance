"""Investment schemas."""

from typing import Optional
from pydantic import BaseModel, field_validator


class HoldingResponse(BaseModel):
    ticker: str
    name: str
    type: str
    shares: float
    avgPrice: float
    currentPrice: float
    totalValue: float
    profitLoss: float
    profitLossRate: float


class TradeCreate(BaseModel):
    ticker: str
    action: str
    date: str
    shares: float
    price: float
    fee: Optional[float] = 0
    # 현금(주문 결제)용 계좌. 지정하지 않으면 백엔드에서 기본 계좌를 선택합니다.
    accountId: Optional[str] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("buy", "sell"):
            raise ValueError("action은 buy 또는 sell이어야 합니다.")
        return v


class TradeResponse(BaseModel):
    id: str
    ticker: str
    name: Optional[str]
    type: str
    action: str
    date: str
    shares: float
    price: float
    fee: Optional[float] = None
