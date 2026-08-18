from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_retry_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """재시도 백오프로 테스트가 느려지지 않도록 time.sleep을 무력화한다."""
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
