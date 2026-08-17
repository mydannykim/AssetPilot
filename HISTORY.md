# AssetPilot 개발 히스토리

진행 상황 기록. 체크리스트는 [PLAN.md](PLAN.md), 사용법은 [README.md](README.md) 참고.

## 2026-08-17

### Phase 0 — 준비 & 설계
- 프로젝트 구조 스캐폴딩 (`src/assetpilot/{toss_client,storage,analysis,news,mcp_server}/`)
- Python 가상환경 + 의존성 설정 (httpx, pydantic, click, mcp, feedparser 등)
- git 저장소 초기화, [github.com/mydannykim/AssetPilot](https://github.com/mydannykim/AssetPilot)에 연결
- `.env` 기반 시크릿 관리, SQLite DB 스키마 초기화

### Phase 1 — 토스증권 연동 (조회 전용)
- OAuth2 Client Credentials 인증 구현, 실계좌로 검증
- 계좌/보유종목/시세/캔들/호가/환율 조회 API 연동 — 전부 실API 호출로 검증
- 문서에 없던 실제 API 세부사항 발견: `X-Tossinvest-Account` 헤더는 `accountNo`가 아니라 `accountSeq` 사용, `/prices`는 `symbols`(복수), `/candles`·`/orderbook`은 `symbol`(단수)
- 포트폴리오 스냅샷 SQLite 저장 (`assetpilot snapshot`), 429/5xx 재시도 로직 추가

### Phase 2 — 자산 관리 코어 로직
- Pydantic 기반 포트폴리오 모델 (`Holding`, `PortfolioSummary`), 환율 반영 원화 환산
- 자산 비중/집중도 경고 (`assetpilot allocation`)
- 스냅샷 히스토리 기반 기간별 변화 리포트 (`assetpilot report`)
- 로컬 HTML 대시보드 (`assetpilot dashboard`) — 실행할 때마다 최신 데이터로 재생성, 브라우저 자동 실행. 콕핏 컨셉 디자인, 다크/라이트 모드, 색맹 접근성 검증 완료

### Phase 3 — MCP 서버
- Python `mcp` SDK 2.0 기반 서버 구현 (`mcp.server.MCPServer`, `fastmcp` 아님 — 실제 패키지로 확인)
- `.mcp.json`으로 Claude Code에 등록, stdio 프로토콜로 실API 응답까지 연동 테스트 완료
- 스냅샷 자동화: macOS launchd로 하루 2회(16:00 국내장 마감 후, 07:00 미국장 마감 후) 자동 실행 등록

## 2026-08-18

### Phase 4 — 뉴스 수집 & 동향 탐지 (진행 중)
- 토스 매매동향 데이터 연동: 투자자별(개인/외국인/기관) 매매동향, 공매도, 신용거래, 매수유의사항 — **국내 종목 전용**(해외 종목은 `unsupported-market` 오류로 확인)
- 뉴스 수집 파이프라인: 구글 뉴스 RSS 기반(무료, API 키 불필요). 해외 종목은 티커만으로 검색하면 노이즈가 커서(예: "VOO"→포뮬러1 기사 오매칭) 토스 종목정보 API로 영문 정식명+유형(ETF/주식)을 붙여 검색어 보강
- **AI 감성분석/요약은 의도적으로 미구현** — `news_items`의 `sentiment`/`summary` 컬럼은 비워두고 원문만 저장. Anthropic API 빌링 미설정 상태라, 실제 해석은 Claude Code 세션에서 대화형으로 수행하는 방식 채택 (비용 없이 바로 사용 가능)
- 토스 앱의 자체 AI 분석 기능은 Open API 범위 밖임을 문서로 확인 (뉴스/리포트/컨센서스 엔드포인트 자체가 없음)
