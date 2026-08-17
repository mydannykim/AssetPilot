from __future__ import annotations

from pathlib import Path

from ..analysis.models import Holding
from ..storage.news import save_news_articles
from ..toss_client.client import TossClient
from .sources import fetch_google_news

# 종목에 속하지 않는 "일반 시황" 뉴스를 저장할 때 쓰는 가상 심볼 (news_items.related_symbols)
MARKET_NEWS_SYMBOL = "MARKET"
_MARKET_QUERY = "코스피 OR 코스닥 OR 증시 OR 연준 OR 금리"


def _query_for_holding(client: TossClient, holding: Holding) -> tuple[str, str]:
    """(검색어, locale)을 반환한다."""
    if holding.currency == "KRW":
        name = holding.name
        if name.endswith("우") and len(name) > 2:  # 우선주 표기 제거 (삼성전자우 -> 삼성전자)
            name = name[:-1]
        return name, "ko"

    # 해외 종목은 티커만으로 검색하면 노이즈가 크다 (예: "VOO"가 무관한 기사와 매칭됨).
    # 토스 종목정보 API로 영문 정식명 + 유형(ETF/주식)을 붙여 검색어를 보강한다.
    try:
        info = client.get_stock_info(holding.symbol)["result"][0]
    except (KeyError, IndexError, TypeError):
        info = None

    if info:
        english_name = info.get("englishName") or holding.name
        suffix = "ETF" if info.get("securityType") == "ETF" else "stock"
        return f"{english_name} {suffix}", "en"
    return f"{holding.name} stock", "en"


def collect_news_for_holdings(
    client: TossClient, db_path: Path, holdings: list[Holding], max_items_per_symbol: int = 8
) -> dict[str, int]:
    """보유 종목별로 관련 뉴스를 검색해 저장한다.

    감성분석/요약은 하지 않는다 — 원문 제목/링크만 저장하고, 해석은 대화형으로 진행한다.
    반환값: {symbol: 신규 저장 건수}
    """
    saved_counts: dict[str, int] = {}
    for holding in holdings:
        query, locale = _query_for_holding(client, holding)
        articles = fetch_google_news(query, locale=locale, max_items=max_items_per_symbol)
        saved_counts[holding.symbol] = save_news_articles(db_path, articles, holding.symbol)
    return saved_counts


def collect_market_news(db_path: Path, max_items: int = 10) -> int:
    """보유 종목과 무관한 일반 시황(코스피/코스닥/증시/금리 등) 뉴스를 검색해 저장한다.
    종목별 뉴스와 구분하기 위해 MARKET_NEWS_SYMBOL로 저장한다. 신규 저장 건수를 반환."""
    articles = fetch_google_news(_MARKET_QUERY, locale="ko", max_items=max_items)
    return save_news_articles(db_path, articles, MARKET_NEWS_SYMBOL)
