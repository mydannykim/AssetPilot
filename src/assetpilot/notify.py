from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .ai_briefing import AIBriefing

MAX_SUMMARY_LEN = 200


def _escape_applescript(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _truncate_summary(text: str) -> str:
    text = text.strip()
    if len(text) > MAX_SUMMARY_LEN:
        return text[:MAX_SUMMARY_LEN] + "…"
    return text


def send_briefing_notification(
    briefing: AIBriefing,
    title: str = "AssetPilot 브리핑",
    dashboard_path: Path | None = None,
) -> None:
    """생성된 AI 브리핑의 총평을 macOS 알림으로 띄운다.

    `terminal-notifier`가 설치되어 있으면 클릭 시 dashboard_path를 열도록 연결한다
    (없으면 클릭 액션이 없는 기본 `osascript` 알림으로 대체한다).
    """
    summary = _truncate_summary(briefing.overall_summary)
    terminal_notifier = shutil.which("terminal-notifier")

    if terminal_notifier:
        args = [terminal_notifier, "-title", title, "-message", summary]
        if dashboard_path is not None and dashboard_path.exists():
            args += ["-open", dashboard_path.resolve().as_uri()]
        subprocess.run(args, check=True)
        return

    script = (
        f'display notification "{_escape_applescript(summary)}" '
        f'with title "{_escape_applescript(title)}" sound name "Glass"'
    )
    subprocess.run(["osascript", "-e", script], check=True)
