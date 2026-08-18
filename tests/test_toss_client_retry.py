from __future__ import annotations

import httpx
import pytest

from assetpilot.toss_client.client import TossClient


def _make_client(handler) -> TossClient:
    return TossClient(
        client_id="id",
        client_secret="secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )


def _token_response() -> httpx.Response:
    return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})


def test_get_retries_on_transient_status_then_succeeds():
    calls = {"token": 0, "data": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            calls["token"] += 1
            return _token_response()
        calls["data"] += 1
        if calls["data"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"result": "ok"})

    client = _make_client(handler)
    result = client.get_accounts()

    assert result == {"result": "ok"}
    assert calls["data"] == 3


def test_get_retries_on_transport_error_then_succeeds():
    calls = {"data": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response()
        calls["data"] += 1
        if calls["data"] < 2:
            raise httpx.ReadTimeout("simulated timeout", request=request)
        return httpx.Response(200, json={"result": "ok"})

    client = _make_client(handler)
    result = client.get_accounts()

    assert result == {"result": "ok"}
    assert calls["data"] == 2


def test_get_gives_up_after_max_retries():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return _token_response()
        return httpx.Response(503)

    client = _make_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.get_accounts()


def test_token_fetch_retries_on_transient_status_then_succeeds():
    calls = {"token": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            calls["token"] += 1
            if calls["token"] < 2:
                return httpx.Response(500)
            return _token_response()
        return httpx.Response(200, json={"result": "ok"})

    client = _make_client(handler)
    result = client.get_accounts()

    assert result == {"result": "ok"}
    assert calls["token"] == 2


def test_token_fetch_does_not_retry_on_non_retryable_error():
    calls = {"token": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            calls["token"] += 1
            return httpx.Response(401, json={"error": "invalid_client"})
        return httpx.Response(200, json={"result": "ok"})

    client = _make_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.get_accounts()

    assert calls["token"] == 1
