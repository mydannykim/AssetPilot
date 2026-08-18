from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .auth import TossAuth

# 조회 전용 클라이언트 (Phase 1). 주문/조건주문 등 매매 관련 엔드포인트는
# Phase 2(자동매매) 착수 전까지 의도적으로 구현하지 않는다.

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 1.0

_logger = logging.getLogger(__name__)


class TossClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str,
        account_id: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._account_id = account_id
        self._auth = TossAuth(client_id, client_secret, base_url)
        self._http = httpx.Client(timeout=10.0, transport=transport)

    def close(self) -> None:
        self._http.close()

    def set_account(self, account_seq: str) -> None:
        """X-Tossinvest-Account 헤더 값. accountNo가 아니라 accounts 응답의 accountSeq를 받는다(실API 확인 완료)."""
        self._account_id = account_seq

    def __enter__(self) -> "TossClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._auth.get_token(self._http)}"}
        if self._account_id:
            headers["X-Tossinvest-Account"] = self._account_id
        return headers

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            if attempt > 0:
                _logger.warning("재시도 %d/%d: %s (직전 오류: %s)", attempt, _MAX_RETRIES, path, last_error)
                time.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
            try:
                response = self._http.get(f"{self._base_url}{path}", headers=self._headers(), params=params)
            except httpx.TransportError as exc:
                last_error = exc
                continue
            if response.status_code in _RETRYABLE_STATUS_CODES:
                last_error = httpx.HTTPStatusError(
                    f"retryable status {response.status_code}", request=response.request, response=response
                )
                continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                _logger.error("요청 실패: %s (status=%d)", path, response.status_code)
                raise
            _logger.debug("요청 성공: %s", path)
            return response.json()
        _logger.error("최대 재시도(%d회) 초과: %s", _MAX_RETRIES, path)
        assert last_error is not None
        raise last_error

    # --- 계좌 및 자산 ---

    def get_accounts(self) -> dict[str, Any]:
        return self._get("/api/v1/accounts")

    def get_holdings(self) -> dict[str, Any]:
        return self._get("/api/v1/holdings")

    # --- 국내 시세 ---

    def get_price(self, symbol: str) -> dict[str, Any]:
        # /prices는 파라미터명이 "symbols"(복수), 나머지 두 엔드포인트는 "symbol"(단수) — 실API로 확인함
        return self._get("/api/v1/prices", params={"symbols": symbol})

    def get_candles(self, symbol: str, interval: str = "1d", count: int = 30) -> dict[str, Any]:
        return self._get("/api/v1/candles", params={"symbol": symbol, "interval": interval, "count": count})

    def get_orderbook(self, symbol: str) -> dict[str, Any]:
        return self._get("/api/v1/orderbook", params={"symbol": symbol})

    # --- 해외/지표 ---

    def get_exchange_rate(self, base_currency: str = "USD", quote_currency: str = "KRW") -> dict[str, Any]:
        return self._get(
            "/api/v1/exchange-rate",
            params={"baseCurrency": base_currency, "quoteCurrency": quote_currency},
        )

    # --- 종목 정보 / 동향 데이터 (국내(KR) 종목 전용, 실API로 확인함) ---

    def get_stock_info(self, symbol: str) -> dict[str, Any]:
        return self._get("/api/v1/stocks", params={"symbols": symbol})

    def get_investor_trading(self, symbol: str) -> dict[str, Any]:
        """투자자별(개인/외국인/기관) 매매동향."""
        return self._get(f"/api/v1/stocks/{symbol}/investor-trading")

    def get_short_selling(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/api/v1/stocks/{symbol}/short-selling")

    def get_credit_trades(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/api/v1/stocks/{symbol}/credit-trades")

    def get_program_trades(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/api/v1/stocks/{symbol}/program-trades")

    def get_securities_lending(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/api/v1/stocks/{symbol}/securities-lending")

    def get_stock_warnings(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/api/v1/stocks/{symbol}/warnings")
