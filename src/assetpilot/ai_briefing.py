from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DEFAULT_BRIEFING_PATH = Path("data/ai_briefing.json")

Sentiment = Literal["positive", "neutral", "negative"]
Impact = Literal["high", "medium", "low"]


class KeyPoint(BaseModel):
    point: str
    # 개별 뉴스 하나가 아니라, 관련된 뉴스 여러 건을 하나의 이슈로 묶은 단위다
    # (Phase 4의 "유사 이슈 클러스터링" 보류 항목 — 별도 알고리즘 대신 브리핑
    # 프롬프트가 Claude에게 직접 묶어서 정리하도록 요청하는 방식으로 대체).
    impact: Impact = "medium"


class HoldingBriefing(BaseModel):
    symbol: str
    name: str
    sentiment: Sentiment
    summary: str
    key_points: list[KeyPoint] = []


class AIBriefing(BaseModel):
    generated_at: str
    overall_summary: str
    holdings: list[HoldingBriefing] = []


def load_briefing(path: Path = DEFAULT_BRIEFING_PATH) -> AIBriefing | None:
    """저장된 AI 브리핑을 읽는다. 파일이 없거나 형식이 깨졌으면 None을 반환한다(대시보드는 이 경우 빈 상태를 보여줌)."""
    if not path.exists():
        return None
    try:
        return AIBriefing.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_briefing(briefing: AIBriefing, path: Path = DEFAULT_BRIEFING_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(briefing.model_dump_json(indent=2), encoding="utf-8")
    return path
