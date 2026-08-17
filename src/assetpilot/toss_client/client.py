from __future__ import annotations

from typing import Any

import httpx

from .auth import TossAuth

# 조회 전용 클라이언트 (Phase 1). 주문/조건주문 등 매매 관련 엔드포인트는
# Phase 2(자동매매) 착수 전까지 의도적으로 구현하지 않는다.


class TossClient:
    def __init__(self, client_id: str, client_secret: str, base_url: str, account_id: str | None = None):
        self._base_url = base_url.rstrip("/")
        self._account_id = account_id
        self._auth = TossAuth(client_id, client_secret, base_url)
        self._http = httpx.Client(timeout=10.0)

    def close(self) -> None:
        self._http.close()

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
        response = self._http.get(f"{self._base_url}{path}", headers=self._headers(), params=params)
        response.raise_for_status()
        return response.json()

    # --- 계좌 및 자산 ---

    def get_accounts(self) -> dict[str, Any]:
        return self._get("/api/v1/accounts")

    def get_holdings(self) -> dict[str, Any]:
        return self._get("/api/v1/holdings")

    # --- 국내 시세 ---

    def get_price(self, symbol: str) -> dict[str, Any]:
        return self._get("/api/v1/prices", params={"symbol": symbol})

    def get_candles(self, symbol: str, interval: str = "1d", count: int = 30) -> dict[str, Any]:
        return self._get("/api/v1/candles", params={"symbol": symbol, "interval": interval, "count": count})

    def get_orderbook(self, symbol: str) -> dict[str, Any]:
        return self._get("/api/v1/orderbook", params={"symbol": symbol})

    # --- 해외/지표 ---

    def get_exchange_rate(self) -> dict[str, Any]:
        return self._get("/api/v1/exchange-rate")
