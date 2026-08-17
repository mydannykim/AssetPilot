# AssetPilot

토스증권 Open API와 Claude를 연동해 실시간 자산 관리를 돕고, AI로 주식 시장 뉴스와 트렌드를 탐지하는 프로젝트.

현재 단계: **Phase 3 (MCP 서버) 완료**. 자동매매 기능은 의도적으로 이후 단계로 미뤄져 있으며 아직 구현되어 있지 않다. 전체 로드맵은 [PLAN.md](PLAN.md) 참고.

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
assetpilot dashboard   # 최신 데이터로 로컬 HTML 대시보드 생성 후 브라우저로 열기
```

`report`는 스냅샷 히스토리가 쌓여야 의미 있는 값을 보여준다.

## 스냅샷 자동화 (launchd)

`assetpilot snapshot`을 하루 두 번 자동 실행하도록 등록되어 있다 (macOS launchd 사용):
- **16:00** — 국내(KRX) 장 마감(15:30) 후 30분 뒤
- **07:00** — 미국 장 마감 이후 (서머타임 여부와 무관하게 커버되도록 여유를 둠)

장중 실시간 반영(시간 단위 등)은 지금 단계에선 하지 않고 추후 필요할 때 고려한다.

```bash
scripts/launchd/install.sh   # 등록/재등록
launchctl list | grep com.assetpilot.snapshot   # 상태 확인
launchctl unload ~/Library/LaunchAgents/com.assetpilot.snapshot.plist && \
  rm ~/Library/LaunchAgents/com.assetpilot.snapshot.plist   # 해제
```

실행 로그는 `data/snapshot.log`(`.error.log`)에 쌓인다. 시간을 바꾸려면 `scripts/launchd/com.assetpilot.snapshot.plist`의 `StartCalendarInterval`을 수정한 뒤 `install.sh`를 다시 실행한다.

## 대시보드

```bash
assetpilot dashboard          # data/dashboard.html 생성 후 기본 브라우저로 열기
assetpilot dashboard --no-open   # 파일만 생성 (열지 않음)
```

실행할 때마다 최신 잔고/비중/손익/히스토리로 `data/dashboard.html`을 다시 만든다. 항상 같은 경로(`data/dashboard.html`)에 쓰기 때문에 브라우저 즐겨찾기에 등록해두면, 명령어 재실행 후 새로고침만으로 최신 상태를 볼 수 있다. 렌더링 로직은 `src/assetpilot/dashboard.py`에 있다.

## MCP 서버 (Claude Code/Desktop 연동)

`assetpilot-mcp`가 조회 전용 MCP 서버로 동작하며, `.mcp.json`에 등록되어 있어 이 프로젝트 디렉토리에서 Claude Code를 실행하면 자동으로 인식된다(세션 재시작 필요). 제공하는 도구:

| 도구 | 설명 |
|---|---|
| `get_accounts` | 계좌 목록 조회 |
| `get_holdings` | 보유 종목/평가금액/손익 조회 |
| `get_quote` | 종목 현재가 조회 |
| `get_allocation` | 원화 환산 비중 및 집중도 경고 |
| `get_asset_history` | 저장된 스냅샷 기반 기간별 평가금액 변화 |

수동으로 서버만 확인하려면:

```bash
assetpilot-mcp   # stdio MCP 서버 실행 (Claude Code가 내부적으로 호출하는 것과 동일)
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
  dashboard.py   # 로컬 HTML 대시보드 렌더링
scripts/launchd/ # 스냅샷 자동 실행용 launchd plist + 설치 스크립트
```

## 주의

- `toss_client`의 조회 엔드포인트(계좌/보유종목/시세/캔들/호가/환율)는 실제 계좌로 검증 완료했다. 세부 사항(예: `X-Tossinvest-Account` 헤더는 accountSeq를 사용, `/prices`는 `symbols` 파라미터)은 [PLAN.md](PLAN.md)에 정리되어 있다.
- 매매 실행(주문 생성/취소) 기능은 아직 구현되어 있지 않다. Phase 7(자동매매)에서 별도로 설계한다.
