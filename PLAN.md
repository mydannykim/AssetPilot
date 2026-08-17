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
- [x] 자산 스냅샷 자동 주기 실행 — macOS launchd로 매일 18:00 자동 실행 등록 완료 (`scripts/launchd/`)
- [x] 자산 비중/리밸런싱 분석 로직 — `assetpilot allocation` (종목별 원화 환산 비중, 집중도 임계치 경고)
- [x] 손익 리포트 생성 — `assetpilot report` (1일/7일/30일 전 대비 평가금액 변화, 스냅샷 히스토리 필요)

## Phase 3 — MCP 서버 구축
- [x] MCP 서버 스캐폴딩 (Python `mcp` SDK 2.0, `MCPServer` 클래스 — `fastmcp`가 아니라 `mcp.server.MCPServer`임을 실제 패키지로 확인)
- [x] Tool 정의: `get_accounts`, `get_holdings`, `get_quote`, `get_allocation`, `get_asset_history` (뉴스 관련 툴은 Phase 4 이후 추가 예정)
- [x] Claude Code 설정에 로컬 MCP 서버 등록(`.mcp.json`) 및 stdio 프로토콜 연동 테스트 완료 (실API 응답까지 확인)
- [ ] 인증정보(토큰) MCP 프로세스 내 안전한 접근 방식 설계 — 현재는 서버 프로세스 내 `.env` 직접 로드, 별도 격리 없음
- [ ] 인증정보(토큰) MCP 프로세스 내 안전한 접근 방식 설계

## Phase 4 — 뉴스 수집 & 트렌드 탐지
- [ ] 뉴스 소스 선정 (국내: 네이버금융/언론사 RSS, 해외: NewsAPI 등 — 결정 필요)
- [ ] 수집 파이프라인 구축 (스케줄러 기반 주기적 수집)
- [ ] 보유 종목 ↔ 뉴스 매핑 (종목명/티커 키워드 필터링)
- [ ] Claude API로 뉴스 요약 + 감성분석(긍정/부정/중립) + 시장영향도 판단
- [ ] 유사 이슈 클러스터링으로 "트렌드" 탐지
- [ ] 분석 결과 저장 및 이력 관리

## Phase 5 — 실시간 인사이트 통합
- [ ] 스케줄러로 주기적 파이프라인 실행 (장중 주기 결정)
- [ ] 알림 채널 결정 및 구현 (터미널/macOS 알림/기타 — 결정 필요)
- [ ] Claude API로 "오늘의 자산 요약 + 관련 뉴스 브리핑" 생성
- [ ] CLI 명령어 설계 (`assetpilot status`, `assetpilot news`, `assetpilot brief` 등)

## Phase 6 — 테스트 & 안정화
- [ ] 통합 테스트 (목데이터 + 실제 API 소량 검증)
- [ ] 토큰 만료/네트워크 오류 등 예외 시나리오 테스트
- [ ] 로깅 체계 구축 (요청/응답, 에러 추적)
- [ ] README 및 설정 가이드 작성

## Phase 7 — (향후 별도 진행) 자동매매 확장
> 지금 단계에서는 설계만 메모. 실제 구현은 Phase 0~6 완료 후 사용자 요청 시 별도 기획.
- [ ] 매매 전략 규칙 정의
- [ ] 리스크 한도(포지션 크기, 일일 손실 한도 등) 설계
- [ ] 주문 실행 전 승인/확인 절차 설계
- [ ] 실거래 전 모의투자(paper trading) 검증 단계
