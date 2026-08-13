# 🤝 Handoff Document

- **작성 일시**: 2026-08-13 10:45 KST
- **작업 브랜치**: `main`

## 🎯 1. 작업 목표 & 현재 상태

- **목표**: 이전 세션이 남긴 worker `JSONDecodeError` 진단, UAT 1·2번(인제스트/Ask 흐름) 라이브 테스트, Phase 6(Dashboard) 완료 전환. 이어서 미커밋 상태 정리.
- **진행률**: **완료.** Phase 6은 ROADMAP.md/STATE.md 양쪽에서 `[x]` 완료로 전환됐고, `.planning/phases/06-dashboard/06-UAT.md`는 5/5 전부 `pass`다. 워킹 트리는 완전히 clean — untracked/modified 상태였던 모든 파일이 논리적 커밋으로 정리됐다. **다음 세션은 Phase 7(Integration and Ops Baseline)을 처음부터 시작한다** — `_auto_chain_active: false`라 자동으로 넘어가지 않았다.

## ✏️ 2. 주요 변경 사항 & 의사결정 (Why)

- **worker `JSONDecodeError` 근본 원인 규명·수정** (`/gsd-debug` 세션, 아카이브: `.planning/debug/resolved/worker-parse-jsondecodeerror.md`): `worker/db/service.py`의 `_rpc()`가 `raise_for_status()` 직후 무조건 `response.json()`을 호출했다. `index_source_chunk_lexical`/`index_wiki_page_lexical`은 SQL에서 `returns void`로 선언돼 있고(`0011_retrieval.sql:18-58`), PostgREST는 void 함수 호출에 **HTTP 204 No Content(빈 바디)**로 응답한다 — `raise_for_status()`는 204도 2xx라 통과시키므로 `.json()`이 그 자리에서 터졌다. `curl`로 로컬 PostgREST를 직접 호출해 204를 실측하고, `httpx.Response(204, content=b'')`로 정확히 같은 `JSONDecodeError` 문자열을 재현해 메커니즘을 확정했다. 수정: `_rpc()`가 `status_code == 204` 또는 빈 바디를 `.json()` 호출 **전에** 걸러 `None`으로 정규화 (`bf338a8`). 회귀 테스트 2건 추가(`test_service_client.py`), revert-and-reconfirm으로 수정이 실제로 버그를 고쳤음을 실증. `compile.py`도 같은 `_rpc()` 경로로 `index_wiki_page_lexical`을 호출하므로 동일하게 영향받았었다.
- **UAT 1·2번 실 라이브 검증** (`06-UAT.md`): `.env` 접근 차단이 해소되어(이전 세션의 권한 문제가 이번 세션엔 없었음) `apps/api`(port 8000)+`worker`를 로컬 스택(`SUPABASE_URL=http://127.0.0.1:54421` 등 override, 로컬 CLI 데모 키 사용) 대상으로 실제 기동하고, plain Playwright 스크립트(gstack 아님)로 `dev-test@example.test` 로그인 후 실제 텍스트 소스 등록·Ask 질문을 수행했다.
  - **테스트 1(인제스트 흐름)**: JobStepper가 업로드→파싱→컴파일→링크 동기화→임베딩 5단계를 실제 잡 타입으로 순서대로 표시. 임베딩 단계가 실제로 dead가 되어 재시도 버튼·에러 배너가 정확히 렌더됨을 확인(아래 EMBEDDING_MODEL 이슈가 원인). 재시도 클릭 → 폴링 재개 → 5단계 전부 성공으로 귀결.
  - **테스트 2(Ask 이중 인용)**: 실 OpenRouter LLM 스트리밍 답변 + citations 프레임 도착 후 클릭 가능한 숫자 배지 6개 렌더. 6개 마커를 전부 클릭해 source/wiki/source/wiki/source/wiki로 정확히 교차하며 각자 자기 인용만 여는 것을 확인 — D-10 accepted override(마커별 단일 카드)가 실제로 충분함을 실증.
  - 테스트에 쓴 raw_source/wiki_page/jobs/usage_events는 전부 삭제, 0행 확인. 로컬 서비스(worker/api/dashboard) 전부 종료.
- **로컬 `.env`에 `EMBEDDING_MODEL`/`EMBEDDING_PROVIDER` 추가** (코드 변경 아님): 임베딩 잡이 OpenRouter에 `model: null`을 보내 400을 받고 있었다 — `worker/settings.py`가 이 두 필드에 의도적으로 코드 기본값을 두지 않기 때문(이 로컬 환경이 이 코드 경로를 처음 실행했을 때만 드러남). `.env.sample`/`docs/ops/openrouter-contract-record.md`에 이미 관측·기록된 값(`baai/bge-m3` / `deepinfra/fp32`)을 `.env`에 추가해 해결. **주의: `.env`는 gitignore 대상이라 이 값은 로컬에만 있다 — 클라우드/Railway worker 서비스 env에도 이 두 키가 있는지 다음 세션에서 확인할 것.**
- **Phase 6 완료 전환**: `06-UAT.md` 5/5 pass 커밋(`e24b841`) → `gsd_run phase uat-passed` 통과 확인 → `gsd-tools query phase.complete 6` 실행(`d1c4cae`)으로 ROADMAP.md `[x]`, STATE.md `current_phase: 7` 반영. `WINDOWS.md #12`(06-07 위키 뷰어 미검증)를 `gsd-tools windows fixed 12`로 정리(테스트 3이 이미 실측 검증했었음).
- **`_auto_chain_active: false` 존중**: yolo 모드 기본 동작이면 Phase 6 완료 즉시 `/gsd-discuss-phase 7 --auto`로 자동 진입하지만, 사용자가 이 프로젝트에서 auto-chain을 명시적으로 꺼뒀다(`.planning/config.json`) — 그 설정을 존중해 Phase 7은 시작하지 않고 여기서 멈췄다.
- **미커밋 상태 정리(사용자 요청 "organize git commits")**: 세션 시작 전부터 쌓여있던 미커밋/untracked 파일들을 조사해 툴링 산출물(`.agents/`, `.pnpm-store/`, `.planning/research/.cache/`)은 `.gitignore`에 추가하고, 실제 문서/설정 산출물(architecture HTML, Phase 4 벤치마크 재실행 기록, UI-review `.gitignore`, GSD config, checklists.json, HANDOFF.md)은 7개의 논리적 커밋으로 분리해 커밋했다(`39c7ebd`~`c39fe51`).

## 🧪 3. 검증 상태

- **완료된 검증**:
  - worker fix: `apps/worker/tests/test_service_client.py`에 회귀 테스트 2건 추가, 워크스페이스 전체 pytest 410/410 통과
  - `06-UAT.md`: 5/5 pass (테스트 1·2는 이번 세션 실 라이브 검증, 테스트 3·4·5는 이전 세션 실 라이브 검증)
  - `gsd_run phase uat-passed 6 --require-verification`: `passed: true`, blockers 없음
  - `06-VERIFICATION.md`: status `passed` (기존)
  - `06-SECURITY.md`: STRIDE 25/25 closed (기존)
  - Phase 6 전환 후 `git status -s` clean 확인
- **미검증/후속 항목**:
  - **[신규] 클라우드 worker env에 `EMBEDDING_MODEL`/`EMBEDDING_PROVIDER`가 있는지 미확인** — 로컬만 고쳤다. Railway worker 서비스 env var를 다음 세션에서 점검할 것 (없으면 프로덕션에서도 임베딩 잡이 전부 dead로 간다).
  - `WINDOWS.md` #13(App Router에 `error.tsx`/`not-found.tsx` 전무), #14(`GraphCanvas.tsx` hex 리터럴 8개) — 여전히 open, 사용자가 후순위로 미룸. 급하지 않으면 Phase 7에서.
  - Phase 4 HNSW `strict_order` vs `relaxed_order` 실측 비교 (`WINDOWS.md` #10) — 여전히 open, Phase 7 OPS 이월로 이미 문서화됨.
  - Ask 임베딩 실패(테스트 1에서 발견)의 근본 원인(`EMBEDDING_MODEL`/`PROVIDER` 누락)은 로컬 `.env`로만 고쳤다 — 위 항목과 동일.

## ⚠️ 4. 주의사항 & 남은 작업 (TODO)

- [ ] **클라우드/Railway worker env에 `EMBEDDING_MODEL=baai/bge-m3`, `EMBEDDING_PROVIDER=deepinfra/fp32`가 설정돼 있는지 확인** (최우선 신규 항목) — 로컬 `.env`에만 추가했다.
- [ ] **Phase 7(Integration and Ops Baseline) 시작** — `.planning/phases/07-*/` 디렉토리도 `CONTEXT.md`도 아직 없다. `/gsd-discuss-phase 7`로 시작.
- [ ] (선택) `WINDOWS.md` #13·#14 — error/not-found 바운더리, GraphCanvas hex 리터럴. 급하지 않음.
- [ ] (선택) `WINDOWS.md` #10 — Phase 4 HNSW strict/relaxed order 실측 비교, 대용량 코퍼스 필요(Phase 7 OPS 이월로 이미 문서화됨).
- **주의사항**:
  - **`docs/design-systems/design-tokens.css`는 여전히 건드리지 않는다** — 토큰 파일 자체의 원래 웨이트 값은 그대로, 컴포넌트별 오버라이드로만 처리하는 기존 결정 유지.
  - **로컬 스택으로 `apps/api`+`worker`+dashboard를 띄우는 절차**(다음에 재현할 때 참고): DB/REST는 `docker exec supabase_db_NexusWiki`/`http://127.0.0.1:54421` (Kong 게이트웨이, `supabase status -o env`로 로컬 데모 키 확인 가능). `apps/api`는 기본 8000 포트(`PORT` env로 override), `apps/dashboard`는 `NEXT_PUBLIC_API_URL`을 8000으로 맞춰야 한다(`.env.local`의 기존 값 `54421`은 stale). Ask 스트리밍을 쓰려면 api/worker 양쪽에 동일한 `QUERY_EMBEDDING_INTERNAL_TOKEN`/`LLM_STREAM_INTERNAL_TOKEN`을 주입해야 worker의 내부 리스너(8081)가 뜬다.
  - **커밋 정리는 완료됐다** — `git status -s`가 clean이다. 다음 세션에서 또 미커밋 잔여물이 쌓이면 같은 방식(툴링 산출물 vs 실제 문서 산출물 구분)으로 정리할 것.
  - `dev-test@example.test` 계정 비밀번호는 이번 세션에 GoTrue admin API로 재설정했다(`UatVerify-2026!`) — 로컬 전용, 다음 세션에서 다시 라이브 테스트할 때 재사용 가능.

## 🚀 5. 다음 세션 재개 안내

다음 세션 시작 시 `/catchup` 스킬을 실행하거나 아래 멘트를 입력하세요:

> "HANDOFF.md 확인하고, 클라우드 worker env에 EMBEDDING_MODEL/EMBEDDING_PROVIDER 설정돼 있는지 확인한 다음 Phase 7(Integration and Ops Baseline)을 /gsd-discuss-phase 7로 시작해줘."
