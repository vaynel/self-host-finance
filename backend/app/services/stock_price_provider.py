"""Stock price provider abstraction.

현재는 외부 API를 바로 붙이기보다는, '최신가 fetch'를 담당하는 공급자 함수를 분리해두었습니다.
환경에 따라 provider는 달라질 수 있습니다.
"""

from __future__ import annotations

import csv
import io
from typing import Optional

import httpx


class StockPriceProvider:
    async def fetch_latest_price(self, *, ticker: str) -> Optional[float]:
        raise NotImplementedError


class StooqStockPriceProvider(StockPriceProvider):
    """Stooq(무키) 기반: 가장 최근 close를 current price로 사용합니다."""

    def _to_stooq_symbol(self, ticker: str) -> str:
        # stooq는 보통 US를 .us로 받습니다. (예: aapl.us)
        if "." in ticker:
            return ticker.lower()
        return f"{ticker.lower()}.us"

    async def fetch_latest_price(self, *, ticker: str) -> Optional[float]:
        symbol = self._to_stooq_symbol(ticker)
        # CSV 컬럼: Date,Open,High,Low,Close,Volume 등
        # i 파라미터는 데이터 granularity를 바꿀 수 있으나, 환경에 따라 daily만 올 수도 있습니다.
        url = f"https://stooq.com/q/l/?s={symbol}&i=5&h&e=csv"

        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url)
            r.raise_for_status()

        text = r.text
        if not text.strip():
            return None

        # CSV 파싱 후 마지막 row의 Close를 사용
        f = io.StringIO(text)
        reader = csv.DictReader(f)
        last: dict[str, str] | None = None
        for row in reader:
            if not row:
                continue
            last = row

        if not last:
            return None

        close_str = last.get("Close") or last.get("close") or ""
        try:
            return float(close_str)
        except Exception:
            return None


def get_default_provider(provider_name: str | None) -> StockPriceProvider:
    name = (provider_name or "").strip().lower()
    if name == "stooq":
        return StooqStockPriceProvider()
    # fallback: mock provider (return None so system doesn't write garbage)
    return StooqStockPriceProvider()

