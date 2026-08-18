from __future__ import annotations

import httpx
import pytest

import assetpilot.news.sources as sources

_SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>테스트 기사</title><link>https://example.test/a</link>
<source url="https://example.test">테스트 출처</source></item>
</channel></rss>"""


def test_fetch_google_news_retries_on_timeout_then_succeeds(monkeypatch: pytest.MonkeyPatch):
    calls = {"n": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.ReadTimeout("simulated timeout", request=httpx.Request("GET", url))
        return httpx.Response(200, text=_SAMPLE_RSS, request=httpx.Request("GET", url))

    monkeypatch.setattr(sources.httpx, "get", fake_get)

    articles = sources.fetch_google_news("삼성전자", locale="ko")

    assert calls["n"] == 2
    assert len(articles) == 1
    assert articles[0].title == "테스트 기사"


def test_fetch_google_news_gives_up_after_max_retries(monkeypatch: pytest.MonkeyPatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        raise httpx.ReadTimeout("simulated timeout", request=httpx.Request("GET", url))

    monkeypatch.setattr(sources.httpx, "get", fake_get)

    with pytest.raises(httpx.ReadTimeout):
        sources.fetch_google_news("삼성전자", locale="ko")
