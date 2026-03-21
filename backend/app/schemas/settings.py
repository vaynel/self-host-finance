"""Settings schemas."""

from typing import Optional, Any
from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    currency: Optional[str] = None
    language: Optional[str] = None
    notifications: Optional[dict[str, Any]] = None
    # 비우면 웹훅 제거. 미전송 시 기존 값 유지(라우터에서 exclude_unset).
    discord_webhook_url: Optional[str] = Field(
        default=None,
        description="Discord Incoming Webhook 전체 URL. 빈 문자열이면 삭제.",
    )


class SettingsResponse(BaseModel):
    currency: str
    language: str
    notifications: Optional[dict[str, Any]] = None
    discord_webhook_configured: bool = False
    discord_webhook_masked: Optional[str] = None
