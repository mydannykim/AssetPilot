from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from .analysis.fx import fetch_fx_rates_to_krw
from .analysis.market_flow import MarketFlowSummary, summarize_market_flow
from .analysis.models import Holding, PortfolioSummary, parse_holdings
from .news.collector import collect_news_for_holdings
from .storage.news import list_news
from .toss_client.client import TossClient

DEFAULT_INPUT_PATH = Path("data/briefing_input.json")


class NewsHeadline(BaseModel):
    title: str
    source: str
    published_at: str | None
    url: str


class BriefingInputHolding(BaseModel):
    symbol: str
    name: str
    market_country: str
    currency: str
    weight: float
    profit_loss_pct: float
    daily_profit_loss_pct: float
    news: list[NewsHeadline] = []
    market_flow: MarketFlowSummary | None = None  # 국내 종목만, 해외는 None


class BriefingInput(BaseModel):
    generated_at: str
    total_eval_amount_krw: float
    holdings: list[BriefingInputHolding]


def build_briefing_input(
    client: TossClient,
    db_path: Path,
    account_seq: str,
    max_news_per_symbol: int = 8,
    market_flow_days: int = 5,
) -> BriefingInput:
    """뉴스 수집 + 매매동향 조회를 실행하고, Claude가 분석할 원자재 데이터를 만든다.
    이 함수 자체는 순수 데이터 수집/집계만 하며 AI 판단(감성/요약)은 전혀 하지 않는다."""
    client.set_account(account_seq)
    holdings_response = client.get_holdings()
    currencies = {item.get("currency", "KRW") for item in holdings_response.get("result", {}).get("items", [])}
    fx_rates = fetch_fx_rates_to_krw(client, currencies)
    portfolio: PortfolioSummary = parse_holdings(holdings_response, fx_rates)

    # 뉴스는 최신 상태로 갱신 후 저장된 것을 읽어온다 (중복은 collector가 알아서 걸러줌)
    collect_news_for_holdings(client, db_path, portfolio.holdings, max_news_per_symbol)

    input_holdings = []
    weight_by_symbol = {
        h.symbol: (h.eval_amount_krw / portfolio.total_eval_amount_krw if portfolio.total_eval_amount_krw else 0.0)
        for h in portfolio.holdings
    }

    holding: Holding
    for holding in portfolio.holdings:
        news_rows = list_news(db_path, holding.symbol, max_news_per_symbol)
        news = [
            NewsHeadline(title=r["title"], source=r["source"], published_at=r["published_at"], url=r["url"])
            for r in news_rows
        ]

        market_flow: MarketFlowSummary | None = None
        if holding.currency == "KRW":  # 매매동향 API는 국내 종목 전용 (실API로 확인)
            investor = client.get_investor_trading(holding.symbol)
            short = client.get_short_selling(holding.symbol)
            warnings = client.get_stock_warnings(holding.symbol)
            market_flow = summarize_market_flow(holding.symbol, investor, short, warnings, days=market_flow_days)

        input_holdings.append(
            BriefingInputHolding(
                symbol=holding.symbol,
                name=holding.name,
                market_country=holding.market_country,
                currency=holding.currency,
                weight=weight_by_symbol[holding.symbol],
                profit_loss_pct=holding.profit_loss_pct,
                daily_profit_loss_pct=holding.daily_profit_loss_pct,
                news=news,
                market_flow=market_flow,
            )
        )

    return BriefingInput(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_eval_amount_krw=portfolio.total_eval_amount_krw,
        holdings=input_holdings,
    )


def save_briefing_input(data: BriefingInput, path: Path = DEFAULT_INPUT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
    return path
