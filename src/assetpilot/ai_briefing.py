from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DEFAULT_BRIEFING_PATH = Path("data/ai_briefing.json")

Sentiment = Literal["positive", "neutral", "negative"]


class HoldingBriefing(BaseModel):
    symbol: str
    name: str
    sentiment: Sentiment
    summary: str
    key_points: list[str] = []


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
