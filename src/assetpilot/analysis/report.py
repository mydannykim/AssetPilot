from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

from ..storage.db import connect

PERIODS: dict[str, timedelta] = {
    "1일 전": timedelta(days=1),
    "7일 전": timedelta(days=7),
    "30일 전": timedelta(days=30),
}


@dataclass
class _SnapshotTotal:
    taken_at: datetime
    total_eval_amount_krw: float


class PeriodComparison(BaseModel):
    baseline_taken_at: str
    diff_amount_krw: float
    diff_pct: float | None


class PortfolioReport(BaseModel):
    as_of: str
    total_eval_amount_krw: float
    comparisons: dict[str, PeriodComparison | None]


def _snapshot_totals(db_path: Path, account_id: str) -> list[_SnapshotTotal]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT taken_at, SUM(eval_amount_krw) AS total
            FROM portfolio_snapshots
            WHERE account_id = ?
            GROUP BY taken_at
            ORDER BY taken_at
            """,
            (account_id,),
        ).fetchall()
    return [_SnapshotTotal(datetime.fromisoformat(row["taken_at"]), row["total"]) for row in rows]


def generate_report(db_path: Path, account_id: str) -> PortfolioReport | None:
    """저장된 스냅샷 히스토리를 기반으로 기간별 평가금액 변화 리포트를 생성한다.

    스냅샷이 하나도 없으면 None을 반환한다 — 호출측에서 `assetpilot snapshot` 안내 메시지를 출력할 것.
    """
    totals = _snapshot_totals(db_path, account_id)
    if not totals:
        return None

    latest = totals[-1]
    comparisons: dict[str, PeriodComparison | None] = {}
    for label, delta in PERIODS.items():
        cutoff = latest.taken_at - delta
        candidates = [t for t in totals if t.taken_at <= cutoff]
        if not candidates:
            comparisons[label] = None
            continue
        baseline = candidates[-1]
        diff = latest.total_eval_amount_krw - baseline.total_eval_amount_krw
        pct = (diff / baseline.total_eval_amount_krw * 100) if baseline.total_eval_amount_krw else None
        comparisons[label] = PeriodComparison(
            baseline_taken_at=baseline.taken_at.isoformat(),
            diff_amount_krw=diff,
            diff_pct=pct,
        )

    return PortfolioReport(
        as_of=latest.taken_at.isoformat(),
        total_eval_amount_krw=latest.total_eval_amount_krw,
        comparisons=comparisons,
    )
