from __future__ import annotations

import calendar
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
import httpx

_USER_AGENT = "Mozilla/5.0 (compatible; AssetPilotBot/0.1)"

_LOCALES = {
    "ko": {"hl": "ko", "gl": "KR", "ceid": "KR:ko"},
    "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
}

_MAX_RETRIES = 2
_BACKOFF_BASE_SECONDS = 1.0


@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    published_at: str | None  # ISO 8601, 없으면 None


def fetch_google_news(query: str, *, locale: str = "ko", max_items: int = 10) -> list[NewsArticle]:
    """구글 뉴스 RSS 검색 결과를 가져온다.

    feedparser가 직접 요청하면 User-Agent 미설정으로 빈 결과가 오는 경우가 있어(실제로 확인함),
    httpx로 먼저 받아온 뒤 feedparser로 파싱한다.
    """
    params = {"q": query, **_LOCALES.get(locale, _LOCALES["ko"])}

    last_error: Exception | None = None
    response = None
    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            time.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
        try:
            response = httpx.get(
                "https://news.google.com/rss/search",
                params=params,
                headers={"User-Agent": _USER_AGENT},
                timeout=10.0,
            )
            response.raise_for_status()
            break
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_error = exc
            response = None
            continue
    if response is None:
        assert last_error is not None
        raise last_error

    feed = feedparser.parse(response.text)

    articles = []
    for entry in feed.entries[:max_items]:
        source = entry.get("source")
        source_title = source.get("title") if isinstance(source, dict) else (source or "")
        published_at = None
        if entry.get("published_parsed"):
            published_at = datetime.fromtimestamp(
                calendar.timegm(entry.published_parsed), tz=timezone.utc
            ).isoformat()
        articles.append(NewsArticle(title=entry.title, url=entry.link, source=source_title, published_at=published_at))
    return articles
