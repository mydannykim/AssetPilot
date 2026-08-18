#!/bin/bash
# AI 브리핑(뉴스+매매동향 분석)을 16:00/07:00 + 국내장 중 09:00/12:00/15:00(3시간
# 간격)에 자동 갱신하도록 launchd에 등록한다. claude -p를 호출해 Claude Pro 사용량을
# 쓰기 때문에 스냅샷(1시간마다)보다 빈도를 낮게 잡았다.
set -euo pipefail

PLIST_NAME="com.assetpilot.briefing.plist"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$PLIST_NAME"
DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

cp "$SRC" "$DEST"
launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"

echo "등록 완료: $DEST"
echo "상태 확인: launchctl list | grep com.assetpilot.briefing"
echo "수동 실행: launchctl start com.assetpilot.briefing"
echo "해제하려면: launchctl unload $DEST && rm $DEST"
