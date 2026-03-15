"""Transaction schemas."""

from datetime import date
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, field_validator


class TransactionCreate(BaseModel):
    date: str
    description: str
    amount: float
    type: str
    category: str
    account: str
    memo: Optional[str] = ""

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("income", "expense", "transfer"):
            raise ValueError("type은 income, expense, transfer 중 하나여야 합니다.")
        return v


class TransactionUpdate(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    category: Optional[str] = None
    account: Optional[str] = None
    memo: Optional[str] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("income", "expense", "transfer"):
            raise ValueError("type은 income, expense, transfer 중 하나여야 합니다.")
        return v


class TransactionResponse(BaseModel):
    id: str
    date: str
    description: str
    amount: float
    type: str
    category: str
    account: str
    memo: str = ""
