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
    purchase_amount: float
    purchase_amount_krw: float
    eval_amount: float
    eval_amount_krw: float
    profit_loss: float
    profit_loss_pct: float
    profit_loss_krw: float
    daily_profit_loss: float
    daily_profit_loss_pct: float
    daily_profit_loss_krw: float


class PortfolioSummary(BaseModel):
    total_eval_amount_krw: float
    total_purchase_amount_krw: float
    total_profit_loss_krw: float
    total_profit_loss_pct: float
    total_daily_profit_loss_krw: float
    total_daily_profit_loss_pct: float
    holdings: list[Holding]


def parse_holdings(holdings_response: dict[str, Any], fx_rates_to_krw: dict[str, float] | None = None) -> PortfolioSummary:
    """holdings API 응답을 구조화된 모델로 변환한다.

    fx_rates_to_krw: {"USD": 1419.4, ...} — KRW 외 통화의 원화 환산 환율.
    통화가 섞인 포트폴리오도 하나의 원화 총계로 합산할 수 있도록 종목별 KRW 환산값을 함께 계산한다.
    """
    fx_rates_to_krw = fx_rates_to_krw or {}
    items = holdings_response.get("result", {}).get("items", [])

    holdings = []
    for item in items:
        currency = item.get("currency", "KRW")
        rate = 1.0 if currency == "KRW" else fx_rates_to_krw.get(currency, 1.0)

        purchase_amount = float(item["marketValue"]["purchaseAmount"])
        eval_amount = float(item["marketValue"]["amount"])
        profit_loss = float(item["profitLoss"]["amount"])
        daily = item.get("dailyProfitLoss") or {}
        daily_profit_loss = float(daily.get("amount") or 0.0)

        holdings.append(
            Holding(
                symbol=item["symbol"],
                name=item.get("name", item["symbol"]),
                market_country=item.get("marketCountry", ""),
                currency=currency,
                quantity=float(item["quantity"]),
                avg_price=float(item["averagePurchasePrice"]),
                current_price=float(item["lastPrice"]),
                purchase_amount=purchase_amount,
                purchase_amount_krw=purchase_amount * rate,
                eval_amount=eval_amount,
                eval_amount_krw=eval_amount * rate,
                profit_loss=profit_loss,
                profit_loss_pct=float(item["profitLoss"]["rate"]),
                profit_loss_krw=profit_loss * rate,
                daily_profit_loss=daily_profit_loss,
                daily_profit_loss_pct=float(daily.get("rate") or 0.0),
                daily_profit_loss_krw=daily_profit_loss * rate,
            )
        )

    total_eval_amount_krw = sum(h.eval_amount_krw for h in holdings)
    total_purchase_amount_krw = sum(h.purchase_amount_krw for h in holdings)
    total_profit_loss_krw = sum(h.profit_loss_krw for h in holdings)
    total_daily_profit_loss_krw = sum(h.daily_profit_loss_krw for h in holdings)
    prev_total_krw = total_eval_amount_krw - total_daily_profit_loss_krw

    return PortfolioSummary(
        total_eval_amount_krw=total_eval_amount_krw,
        total_purchase_amount_krw=total_purchase_amount_krw,
        total_profit_loss_krw=total_profit_loss_krw,
        total_profit_loss_pct=(total_profit_loss_krw / total_purchase_amount_krw) if total_purchase_amount_krw else 0.0,
        total_daily_profit_loss_krw=total_daily_profit_loss_krw,
        total_daily_profit_loss_pct=(total_daily_profit_loss_krw / prev_total_krw) if prev_total_krw else 0.0,
        holdings=holdings,
    )
