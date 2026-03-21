"""Pydantic schemas for auto-trade global rules."""

from typing import Optional

from pydantic import BaseModel, field_validator


class AutoTradeGlobalRuleCreate(BaseModel):
    account_id: str
    enabled: bool = True
    trigger_kind: str = "cost_drop"  # cost_drop | peak_drop
    trigger_percent: float = 0
    action_mode: str = "alert_only"  # alert_only | auto_sell | alert_and_sell
    order_type: str = "market"  # limit | market
    sell_quantity_ratio: float = 1.0
    limit_price: Optional[float] = None
    cooldown_seconds: int = 300

    @field_validator("trigger_kind")
    @classmethod
    def validate_trigger_kind(cls, v: str) -> str:
        if v not in ("cost_drop", "peak_drop"):
            raise ValueError("invalid trigger_kind")
        return v

    @field_validator("action_mode")
    @classmethod
    def validate_action_mode(cls, v: str) -> str:
        if v not in ("alert_only", "auto_sell", "alert_and_sell"):
            raise ValueError("invalid action_mode")
        return v

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in ("limit", "market"):
            raise ValueError("invalid order_type")
        return v


class AutoTradeGlobalRuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    trigger_kind: Optional[str] = None
    trigger_percent: Optional[float] = None
    action_mode: Optional[str] = None
    order_type: Optional[str] = None
    sell_quantity_ratio: Optional[float] = None
    limit_price: Optional[float] = None
    cooldown_seconds: Optional[int] = None

