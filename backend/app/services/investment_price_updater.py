"""Background task to periodically refresh stock prices for tracked tickers."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Iterable, Optional
import uuid

from app.config import get_settings
from app.database import SessionLocal
from app.models.investment import InvestmentTrade
from app.models.investment_price import InvestmentPriceLatest, InvestmentPriceDaily
from app.models.investment_snapshot import InvestmentHoldingSnapshot
from app.models.broker_account import BrokerAccount
from app.services.stock_price_provider import get_default_provider
from app.brokers.kis import KISAdapter

logger = logging.getLogger("finflow.investment_price_updater")


_updater_task: asyncio.Task | None = None


async def upsert_latest_and_daily(
    db,
    *,
    user_id: str,
    ticker: str,
    price: float,
) -> None:
    now = datetime.utcnow()
    trade_date = date.today()

    # latest: upsert by selecting first row (we don't enforce unique constraint in DB for now)
    latest = (
        db.query(InvestmentPriceLatest)
        .filter(InvestmentPriceLatest.user_id == user_id, InvestmentPriceLatest.ticker == ticker)
        .order_by(InvestmentPriceLatest.updated_at.desc())
        .first()
    )
    if latest:
        latest.price = Decimal(str(price))
        latest.updated_at = now
    else:
        db.add(
            InvestmentPriceLatest(
                id=f"ipl_{user_id[:8]}_{int(now.timestamp())}",
                user_id=user_id,
                ticker=ticker,
                price=Decimal(str(price)),
                updated_at=now,
            )
        )

    # daily: upsert for today's date
    daily = (
        db.query(InvestmentPriceDaily)
        .filter(
            InvestmentPriceDaily.user_id == user_id,
            InvestmentPriceDaily.ticker == ticker,
            InvestmentPriceDaily.trade_date == trade_date,
        )
        .first()
    )
    if daily:
        daily.close = Decimal(str(price))
        daily.updated_at = now
    else:
        db.add(
            InvestmentPriceDaily(
                id=f"ipd_{user_id[:8]}_{int(now.timestamp())}",
                user_id=user_id,
                ticker=ticker,
                trade_date=trade_date,
                close=Decimal(str(price)),
                updated_at=now,
            )
        )

    db.commit()


async def refresh_prices_once(*, tickers: Optional[Iterable[tuple[str, str]]] = None) -> None:
    """Refresh prices once for a set of (user_id, ticker) pairs.

    If tickers is None, refresh for all users' distinct tickers based on investment_trades.
    """
    provider = get_default_provider(get_settings().stock_price_provider)
    interval_prune_days = get_settings().stock_price_prune_days

    db = SessionLocal()
    try:
        if tickers is None:
            # 1) snapshot 우선: 브로커 동기화된 실보유 종목
            snapshot_rows = (
                db.query(InvestmentHoldingSnapshot.user_id, InvestmentHoldingSnapshot.account_id, InvestmentHoldingSnapshot.ticker)
                .distinct()
                .all()
            )

            # 2) fallback: 기존 trade 기반 종목
            trade_rows = db.query(InvestmentTrade.user_id, InvestmentTrade.ticker).distinct().all()

            # KIS 후보 (user, account, ticker)
            kis_targets = {(r[0], r[1], r[2]) for r in snapshot_rows if r[0] and r[1] and r[2]}
            # fallback 후보 (user, ticker)
            fallback_targets = {(r[0], r[1]) for r in trade_rows if r[0] and r[1]}

            # KIS quote 우선 업데이트
            for user_id, account_id, ticker in kis_targets:
                try:
                    broker_account = (
                        db.query(BrokerAccount)
                        .filter(
                            BrokerAccount.account_id == account_id,
                            BrokerAccount.broker_type == "KIS",
                            BrokerAccount.api_enabled.is_(True),
                        )
                        .first()
                    )
                    if broker_account:
                        quote = KISAdapter(db, broker_account).get_quote(ticker)
                        price = float(quote.get("current_price") or 0)
                        if price > 0:
                            await upsert_latest_and_daily(db, user_id=user_id, ticker=ticker, price=price)
                            continue

                    # KIS 실패 시 fallback provider
                    price = await provider.fetch_latest_price(ticker=ticker)
                    if price is None:
                        continue
                    await upsert_latest_and_daily(db, user_id=user_id, ticker=ticker, price=price)
                except Exception:
                    # 실패 시 기존 캐시를 유지하고 로그만 남긴다.
                    logger.exception("Failed to refresh KIS/snapshot price: user_id=%s account_id=%s ticker=%s", user_id, account_id, ticker)

            # snapshot에 없는 종목에 대해서만 fallback 업데이트
            snapshot_user_ticker = {(u, t) for u, _, t in kis_targets}
            for user_id, ticker in fallback_targets:
                if (user_id, ticker) in snapshot_user_ticker:
                    continue
                try:
                    price = await provider.fetch_latest_price(ticker=ticker)
                    if price is None:
                        continue
                    await upsert_latest_and_daily(db, user_id=user_id, ticker=ticker, price=price)
                except Exception:
                    logger.exception("Failed to refresh fallback price: user_id=%s ticker=%s", user_id, ticker)
        else:
            for user_id, ticker in tickers:
                try:
                    price = await provider.fetch_latest_price(ticker=ticker)
                    if price is None:
                        continue
                    await upsert_latest_and_daily(db, user_id=user_id, ticker=ticker, price=price)
                except Exception:
                    logger.exception("Failed to refresh price: user_id=%s ticker=%s", user_id, ticker)

        # prune old daily rows (optional)
        if interval_prune_days and interval_prune_days > 0:
            cutoff = datetime.utcnow() - timedelta(days=int(interval_prune_days))
            db.query(InvestmentPriceDaily).filter(InvestmentPriceDaily.updated_at < cutoff).delete()
            db.commit()
    finally:
        db.close()


async def investment_price_updater_loop() -> None:
    settings = get_settings()
    interval_seconds = int(settings.stock_price_update_interval_seconds)
    # 장중은 1~5분 주기를 권장. 최소 60초.
    if interval_seconds < 60:
        interval_seconds = 60

    logger.info("Starting investment price updater loop interval=%ss", interval_seconds)
    while True:
        try:
            await refresh_prices_once()
        except Exception:
            logger.exception("investment price updater cycle failed")
        await asyncio.sleep(interval_seconds)


def start_investment_price_updater_if_needed() -> None:
    """Start background updater once per process."""
    global _updater_task
    if _updater_task and not _updater_task.done():
        return
    _updater_task = asyncio.create_task(investment_price_updater_loop())

