from __future__ import annotations

from ..toss_client.client import TossClient


def fetch_fx_rates_to_krw(client: TossClient, currencies: set[str]) -> dict[str, float]:
    """holdings에 등장하는 통화들의 KRW 환산 환율을 조회한다. KRW 자체는 조회하지 않는다."""
    rates: dict[str, float] = {}
    for currency in currencies:
        if currency == "KRW":
            continue
        response = client.get_exchange_rate(base_currency=currency, quote_currency="KRW")
        rates[currency] = float(response["result"]["rate"])
    return rates
