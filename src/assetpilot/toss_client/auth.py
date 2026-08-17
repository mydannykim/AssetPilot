from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

# 참고: https://developers.tossinvest.com/docs (2026-08 기준, 정식 오픈 전 단계적 롤아웃 중)
# 실제 서비스 시작 전 OpenAPI 스펙(https://openapi.tossinvest.com/openapi-docs/latest/openapi.json)과
# 대조해 경로/파라미터를 재확인할 것.
TOKEN_PATH = "/oauth2/token"


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
        response = http.post(
            f"{self._base_url}{TOKEN_PATH}",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()
        expires_in = payload.get("expires_in", 3600)
        return AccessToken(value=payload["access_token"], expires_at=time.time() + expires_in)
