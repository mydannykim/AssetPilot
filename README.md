# AssetPilot

토스증권 Open API와 Claude를 연동해 실시간 자산 관리를 돕고, AI로 주식 시장 뉴스와 트렌드를 탐지하는 프로젝트.

현재 단계: **Phase 2 (자산 분석)**. 자동매매 기능은 의도적으로 이후 단계로 미뤄져 있으며 아직 구현되어 있지 않다. 전체 로드맵은 [PLAN.md](PLAN.md) 참고.

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
assetpilot status      # 토스증권 계좌 목록 조회
assetpilot holdings    # 보유 종목 조회
assetpilot price 005935            # 종목 현재가 조회
assetpilot snapshot    # 보유 종목을 스냅샷으로 DB에 기록 (히스토리 리포트의 기반 데이터)
assetpilot allocation  # 종목별 원화 환산 비중 및 집중도 경고
assetpilot report      # 저장된 스냅샷 기반 1일/7일/30일 전 대비 평가금액 변화
```

`report`는 스냅샷 히스토리가 쌓여야 의미 있는 값을 보여준다. `snapshot`을 주기적으로 실행하도록 cron이나 launchd에 등록해두는 것을 권장한다(예: 장 마감 후 하루 한 번).

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

- `toss_client`의 조회 엔드포인트(계좌/보유종목/시세/캔들/호가/환율)는 실제 계좌로 검증 완료했다. 세부 사항(예: `X-Tossinvest-Account` 헤더는 accountSeq를 사용, `/prices`는 `symbols` 파라미터)은 [PLAN.md](PLAN.md)에 정리되어 있다.
- 매매 실행(주문 생성/취소) 기능은 아직 구현되어 있지 않다. Phase 7(자동매매)에서 별도로 설계한다.
