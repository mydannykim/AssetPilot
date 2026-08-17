from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

# 투자자별 매매동향/공매도/매수유의 등은 국내(KR) 종목 전용 엔드포인트다 (실API로 확인, VOO 등 해외 종목은 unsupported-market 오류).


class InvestorFlowDay(BaseModel):
    date: str
    individual_net: float
    foreigner_net: float
    institution_net: float


class MarketFlowSummary(BaseModel):
    symbol: str
    days: list[InvestorFlowDay]
    foreigner_net_sum: float
    institution_net_sum: float
    individual_net_sum: float
    foreigner_streak: str
    institution_streak: str
    short_selling_volume_rate: float | None
    warning_count: int
    warnings: list[str]


def _streak_label(nets: list[float]) -> str:
    if not nets:
        return "데이터 없음"
    positive = nets[0] >= 0
    streak = 0
    for net in nets:
        if (net >= 0) == positive:
            streak += 1
        else:
            break
    direction = "순매수" if positive else "순매도"
    return f"{streak}일 연속 {direction}"


def summarize_market_flow(
    symbol: str,
    investor_trading_response: dict[str, Any],
    short_selling_response: dict[str, Any],
    warnings_response: dict[str, Any],
    days: int = 5,
) -> MarketFlowSummary:
    """최근 N영업일 투자자별 매매동향과 공매도/매수유의 정보를 요약한다.

    감성 판단(좋다/나쁘다)은 하지 않는다 — 숫자 요약만 제공하고, 해석은 대화형으로 Claude가 한다.
    """
    records = investor_trading_response.get("result", {}).get("records", [])[:days]
    flow_days = [
        InvestorFlowDay(
            date=r["date"],
            individual_net=float(r["individual"]["netBuyVolume"]),
            foreigner_net=float(r["foreigner"]["netBuyVolume"]),
            institution_net=float(r["institution"]["netBuyVolume"]),
        )
        for r in records
    ]

    short_records = short_selling_response.get("result", {}).get("records", [])
    short_rate = float(short_records[0]["shortSellingVolumeRate"]) if short_records else None

    raw_warnings = warnings_response.get("result", [])
    warnings = [w if isinstance(w, str) else json.dumps(w, ensure_ascii=False) for w in raw_warnings]

    return MarketFlowSummary(
        symbol=symbol,
        days=flow_days,
        foreigner_net_sum=sum(d.foreigner_net for d in flow_days),
        institution_net_sum=sum(d.institution_net for d in flow_days),
        individual_net_sum=sum(d.individual_net for d in flow_days),
        foreigner_streak=_streak_label([d.foreigner_net for d in flow_days]),
        institution_streak=_streak_label([d.institution_net for d in flow_days]),
        short_selling_volume_rate=short_rate,
        warning_count=len(warnings),
        warnings=warnings,
    )
