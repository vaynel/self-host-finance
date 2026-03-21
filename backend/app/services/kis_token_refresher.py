"""Background scheduler to automatically refresh KIS access tokens.

Goal:
- KIS access token has limited validity (~24h). Tokens should be refreshed automatically
  without requiring manual "connect" presses.
- Refresh should happen only when the stored token is expired (or missing), and
  the actual issuance is guarded by KISAuthService's per-account lock + expiry checks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.database import SessionLocal
from app.models.broker_account import BrokerAccount
from app.models.broker_token import BrokerToken
from app.services.kis_auth_service import KISAuthService

# main.py에서 설정한 logging/basicConfig에 의해 uvicorn.log에 찍히도록 finflow.debug 네임스페이스를 사용합니다.
logger = logging.getLogger("finflow.debug")

_scheduler_task: asyncio.Task | None = None


async def refresh_kis_tokens_once() -> None:
    """Refresh tokens for all enabled KIS broker accounts (only if expired)."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        broker_accounts = (
            db.query(BrokerAccount)
            .filter(
                BrokerAccount.broker_type == "KIS",
                BrokerAccount.api_enabled.is_(True),
            )
            .all()
        )

        for ba in broker_accounts:
            token = db.query(BrokerToken).filter(BrokerToken.broker_account_id == ba.id).first()
            # 토큰이 없거나 만료(= now 이전)면 갱신합니다.
            if not token or not token.expires_at or token.expires_at <= now:
                try:
                    KISAuthService.issue_token(db, ba)
                except Exception:
                    logger.exception("Failed to refresh KIS token. broker_account_id=%s", ba.id)

    finally:
        db.close()


async def kis_token_refresher_loop() -> None:
    interval_seconds = 60
    logger.info("Starting KIS token refresher loop interval=%ss", interval_seconds)
    while True:
        try:
            await refresh_kis_tokens_once()
        except Exception:
            logger.exception("kis_token_refresher cycle failed")
        await asyncio.sleep(interval_seconds)


def start_kis_token_refresher_if_needed() -> None:
    """Start scheduler once per process."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    logger.info("Starting KIS token refresher loop interval=60s")
    _scheduler_task = asyncio.create_task(kis_token_refresher_loop())

