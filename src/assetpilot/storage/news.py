from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..news.sources import NewsArticle
from .db import connect


def save_news_articles(db_path: Path, articles: list[NewsArticle], related_symbol: str) -> int:
    """뉴스 기사를 news_items에 저장한다. url이 이미 저장되어 있으면 건너뛴다. 신규 저장 건수를 반환."""
    if not articles:
        return 0

    fetched_at = datetime.now(timezone.utc).isoformat()
    urls = [a.url for a in articles]

    with connect(db_path) as conn:
        placeholders = ",".join("?" * len(urls))
        existing = {row["url"] for row in conn.execute(f"SELECT url FROM news_items WHERE url IN ({placeholders})", urls)}
        new_articles = [a for a in articles if a.url not in existing]
        conn.executemany(
            """
            INSERT INTO news_items (published_at, source, title, url, related_symbols, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(a.published_at, a.source, a.title, a.url, related_symbol, fetched_at) for a in new_articles],
        )
    return len(new_articles)


def list_news(db_path: Path, symbol: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    query = "SELECT published_at, source, title, url, related_symbols, sentiment, summary, fetched_at FROM news_items"
    params: list[Any] = []
    if symbol:
        query += " WHERE related_symbols = ?"
        params.append(symbol)
    query += " ORDER BY COALESCE(published_at, fetched_at) DESC LIMIT ?"
    params.append(limit)

    with connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
