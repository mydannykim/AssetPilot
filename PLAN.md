# AssetPilot 개발 계획

토스증권 Open API + Claude 연동 실시간 자산관리 & 뉴스 트렌드 탐지 프로젝트

## 확정된 방향
- **매매 범위**: 1단계는 조회·분석 전용(잔고, 시세, 뉴스 인사이트). 자동매매는 2단계로 별도 진행.
- **배포 형태**: 로컬 CLI/스크립트
- **Claude 연동**: MCP 서버(대화형 조회) + Claude API(백그라운드 분석·알림) 둘 다 — 단, Anthropic API 크레딧/빌링 미설정으로 **당분간 보류**. 조회 기능(Phase 1)은 Claude Code(이 세션)와 대화하며 진행하고, 실제 코드 내 Claude API 연동은 빌링 설정 이후 재개.

## 리스크/전제
- 토스증권 Open API는 2026년 5월 사전신청 시작, 단계적 롤아웃 중이었으나 **2026-08-17 실API 테스트로 정상 발급·호출 확인 완료** (계좌 조회, 보유종목, 시세, 캔들, 호가 모두 동작).
- Anthropic API 키는 발급했으나 크레딧 잔액 부족(BillingError) — console.anthropic.com에서 결제수단 등록 필요.

### 실API로 확인된 엔드포인트 세부사항 (문서에 없던 내용)
- `X-Tossinvest-Account` 헤더 값은 `accountNo`가 아니라 `accounts` 응답의 **`accountSeq`**를 사용해야 함
- `/api/v1/prices`는 파라미터명이 **`symbols`**(복수), `/api/v1/candles`·`/api/v1/orderbook`은 **`symbol`**(단수) — API 내에서 일관되지 않음

---

## Phase 0 — 준비 & 설계
- [x] 토스증권 Open API 사전신청 상태 확인, client_id/client_secret 발급 (설정 > Open API)
- [x] Claude API 키 발급 (Anthropic Console) — 빌링 등록은 별도 필요
- [x] 기술 스택 확정 (Python — httpx, pydantic, apscheduler, click, mcp SDK, anthropic SDK)
- [x] git 저장소 초기화 및 디렉토리 구조 설계 (GitHub: github.com/mydannykim/AssetPilot)
- [x] 시크릿 관리 방식 결정 (.env + .gitignore, 절대 커밋 금지)
- [x] 기본 디렉토리 스캐폴딩 (`src/assetpilot/{toss_client,mcp_server,news,analysis,storage}/`, `data/`)

## Phase 1 — 토스증권 연동 (조회 전용)
- [x] OAuth2 Client Credentials 인증 플로우 구현 — 실API 검증 완료
- [x] 토큰 저장 및 자동 갱신 로직 (만료 60초 전 자동 재발급)
- [x] 계좌 잔고/보유종목 조회 API 연동 — 실API 검증 완료 (`assetpilot status`, `assetpilot holdings`)
- [x] 국내(KRX) 시세/캔들/호가 조회 API 연동 — 실API 검증 완료 (`assetpilot price`). 미국 시세는 미검증
- [ ] 응답 데이터 파싱 & 로컬 저장 (SQLite에 스냅샷 기록) — DB 스키마만 있고 저장 로직 미구현
- [ ] API 에러/레이트리밋 처리 및 재시도 로직 — 현재는 기본 `raise_for_status`만 있음, 재시도/백오프 없음
- [ ] 목데이터 기반 단위 테스트

## Phase 2 — 자산 관리 코어 로직
- [x] 포트폴리오 데이터 모델 설계 (Pydantic `Holding`/`PortfolioSummary`, 환율 반영 원화 환산 포함)
- [x] 자산 스냅샷 기록 → 시계열 히스토리 DB (`assetpilot snapshot`)
- [x] 자산 스냅샷 자동 주기 실행 — macOS launchd로 하루 2회(16:00 국내장 마감 후, 07:00 미국장 마감 후) 자동 실행 등록 완료 (`scripts/launchd/`)
- [x] 자산 비중/리밸런싱 분석 로직 — `assetpilot allocation` (종목별 원화 환산 비중, 집중도 임계치 경고)
- [x] 손익 리포트 생성 — `assetpilot report` (1일/7일/30일 전 대비 평가금액 변화, 스냅샷 히스토리 필요)
- [x] 로컬 HTML 대시보드 — `assetpilot dashboard` (실행할 때마다 `data/dashboard.html`을 최신 데이터로 재생성, 브라우저 자동 실행)

## Phase 3 — MCP 서버 구축
- [x] MCP 서버 스캐폴딩 (Python `mcp` SDK 2.0, `MCPServer` 클래스 — `fastmcp`가 아니라 `mcp.server.MCPServer`임을 실제 패키지로 확인)
- [x] Tool 정의: `get_accounts`, `get_holdings`, `get_quote`, `get_allocation`, `get_asset_history`, `get_market_flow`, `collect_news`, `get_news`
- [x] Claude Code 설정에 로컬 MCP 서버 등록(`.mcp.json`) 및 stdio 프로토콜 연동 테스트 완료 (실API 응답까지 확인)
- [ ] 인증정보(토큰) MCP 프로세스 내 안전한 접근 방식 설계 — 현재는 서버 프로세스 내 `.env` 직접 로드, 별도 격리 없음

## Phase 4 — 뉴스 수집 & 트렌드 탐지
- [x] 뉴스 소스 선정 — 구글 뉴스 RSS 검색 (무료, API 키 불필요, `feedparser` + `httpx`로 실검증 완료). 해외 종목은 티커만으로는 노이즈가 커서(예: "VOO"→포뮬러1 기사 오매칭) 토스 종목정보 API의 영문 정식명+유형(ETF/주식)을 붙여 검색어를 보강함. 네이버 뉴스 검색 API(공식, 무료, Client ID/Secret 발급 필요)는 확인만 해두고 보류 — 필요해지면 소스만 교체/추가
- [x] 수집 파이프라인 구축 — `assetpilot news` / MCP `collect_news`가 **2축**으로 수집: (1) 보유 종목별 뉴스, (2) 종목 무관 일반 시황(코스피/증시/금리) 뉴스 — `related_symbols='MARKET'`로 구분 저장. `prepare-briefing`이 매번 최신화하며, 그 외엔 수동 실행
- [x] 보유 종목 ↔ 뉴스 매핑 — 종목명(우선주 표기 제거) 또는 영문 정식명으로 검색, `news_items.related_symbols`에 종목코드 저장
- [x] 국내 종목 매매동향/공매도/매수유의 데이터 연동 — `assetpilot trends` / MCP `get_market_flow` (외국인·기관 순매수 스트릭, 공매도 비중). 해외 종목은 토스 API 자체가 미지원
- [x] AI 요약/감성분석 — `news_items.sentiment`/`summary` 컬럼 대신 별도 `data/ai_briefing.json` + `assetpilot dashboard`의 "AI 브리핑" 패널로 구현. AssetPilot 코드가 Anthropic API를 직접 호출하지 않고, Claude Code가 `get_news`/`get_market_flow`를 읽어 분석한 결과를 `save_briefing()`으로 저장하는 방식(빌링 불필요). 지금은 수동으로 1회 생성해 검증함
- [x] AI 브리핑 자동 갱신 — `assetpilot prepare-briefing`(순수 데이터 수집) → 헤드리스 `claude -p`(`scripts/launchd/run_briefing.sh`)가 분석해 `ai_briefing.json` 저장, 스냅샷과 동일 스케줄(16:00/07:00)로 launchd 등록 완료. 권한은 그 실행 하나에 `--settings`로 직접 전달(`Edit(data/ai_briefing.json)`만 허용 — 파일쓰기는 `Write`가 아니라 `Edit` 규칙으로 검사됨, 비대화형 모드는 프로젝트 `.claude/settings.json`을 신뢰 절차 없이는 안 읽음). 로컬 `claude` CLI 로그인은 `claude setup-token`이 아니라 `claude auth login`으로 해결. `launchctl start com.assetpilot.briefing`으로 실제 트리거 실행까지 검증 완료
- [ ] 유사 이슈 클러스터링으로 "트렌드" 탐지 — 보류
- [ ] 시장영향도 판단 세분화 — 보류

## Phase 5 — 실시간 인사이트 통합
- [ ] 스케줄러로 주기적 파이프라인 실행 (장중 주기 결정)
- [x] 알림 채널 결정 및 구현 — macOS 알림센터로 결정. `assetpilot notify-briefing`이 `data/ai_briefing.json`의 `overall_summary`를 알림으로 띄움. 클릭 시 `data/dashboard.html`이 열리도록 `terminal-notifier`(Homebrew) 설치 및 연동 완료 — 미설치 환경에서는 클릭 액션 없는 `osascript display notification`으로 자동 폴백. `scripts/launchd/run_briefing.sh`가 헤드리스 `claude -p` 분석 → `assetpilot dashboard --no-open`(대시보드 최신화) → `assetpilot notify-briefing` 순으로 자동 호출하므로 16:00/07:00 갱신 시마다 최신 대시보드로 연결되는 알림이 뜬다
- [x] "오늘의 자산 요약 + 관련 뉴스 브리핑" 생성 — Phase 4에서 이미 구현됨(`data/ai_briefing.json`, 헤드리스 `claude -p` 방식). Claude API 직접 호출이 아니라 Claude Code 세션 자체를 쓰는 방식으로 대체 완료(빌링 불필요)
- [ ] CLI 명령어 설계 (`assetpilot status`, `assetpilot news`, `assetpilot brief` 등) — 개별 명령은 이미 있음(`status`/`news`/`notify-briefing` 등), `brief` 통합 명령 여부는 보류

## Phase 6 — 테스트 & 안정화
- [ ] 통합 테스트 (목데이터 + 실제 API 소량 검증)
- [ ] 토큰 만료/네트워크 오류 등 예외 시나리오 테스트 — 08-18 실전에서 2건 발견 후 수정: (1) 구글 뉴스 RSS 타임아웃 → `fetch_google_news` 재시도 로직 추가 (2) 장중 당일 매매동향 레코드의 null 필드 → `summarize_market_flow`에서 미확정 레코드 스킵. 토스 API 쪽 토큰 만료 등은 아직 미점검
- [x] 로깅 체계 구축 — `src/assetpilot/logging_config.py`가 `data/assetpilot.log`에 타임스탬프 포함 구조화 로그를 기록(로테이션 2MB×3). CLI(`assetpilot`)와 MCP 서버(`assetpilot-mcp`) 진입점 모두에서 `configure_logging()` 호출. `sys.excepthook`으로 처리되지 않은 예외도 타임스탬프와 함께 자동 기록(08-18 오전 장애 조사 때 실행 시각을 파일 mtime으로 추측해야 했던 문제 해결). `toss_client._get`/`fetch_google_news`의 재시도마다 경고 로그, `summarize_market_flow`가 미확정 매매동향 레코드를 건너뛸 때도 경고 로그. launchd의 `*.log`/`*.error.log`(작업별 stdout/stderr)는 그대로 유지 — 이 로그는 그와 별도로 코드 내부 이벤트를 추적하는 용도
- [ ] README 및 설정 가이드 작성

## Phase 7 — (향후 별도 진행) 자동매매 확장
> 지금 단계에서는 설계만 메모. 실제 구현은 Phase 0~6 완료 후 사용자 요청 시 별도 기획.
- [ ] 매매 전략 규칙 정의
- [ ] 리스크 한도(포지션 크기, 일일 손실 한도 등) 설계
- [ ] 주문 실행 전 승인/확인 절차 설계
- [ ] 실거래 전 모의투자(paper trading) 검증 단계
