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
- **뉴스 2축 구조 추가**: (1) 보유 종목별 뉴스 (2) 종목 무관 일반 시황(코스피/코스닥/증시/금리) 뉴스 — `related_symbols='MARKET'`로 구분 저장. 네이버 뉴스 API는 검토 후 보류(공식 API 있으나 별도 Client ID/Secret 발급 필요, 구글 뉴스로 충분히 커버됨)
- **AI 브리핑 대시보드 패널** 추가 — `data/ai_briefing.json`을 대시보드가 읽어서 종목별 감성/요약/핵심포인트 + 전체 총평을 표시. 실데이터로 생성해 다크/라이트 모드 렌더링 확인
- **AI 브리핑 자동 갱신 파이프라인 구축** — `assetpilot prepare-briefing`(순수 데이터 수집) → 헤드리스 `claude -p`(`scripts/launchd/run_briefing.sh`)가 분석해 저장, 스냅샷과 동일한 스케줄(16:00/07:00)로 launchd 등록. 과정에서 겪은 문제와 해결:
  - 로컬 `claude` CLI가 별도 로그인 필요함을 발견 (Claude Code 세션 인증과 무관). `claude setup-token`은 토큰을 자동 저장하지 않고 화면에만 출력하는 방식이라 실패 — `claude auth login`(표준 로그인)으로 해결
  - 파일쓰기 권한 규칙은 `Write(path)`가 아니라 `Edit(path)`로 검사됨을 확인
  - 비대화형(`-p`) 모드에서는 프로젝트 `.claude/settings.json`이 워크스페이스 신뢰 절차 때문에 적용되지 않음 → `--permission-mode dontAsk --settings '{...}'`로 그 실행 하나에만 직접 권한(`Edit(data/ai_briefing.json)`)을 넘기는 방식으로 해결
  - 사용자의 실제 터미널에서 수동 실행 검증 완료 + `launchctl start com.assetpilot.briefing`으로 launchd 트리거 실행까지 검증 완료 (정상적으로 `data/ai_briefing.json` 갱신됨). **Phase 4 AI 브리핑 자동화 파이프라인 전체 완료**
- 자동화 파이프라인 안정성 1차 점검 — launchd 등록 후 `snapshot.log` 3회 성공, `briefing.log` 1회 성공(둘 다 에러 로그 없음, `launchctl list` 종료코드 0) 확인

### Phase 5 — 실시간 인사이트 통합 (진행 중)
- 알림 채널을 macOS 알림센터로 결정 (터미널 로그/이메일 대안 중 선택)
- `src/assetpilot/notify.py` 추가 — `osascript display notification`으로 `ai_briefing.json`의 `overall_summary`를 알림으로 띄움. AppleScript 문자열 이스케이프 처리
- `assetpilot notify-briefing` CLI 명령 추가, `scripts/launchd/run_briefing.sh`가 헤드리스 `claude -p` 분석 직후 자동 호출하도록 연결 — 16:00/07:00 브리핑 자동 갱신 시마다 알림이 뜨도록 구성 완료
- 사용자가 클릭 시 대시보드 오픈을 요청 — `terminal-notifier`(Homebrew, MIT 라이선스) 설치 확인 후 진행. `notify.py`가 `shutil.which`로 설치 여부를 감지해 있으면 `-open <dashboard.html file:// URI>`로 클릭 액션을 연결하고, 없으면 기존 `osascript display notification`으로 자동 폴백하도록 구현
- `run_briefing.sh`에 `assetpilot dashboard --no-open` 단계를 추가해 알림 발송 전 대시보드를 항상 최신 상태로 재생성 — 클릭해서 열리는 화면이 그 시점 최신 브리핑을 반영하도록 보장
- 사용자 실환경에서 알림 발송 + 클릭 시 대시보드 오픈까지 최종 확인 완료. **알림 채널 항목 완료**
- 다음날(08-18) 아침 07:00 자동 실행 점검 중 발견: 스냅샷은 성공했으나 브리핑은 실패(`launchctl` 종료코드 1) — `collect_market_news`가 구글 뉴스 RSS 호출 중 `httpx.ReadTimeout`으로 실패해 그날 브리핑 전체가 스킵됨. 재시도 로직이 없던 게 원인
- `src/assetpilot/news/sources.py`의 `fetch_google_news`에 재시도(최대 2회, 지수 백오프) 추가 — `toss_client._get`과 동일한 패턴. 실호출로 정상 동작 확인. (Phase 6에서 예정했던 "예외 시나리오 처리"를 하나 앞당겨 처리함)
- 07:00 실행 실패 후 `launchctl start com.assetpilot.briefing`으로 수동 백필 시도 중 **두 번째 버그 발견**: 장중(당일, 아직 미확정)에는 투자자별 매매동향 레코드의 individual/foreigner/institution 필드가 `null`로 오는 경우가 있는데, `summarize_market_flow`가 항상 dict라고 가정해 `TypeError: 'NoneType' object is not subscriptable`로 크래시. 미확정 레코드는 건너뛰도록 수정(`src/assetpilot/analysis/market_flow.py`) — 재실행으로 정상 동작 확인, 11:45 기준 브리핑 백필 완료
- launchd `StartCalendarInterval`은 실패한 실행을 자동 재시도하지 않음(정해진 시각에만 트리거) — 이번처럼 실패 시 수동 복구는 `launchctl start com.assetpilot.<label>`로 즉시 트리거 가능

### Phase 6 — 테스트 & 안정화 (진행 중)
- **로깅 체계 구축**: 오전 장애 조사 때 로그에 타임스탬프가 없어서 `stat`으로 파일 mtime을 보고 실행 시각을 추측해야 했던 게 계기. `src/assetpilot/logging_config.py` 추가 — `data/assetpilot.log`에 로테이션(2MB×3) 파일 핸들러로 타임스탬프 포함 로그 기록, `sys.excepthook`으로 처리되지 않은 예외도 자동 기록
- CLI(`assetpilot`)/MCP 서버(`assetpilot-mcp`) 양쪽 진입점에 `configure_logging()` 연결
- `toss_client._get` 재시도, `fetch_google_news` 재시도, `summarize_market_flow`의 미확정 레코드 스킵에 경고 로그 추가 — 다음에 비슷한 실패가 나면 로그만 보고 원인 파악 가능하도록
- 실행 테스트: 정상 커맨드(`assetpilot snapshot`) 로그 기록 확인 + 강제 예외로 `excepthook` 타임스탬프 기록 확인
- 로깅 작업 중 코드를 살펴보다 **세 번째 버그 발견**: `TossAuth._fetch_token`(토큰 발급)에는 재시도 로직이 없었음 — `TossClient._get`(데이터 조회)만 재시도가 있고, 토큰 발급 자체가 일시적 5xx/429나 네트워크 오류를 만나면 즉시 실패하는 구멍. `_get`과 동일한 재시도 정책 추가
### Phase 4 — 보류 항목 마무리 (유사 이슈 클러스터링, 시장영향도 세분화)
- 사용자 질문("이건 너가 해줘야 하는 거지?")에 확인: 이 프로젝트는 처음부터 AI 판단(감성분석 등)을 알고리즘으로 짜지 않고 Claude가 직접 데이터를 읽고 해석하는 방식을 써왔음 — 클러스터링/영향도 판단도 같은 원칙 적용
- `ai_briefing.py`: `key_points: list[str]` → `key_points: list[KeyPoint]`로 스키마 변경, `KeyPoint`에 `point`(이슈 요약)와 `impact`(high/medium/low) 필드
- `run_briefing.sh` 프롬프트에 "같은 사안을 다루는 기사들을 하나의 이슈로 묶어서 정리 + 영향도 판단" 명시적으로 요청, 판단 기준(실적 서프라이즈·정책 발표 = high 등) 예시 추가
- `dashboard.py`: 이슈별 영향도를 도트(●●●/●●○/●○○)로 표시, high는 굵게 강조. 기존 `--warn` 색상(집중도 경고용)과 의미가 겹치지 않도록 별도 톤(텍스트 강조)으로 구현
- `tests/test_ai_briefing.py` 추가 — `KeyPoint` 기본값/JSON 직렬화 검증 2건, 전체 11개 테스트 통과
- 스키마가 바뀌어서 기존 `data/ai_briefing.json`(구 스키마)은 파싱 실패 → `load_briefing()`이 `None` 반환(대시보드는 빈 상태로 정상 폴백) 확인 후, `run_briefing.sh` 재실행으로 새 스키마 브리핑 재생성해 검증
- `pytest`를 dev 의존성으로 도입(`pyproject.toml` `[project.optional-dependencies].dev`), `tests/`에 9개 테스트 작성: 토스 API 재시도(전송 오류/재시도 가능 상태코드/최대 재시도 초과 3종), 토큰 발급 재시도(재시도 가능 vs 즉시 실패 2종), 구글 뉴스 RSS 재시도 2종, 오늘 발견한 매매동향 null 레코드 버그의 회귀 테스트 2종. `httpx.MockTransport`(토스 API)와 `monkeypatch`(뉴스 RSS)로 실제 네트워크 없이 검증, 백오프 대기는 `time.sleep` 무력화로 스킵(`tests/conftest.py`). `TossClient`에 테스트용 `transport` 주입 파라미터 추가. 전체 9개 통과(0.16초) + 실계좌로 `assetpilot status` 재검증까지 완료
- README 정리 — 그동안 기능별로 흩어져 있던 설정 단계(env, init-db, 스냅샷 launchd, claude 로그인, 브리핑 launchd, terminal-notifier)를 "처음 한 번만 하는 설정" 체크리스트로 한 곳에 모음. **Phase 6(테스트 & 안정화) 4개 항목 전부 완료**

### Phase 5 — 장중 주기적 실행 (완료)
- 범위/주기 결정: 스냅샷+브리핑 전체를 국내장 시간(09:00~15:00) 1시간마다 추가 실행 (사용자 선택 — 비용 트레이드오프 설명 후 "스냅샷+브리핑 전체"/"1시간마다" 선택받음)
- `com.assetpilot.snapshot.plist`/`com.assetpilot.briefing.plist`의 `StartCalendarInterval`에 09~15시 엔트리 7개씩 추가 (기존 16:00/07:00과 합쳐 9개 트리거). 처음엔 요일(Weekday 1-5)까지 제한하려다 plist가 35개 엔트리로 불어나서, 기존 16:00/07:00 항목처럼 요일 필터 없이 심플하게 유지하는 쪽으로 되돌림(주말 장중 실행은 시세가 그대로라 사실상 무해)
- `plutil -lint`로 plist 문법 검증 후 `install.sh`/`install_briefing.sh` 재실행으로 launchd에 반영, `launchctl print`로 calendarinterval 9개 등록 확인
- 사용자 질문(맥북 꺼짐/와이파이 없을 때 자동 복구되는지, 빈도가 높으면 Claude Pro 사용량이 빨리 닳는지)에 답하며 재조정: (1) launchd `StartCalendarInterval`은 놓친 실행을 나중에 몰아서 재실행해주지 않음(깨어난 뒤엔 별도 조치 없이 다음 예정 시각부터 정상 작동) — 알려주기만 하고 로직 변경은 안 함 (2) 스냅샷(토스 API만 사용)은 Claude 사용량과 무관하니 1시간마다 유지, 브리핑(헤드리스 `claude -p`, Claude Pro 사용량 소모)만 09:00/12:00/15:00(3시간 간격, 기존 포함 총 5개 트리거)로 낮춤. `com.assetpilot.briefing.plist` 재수정 후 재등록, `launchctl print`로 5개 확인. **Phase 5 실질적으로 완료** (남은 건 `assetpilot brief` 같은 통합 CLI 명령 여부뿐, 보류 중)
