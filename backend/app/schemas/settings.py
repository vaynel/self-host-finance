"""Settings schemas."""

from typing import Optional, Any
from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    currency: Optional[str] = None
    language: Optional[str] = None
    notifications: Optional[dict[str, Any]] = None


class SettingsResponse(BaseModel):
    currency: str
    language: str
    notifications: Optional[dict[str, Any]] = None
