from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

# 참고: https://developers.tossinvest.com/docs (2026-08 기준, 정식 오픈 전 단계적 롤아웃 중)
# 실제 서비스 시작 전 OpenAPI 스펙(https://openapi.tossinvest.com/openapi-docs/latest/openapi.json)과
# 대조해 경로/파라미터를 재확인할 것.
TOKEN_PATH = "/oauth2/token"

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 1.0

_logger = logging.getLogger(__name__)


@dataclass
class AccessToken:
    value: str
    expires_at: float  # unix timestamp

    @property
    def is_expired(self) -> bool:
        # 만료 60초 전에 미리 갱신
        return time.time() >= self.expires_at - 60


class TossAuth:
    """OAuth2 Client Credentials Grant로 토스증권 access token을 발급/캐싱/자동 갱신한다."""

    def __init__(self, client_id: str, client_secret: str, base_url: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._token: AccessToken | None = None

    def get_token(self, http: httpx.Client) -> str:
        if self._token is None or self._token.is_expired:
            self._token = self._fetch_token(http)
        return self._token.value

    def _fetch_token(self, http: httpx.Client) -> AccessToken:
        # 데이터 조회 API(_get)는 재시도가 있는데 토큰 발급 자체는 없어서, 일시적 5xx/429나
        # 네트워크 오류에도 즉시 실패하던 문제가 있었다. 같은 재시도 정책을 여기도 적용한다.
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            if attempt > 0:
                _logger.warning("토큰 발급 재시도 %d/%d (직전 오류: %s)", attempt, _MAX_RETRIES, last_error)
                time.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
            try:
                response = http.post(
                    f"{self._base_url}{TOKEN_PATH}",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                )
            except httpx.TransportError as exc:
                last_error = exc
                continue
            if response.status_code in _RETRYABLE_STATUS_CODES:
                last_error = httpx.HTTPStatusError(
                    f"retryable status {response.status_code}", request=response.request, response=response
                )
                continue
            response.raise_for_status()
            payload = response.json()
            expires_in = payload.get("expires_in", 3600)
            return AccessToken(value=payload["access_token"], expires_at=time.time() + expires_in)
        _logger.error("토큰 발급 최대 재시도(%d회) 초과", _MAX_RETRIES)
        assert last_error is not None
        raise last_error
