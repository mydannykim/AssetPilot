from __future__ import annotations

from mcp.server import MCPServer

from ..analysis.allocation import compute_allocation
from ..analysis.fx import fetch_fx_rates_to_krw
from ..analysis.market_flow import summarize_market_flow
from ..analysis.models import parse_holdings
from ..analysis.report import generate_report
from ..config import load_settings
from ..news.collector import MARKET_NEWS_SYMBOL, collect_market_news, collect_news_for_holdings
from ..storage.news import list_news
from ..toss_client.client import TossClient

settings = load_settings()
_client = TossClient(
    client_id=settings.toss_client_id,
    client_secret=settings.toss_client_secret,
    base_url=settings.toss_api_base_url,
)

mcp = MCPServer(
    name="assetpilot",
    instructions=(
        "토스증권 계좌의 잔고/보유종목/시세를 조회하고 자산 비중, 손익 히스토리를 분석하는 조회 전용 도구 모음. "
        "매매(주문 생성/취소) 기능은 제공하지 않는다."
    ),
)


def _resolve_account_seq(account_seq: str | None) -> str:
    if account_seq:
        return account_seq
    accounts = _client.get_accounts()["result"]
    return str(accounts[0]["accountSeq"])


@mcp.tool()
def get_accounts() -> dict:
    """토스증권에 연결된 계좌 목록을 조회한다."""
    return _client.get_accounts()


@mcp.tool()
def get_holdings(account_seq: str | None = None) -> dict:
    """보유 종목과 평가금액/손익을 조회한다. account_seq를 생략하면 첫 번째 계좌를 사용한다."""
    seq = _resolve_account_seq(account_seq)
    _client.set_account(seq)
    return _client.get_holdings()


@mcp.tool()
def get_quote(symbol: str) -> dict:
    """종목 코드의 현재가를 조회한다. 예: 005935(삼성전자우), VOO"""
    return _client.get_price(symbol)


@mcp.tool()
def get_allocation(account_seq: str | None = None, threshold: float = 0.3) -> dict:
    """보유 종목의 원화 환산 비중을 계산하고, threshold(기본 0.3=30%)를 초과하는 종목에 집중도 경고를 표시한다."""
    seq = _resolve_account_seq(account_seq)
    _client.set_account(seq)
    holdings = _client.get_holdings()
    currencies = {item.get("currency", "KRW") for item in holdings.get("result", {}).get("items", [])}
    fx_rates = fetch_fx_rates_to_krw(_client, currencies)
    portfolio = parse_holdings(holdings, fx_rates)
    return compute_allocation(portfolio, threshold).model_dump()


@mcp.tool()
def get_asset_history(account_seq: str | None = None) -> dict:
    """`assetpilot snapshot`으로 저장된 스냅샷 히스토리를 바탕으로 1일/7일/30일 전 대비 평가금액 변화를 조회한다."""
    seq = _resolve_account_seq(account_seq)
    report = generate_report(settings.db_path, seq)
    if report is None:
        return {"error": "저장된 스냅샷이 없습니다. `assetpilot snapshot`을 먼저 실행해 히스토리를 쌓아주세요."}
    return report.model_dump()


@mcp.tool()
def get_market_flow(symbol: str, days: int = 5) -> dict:
    """국내(KR) 종목의 최근 N영업일 투자자별(개인/외국인/기관) 매매동향, 공매도 비중, 매수 유의사항을 조회한다.
    해외 종목(예: VOO)은 지원하지 않는다 — 토스 API 자체가 국내 종목 전용이다.
    숫자만 반환하며 좋다/나쁘다 판단은 하지 않는다. 판단은 이 데이터를 읽는 쪽(Claude)이 한다."""
    investor = _client.get_investor_trading(symbol)
    short = _client.get_short_selling(symbol)
    warnings = _client.get_stock_warnings(symbol)
    return summarize_market_flow(symbol, investor, short, warnings, days=days).model_dump()


@mcp.tool()
def collect_news(account_seq: str | None = None, max_items_per_symbol: int = 8) -> dict:
    """보유 종목별 뉴스 + 일반 시황(코스피/증시 등) 뉴스, 두 축으로 구글 뉴스에서 검색해 로컬 DB에 저장한다.
    감성분석/요약은 하지 않는다 — 원문 제목/링크만 저장한다. 저장 후 get_news로 읽어서 직접 해석할 것.
    시황 뉴스는 symbol='MARKET'으로 저장된다."""
    seq = _resolve_account_seq(account_seq)
    _client.set_account(seq)
    holdings = _client.get_holdings()
    currencies = {item.get("currency", "KRW") for item in holdings.get("result", {}).get("items", [])}
    fx_rates = fetch_fx_rates_to_krw(_client, currencies)
    portfolio = parse_holdings(holdings, fx_rates)
    counts = collect_news_for_holdings(_client, settings.db_path, portfolio.holdings, max_items_per_symbol)
    counts[MARKET_NEWS_SYMBOL] = collect_market_news(settings.db_path, max_items_per_symbol)
    return counts


@mcp.tool()
def get_news(symbol: str | None = None, limit: int = 20) -> list[dict]:
    """collect_news로 저장된 뉴스 목록을 조회한다 (제목/출처/링크/발행시각).
    symbol을 생략하면 전체, 'MARKET'을 지정하면 일반 시황 뉴스만 조회한다."""
    return list_news(settings.db_path, symbol, limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
