"""Investment schemas."""

from typing import Optional
from pydantic import BaseModel, field_validator
from pydantic import Field


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


class OrderCreate(BaseModel):
    account_id: str
    ticker: str
    side: str
    quantity: float
    price: Optional[float] = None
    order_type: str = "limit"

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in ("buy", "sell"):
            raise ValueError("side는 buy 또는 sell이어야 합니다.")
        return v

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in ("limit", "market"):
            raise ValueError("order_type은 limit 또는 market이어야 합니다.")
        return v


class AutoTradeRuleCreate(BaseModel):
    account_id: str
    ticker: str
    side: str
    enabled: bool = True
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    order_type: str = "limit"
    quantity: float
    limit_price: Optional[float] = None
    cooldown_seconds: int = 300
    # New fields
    trigger_kind: Optional[str] = "cost_drop"  # cost_drop | peak_drop
    trigger_percent: Optional[float] = 0
    action_mode: Optional[str] = "alert_only"  # alert_only | auto_sell | alert_and_sell

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in ("buy", "sell"):
            raise ValueError("side는 buy 또는 sell이어야 합니다.")
        return v

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in ("limit", "market"):
            raise ValueError("order_type은 limit 또는 market이어야 합니다.")
        return v

    @field_validator("action_mode")
    @classmethod
    def validate_action_mode(cls, v: Optional[str]) -> str:
        if v is None:
            return "alert_only"
        if v not in ("alert_only", "auto_sell", "alert_and_sell"):
            raise ValueError("action_mode가 올바르지 않습니다.")
        return v


class AutoTradeRuleUpdate(BaseModel):
    ticker: Optional[str] = None
    side: Optional[str] = None
    enabled: Optional[bool] = None
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    order_type: Optional[str] = None
    quantity: Optional[float] = None
    limit_price: Optional[float] = None
    cooldown_seconds: Optional[int] = None
    trigger_kind: Optional[str] = None
    trigger_percent: Optional[float] = None
    action_mode: Optional[str] = None

    @field_validator("action_mode")
    @classmethod
    def validate_action_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ("alert_only", "auto_sell", "alert_and_sell"):
            raise ValueError("action_mode가 올바르지 않습니다.")
        return v


class KISConnectRequest(BaseModel):
    """KIS OpenAPI 계좌 연동 요청 (최소 구현)."""

    # KIS에서 CANO로 사용하는 값입니다.
    # 보안 상 실운영에서는 암호화/마스킹 정책이 필요하지만,
    # 현재 동기화 구현은 이 값을 그대로 요청 헤더에 사용합니다.
    broker_account_no: str = Field(min_length=1, max_length=100)
    # 비우면 서버가 잔고조회 API로 ACNT_PRDT_CD를 자동 탐색합니다.
    product_code: Optional[str] = Field(default=None, max_length=50)
    is_mock: bool = False

    @field_validator("product_code", mode="before")
    @classmethod
    def empty_product_means_auto(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.upper() == "AUTO":
            return None
        return s