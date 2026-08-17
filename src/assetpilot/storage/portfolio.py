from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import connect


def save_holdings_snapshot(
    db_path: Path,
    account_id: str,
    holdings_response: dict[str, Any],
    fx_rates_to_krw: dict[str, float] | None = None,
) -> int:
    """holdings API 응답의 items를 portfolio_snapshots에 기록한다.

    fx_rates_to_krw: {"USD": 1419.4, ...} 형태로 해당 통화 1단위의 원화 환산값을 전달한다.
    KRW는 항상 1.0으로 취급하며, 매핑에 없는 통화는 환산 없이 원값을 그대로 사용한다(경고 목적으로만 부적절).
    저장한 행 수를 반환.
    """
    fx_rates_to_krw = fx_rates_to_krw or {}
    items = holdings_response.get("result", {}).get("items", [])
    taken_at = datetime.now(timezone.utc).isoformat()

    rows = []
    for item in items:
        currency = item.get("currency", "KRW")
        eval_amount = float(item["marketValue"]["amount"])
        rate = 1.0 if currency == "KRW" else fx_rates_to_krw.get(currency, 1.0)
        rows.append(
            (
                taken_at,
                account_id,
                item["symbol"],
                currency,
                float(item["quantity"]),
                float(item["averagePurchasePrice"]),
                float(item["lastPrice"]),
                eval_amount,
                eval_amount * rate,
                float(item["profitLoss"]["amount"]),
                float(item["profitLoss"]["rate"]),
            )
        )

    with connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO portfolio_snapshots
                (taken_at, account_id, symbol, currency, quantity, avg_price, current_price,
                 eval_amount, eval_amount_krw, profit_loss, profit_loss_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)
