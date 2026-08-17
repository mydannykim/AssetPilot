#!/bin/bash
# 뉴스/매매동향 데이터를 모으고(prepare-briefing), 헤드리스 Claude Code로 분석해
# data/ai_briefing.json을 갱신한다. .claude/settings.json에 briefing_input.json
# 읽기 / ai_briefing.json 쓰기만 허용되어 있어 그 외 파일은 건드릴 수 없다.
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

source .venv/bin/activate
assetpilot prepare-briefing

PROMPT=$(cat <<'EOF'
data/briefing_input.json 파일을 읽어줘. 두 축의 데이터가 들어있어:
1. holdings: 보유 종목별 최근 뉴스 제목/출처/발행일 + (국내 종목만) 투자자별
   매매동향·공매도·매수유의 데이터
2. market_news: 보유 종목과 무관한 일반 시황(코스피/코스닥/증시/금리 등) 뉴스

이 데이터를 바탕으로 종목별 감성/요약과, 시황을 반영한 전체 총평을 작성한 뒤
아래 JSON 스키마 형식 그대로 data/ai_briefing.json에 저장해줘
(다른 파일은 읽거나 쓰지 말 것):

{
  "generated_at": "<ISO 8601 현재 시각>",
  "overall_summary": "<market_news의 큰 흐름 + 포트폴리오 상황을 종합한 2~4문장 총평>",
  "holdings": [
    {
      "symbol": "<종목코드>",
      "name": "<종목명>",
      "sentiment": "positive|neutral|negative",
      "summary": "<뉴스와 매매동향을 종합한 2~4문장 요약>",
      "key_points": ["<핵심 포인트1>", "<핵심 포인트2>", "..."]
    }
  ]
}

과장하지 말고 데이터에 근거해서 중립적으로 판단해줘. 특별한 이슈가 없으면
"특이사항 없음"이라고 정직하게 써줘. sentiment는 뉴스 논조와 매매동향(있는 경우)을
같이 고려해서 판단하되, 확신이 없으면 neutral로 둬.
EOF
)

claude -p "$PROMPT" --output-format text --permission-mode default
