#!/bin/bash
# assetpilot snapshot을 매일 18:00에 자동 실행하도록 launchd에 등록한다.
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
