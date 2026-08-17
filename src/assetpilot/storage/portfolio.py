from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import connect


def save_holdings_snapshot(db_path: Path, account_id: str, holdings_response: dict[str, Any]) -> int:
    """holdings API 응답의 items를 portfolio_snapshots에 기록한다. 저장한 행 수를 반환."""
    items = holdings_response.get("result", {}).get("items", [])
    taken_at = datetime.now(timezone.utc).isoformat()

    rows = [
        (
            taken_at,
            account_id,
            item["symbol"],
            float(item["quantity"]),
            float(item["averagePurchasePrice"]),
            float(item["lastPrice"]),
            float(item["marketValue"]["amount"]),
            float(item["profitLoss"]["amount"]),
            float(item["profitLoss"]["rate"]),
        )
        for item in items
    ]

    with connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO portfolio_snapshots
                (taken_at, account_id, symbol, quantity, avg_price, current_price, eval_amount, profit_loss, profit_loss_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)
