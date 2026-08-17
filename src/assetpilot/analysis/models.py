from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Holding(BaseModel):
    symbol: str
    name: str
    market_country: str
    currency: str
    quantity: float
    avg_price: float
    current_price: float
    eval_amount: float
    eval_amount_krw: float
    profit_loss: float
    profit_loss_pct: float


class PortfolioSummary(BaseModel):
    total_eval_amount_krw: float
    holdings: list[Holding]


def parse_holdings(holdings_response: dict[str, Any], fx_rates_to_krw: dict[str, float] | None = None) -> PortfolioSummary:
    """holdings API 응답을 구조화된 모델로 변환한다.

    fx_rates_to_krw: {"USD": 1419.4, ...} — KRW 외 통화의 원화 환산 환율.
    """
    fx_rates_to_krw = fx_rates_to_krw or {}
    items = holdings_response.get("result", {}).get("items", [])

    holdings = []
    for item in items:
        currency = item.get("currency", "KRW")
        eval_amount = float(item["marketValue"]["amount"])
        rate = 1.0 if currency == "KRW" else fx_rates_to_krw.get(currency, 1.0)
        holdings.append(
            Holding(
                symbol=item["symbol"],
                name=item.get("name", item["symbol"]),
                market_country=item.get("marketCountry", ""),
                currency=currency,
                quantity=float(item["quantity"]),
                avg_price=float(item["averagePurchasePrice"]),
                current_price=float(item["lastPrice"]),
                eval_amount=eval_amount,
                eval_amount_krw=eval_amount * rate,
                profit_loss=float(item["profitLoss"]["amount"]),
                profit_loss_pct=float(item["profitLoss"]["rate"]),
            )
        )

    total_eval_amount_krw = sum(h.eval_amount_krw for h in holdings)
    return PortfolioSummary(total_eval_amount_krw=total_eval_amount_krw, holdings=holdings)
