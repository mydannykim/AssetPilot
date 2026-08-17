# AssetPilot

토스증권 Open API와 Claude를 연동해 실시간 자산 관리를 돕고, AI로 주식 시장 뉴스와 트렌드를 탐지하는 프로젝트.

현재 단계: **Phase 1 (조회·분석 전용)**. 자동매매 기능은 의도적으로 이후 단계로 미뤄져 있으며 아직 구현되어 있지 않다. 전체 로드맵은 [PLAN.md](PLAN.md) 참고.

## 시작하기

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

`.env.example`을 복사해 `.env`를 만들고 값을 채운다.

```bash
cp .env.example .env
```

필요한 값:
- `TOSS_CLIENT_ID`, `TOSS_CLIENT_SECRET`: 토스증권 앱 > 설정 > Open API 메뉴에서 발급 (2026-08 기준 단계적 롤아웃 중이라 계정에 따라 아직 발급이 불가능할 수 있음)
- `ANTHROPIC_API_KEY`: https://console.anthropic.com 에서 발급

## 사용법

```bash
assetpilot init-db     # 로컬 SQLite DB 초기화 (data/assetpilot.db)
assetpilot status      # 토스증권 계좌 조회
```

## 디렉토리 구조

```
src/assetpilot/
  toss_client/   # 토스증권 OAuth2 인증 + REST API 래퍼 (조회 전용)
  storage/       # SQLite 스키마 및 접근 (포트폴리오 스냅샷, 뉴스)
  news/          # 뉴스 수집 파이프라인 (Phase 4)
  analysis/      # 자산 분석 / 리밸런싱 로직 (Phase 2)
  mcp_server/    # Claude Code/Desktop용 MCP 서버 (Phase 3)
  cli.py         # CLI 진입점
  config.py      # 환경변수 로딩
```

## 주의

- `toss_client`의 API 경로는 2026-08 시점 문서 기준으로 작성되었으며, 정식 서비스 오픈 시 실제 OpenAPI 스펙(`https://openapi.tossinvest.com/openapi-docs/latest/openapi.json`)과 대조해 재확인이 필요하다.
- 매매 실행(주문 생성/취소) 기능은 아직 구현되어 있지 않다. Phase 2에서 별도로 설계한다.
