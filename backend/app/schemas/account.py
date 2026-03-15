"""Account schemas."""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, field_validator


class AccountCreate(BaseModel):
    name: str
    type: str
    balance: float
    institution: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("bank", "investment"):
            raise ValueError("type은 bank 또는 investment여야 합니다.")
        return v


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    balance: Optional[float] = None
    institution: Optional[str] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("bank", "investment"):
            raise ValueError("type은 bank 또는 investment여야 합니다.")
        return v


class AccountResponse(BaseModel):
    id: str
    name: str
    type: str
    balance: float
    institution: str
    lastSync: Optional[str] = None


class AccountFlowItem(BaseModel):
    date: str
    balance: float


class AccountFlowResponse(BaseModel):
    accountId: str
    chartData: list[AccountFlowItem]
