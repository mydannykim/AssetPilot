from __future__ import annotations

from pydantic import BaseModel

from .models import PortfolioSummary

DEFAULT_CONCENTRATION_THRESHOLD = 0.3  # 단일 종목이 전체 자산의 30%를 넘으면 경고


class AllocationItem(BaseModel):
    symbol: str
    name: str
    eval_amount_krw: float
    weight: float


class AllocationReport(BaseModel):
    total_eval_amount_krw: float
    breakdown: list[AllocationItem]
    warnings: list[str]


def compute_allocation(
    portfolio: PortfolioSummary, threshold: float = DEFAULT_CONCENTRATION_THRESHOLD
) -> AllocationReport:
    total = portfolio.total_eval_amount_krw
    breakdown = []
    warnings = []
    for holding in portfolio.holdings:
        weight = holding.eval_amount_krw / total if total else 0.0
        breakdown.append(
            AllocationItem(
                symbol=holding.symbol,
                name=holding.name,
                eval_amount_krw=holding.eval_amount_krw,
                weight=weight,
            )
        )
        if weight > threshold:
            warnings.append(f"{holding.name} 비중이 {weight:.1%}로 임계치({threshold:.0%})를 초과했습니다.")

    breakdown.sort(key=lambda item: item.weight, reverse=True)
    return AllocationReport(total_eval_amount_krw=total, breakdown=breakdown, warnings=warnings)
