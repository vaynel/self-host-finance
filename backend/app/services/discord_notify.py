"""Discord webhook notifications for investment rule triggers."""

from __future__ import annotations

import logging
from typing import Optional

import requests
from sqlalchemy.orm import Session

from app.core.token_encryption import decrypt_token
from app.models.settings import UserSettings

logger = logging.getLogger("finflow.discord")


def notify_rule_triggered(
    db: Session,
    *,
    user_id: str,
    scope: str,
    rule_id: str,
    account_id: str,
    ticker: str,
    stock_name: Optional[str],
    trigger_kind: str,
    trigger_percent: float,
    action_mode: str,
    detail: Optional[str] = None,
    order_id: Optional[str] = None,
) -> None:
    """룰 트리거 시 Discord 웹훅으로 알림 (URL이 설정된 사용자만)."""
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not s or not s.discord_webhook_encrypted:
        return
    try:
        url = decrypt_token(s.discord_webhook_encrypted)
    except Exception:
        logger.exception("Discord 웹훅 복호화 실패 user_id=%s", user_id)
        return

    scope_ko = "종목별 룰" if scope == "ticker" else "글로벌 룰"
    mode_ko = {
        "alert_only": "알림만",
        "auto_sell": "자동매도",
        "alert_and_sell": "알림+매도",
    }.get(action_mode, action_mode)
    kind_ko = "원금 대비 하락" if trigger_kind == "cost_drop" else "고점 대비 하락"

    lines = [
        "🔔 **투자 룰 트리거**",
        f"**{stock_name or ticker}** (`{ticker}`)",
        f"· 조건: {kind_ko} **≥ {trigger_percent:g}%**",
        f"· 처리: {mode_ko}",
        f"· {scope_ko} `{rule_id}` · 계좌 `{account_id}`",
    ]
    if detail:
        lines.append(f"· {detail}")
    if order_id:
        lines.append(f"· 주문 ID `{order_id}`")

    content = "\n".join(lines)
    if len(content) > 1900:
        content = content[:1890] + "…"

    try:
        r = requests.post(url, json={"content": content}, timeout=12)
        r.raise_for_status()
    except Exception:
        logger.exception("Discord 웹훅 전송 실패 user_id=%s", user_id)
