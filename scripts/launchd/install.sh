#!/bin/bash
# assetpilot snapshot을 하루 2회(16:00/07:00) + 국내장 중(09:00~15:00, 1시간마다)
# 자동 실행하도록 launchd에 등록한다. 스케줄은 com.assetpilot.snapshot.plist 참고.
set -euo pipefail

PLIST_NAME="com.assetpilot.snapshot.plist"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$PLIST_NAME"
DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

cp "$SRC" "$DEST"
launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"

echo "등록 완료: $DEST"
echo "상태 확인: launchctl list | grep com.assetpilot.snapshot"
echo "해제하려면: launchctl unload $DEST && rm $DEST"
