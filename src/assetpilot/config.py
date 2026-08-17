from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    toss_client_id: str
    toss_client_secret: str
    toss_api_base_url: str
    anthropic_api_key: str
    db_path: Path


def load_settings() -> Settings:
    missing = [
        name
        for name in ("TOSS_CLIENT_ID", "TOSS_CLIENT_SECRET", "ANTHROPIC_API_KEY")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(
            f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}. "
            ".env.example을 복사해 .env를 만들고 값을 채워주세요."
        )

    return Settings(
        toss_client_id=os.environ["TOSS_CLIENT_ID"],
        toss_client_secret=os.environ["TOSS_CLIENT_SECRET"],
        toss_api_base_url=os.environ.get("TOSS_API_BASE_URL", "https://openapi.tossinvest.com"),
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        db_path=PROJECT_ROOT / os.environ.get("ASSETPILOT_DB_PATH", "data/assetpilot.db"),
    )
