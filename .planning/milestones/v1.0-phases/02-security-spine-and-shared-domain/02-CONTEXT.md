# Phase 2: Security Spine and Shared Domain - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

테넌트 격리를 *코드 규약*이 아니라 **역량 부재**로 강제하고, 라우터를 하나라도 쓰기 전에 네 가지 기반 계약을 확정한다 — DB 트랜스포트(스파이크로 판정), 공용 한국어 토크나이저, 결정적 슬러그, 워커 큐 계약.

15개 요구사항: SEC-01~06 (service key 격리 · `UserDb` 403 매핑 · 교차 테넌트 테스트), DOM-01~09 (트랜스포트 스파이크 · 마이그레이션 `0007` · 토크나이저 · 슬러그 · 워커 스켈레톤).

**이 페이즈가 하지 않는 것:** 실제 도메인 라우터(Phase 3~5), LLM 호출(Phase 3), 수집 파이프라인(Phase 3), 검색 융합 로직(Phase 4). Phase 2는 그 전부가 딛고 설 바닥만 만든다.

</domain>

<decisions>
## Implementation Decisions

### DB 트랜스포트 스파이크 (DOM-01)

- **D-01 (판정 기준 — 사용자 결정):** 스파이크는 `current_setting()` 반환값이 아니라 **RPC 안에서 뜬 `EXPLAIN (ANALYZE)` 계획 + 실제 반환 행 수**로 판정한다. `HNSW Index Scan`이 쓰였는지와 workspace post-filter 후에도 `k`개가 채워지는지를 함께 본다. "GUC가 설정되었다"와 "플래너가 실제로 그것을 따랐다"는 다르며, 전자만 확인하면 Phase 4에서 조용히 seq scan으로 이탈해도 모른다. 이 장치가 곧 RTV-08의 EXPLAIN 회귀 테스트 원형이 된다.

- **D-02 (스파이크 코퍼스 — 사용자 결정):** **합성 데이터, 적대적 분포.** 랜덤 1536차 벡터 수만~십만 행을 넣되 타깃 워크스페이스가 전체의 **1~2%만** 차지하게 만들어 post-filter가 반드시 물어지도록 강제한다. 임베딩 API 비용 0, 재현 가능, 판정 조건을 직접 통제한다. 코퍼스가 작으면 RPC든 asyncpg든 똑같이 통과해 스파이크가 아무것도 판정하지 못한다 — 이 함정을 피하는 것이 합성 선택의 유일한 이유다.

- **D-03 (애매할 때의 tie-break):** RPC 경로는 **RTV-03의 GUC 3종(`hnsw.iterative_scan` · `hnsw.ef_search` · `hnsw.max_scan_tuples`)이 전부 적용되고** EXPLAIN이 HNSW Index Scan을 보이며 `k`개가 채워질 때만 채택한다. 하나라도 미달이면 **asyncpg + Supavisor session mode**로 간다. 부분 적용을 받아들이면 `ef_search` 기본값 40에 묶인 채 Phase 4에서 반드시 되돌아오게 되고, 그때는 검색 함수·`UserDb`·라우터가 이미 그 위에 쌓여 있다. — **Reversibility:** one-way — 트랜스포트를 뒤집으면 `0007`의 검색 함수 시그니처, `UserDb` 구현, Phase 4 융합 계층이 함께 움직인다. 그래서 애매하면 되돌리기 싼 쪽이 아니라 **확실한 쪽**으로 기운다.

- **D-04 (RLS 유지 방식이 트랜스포트마다 다르다):** 이게 두 선택지의 진짜 차이다.
  - **RPC 채택 시:** `SECURITY INVOKER` 함수 + 요청자 JWT. RLS가 자동으로 걸린다. `search_path`는 함수에 고정.
  - **asyncpg 채택 시:** 트랜잭션마다 `set local role authenticated` + `set local request.jwt.claims = '...'`를 **직접** 세워야 `auth.uid()`가 값을 본다. ⚠️ 하나라도 빠지면 격리가 **에러 없이 조용히 풀린다**. 이 경우 `UserDb`가 트랜잭션 진입점에서 GUC 세팅을 강제하고, 세팅 없이 쿼리를 실행할 수 있는 공개 API를 두지 않는다.

- **D-05 (산출물과 결정 잠금 위치):** 스파이크 결과 문서는 `docs/ops/db-transport-spike.md` (Phase 1의 `docs/ops/rtt-baseline.md` 관례와 대칭). 재현용 SQL/스크립트도 커밋한다. **결정 자체는 `checklists.json > decisions.db_transport`에 잠근다** — 프로젝트 수명 전체에 걸친 결정이므로 `CLAUDE.md`의 인용 계층 규칙상 phase CONTEXT가 아니라 `checklists.json`이 맞다. 이후 파일 헤더는 이 키를 인용한다.

### service key 격리 집행 (SEC-01/02/03/05)

- **D-06 (⚠️ "역량 부재"는 import 차단이 아니라 *키의 부재*로 달성된다):** 스카우트로 확인한 사실 — 루트 `pyproject.toml`의 uv 워크스페이스 멤버는 `apps/api` · `apps/worker` · `packages/core` 셋이고 `apps/api`는 worker를 의존성으로 갖지 않는다. **그러나** Phase 1의 D-01(단일 Dockerfile · 단일 이미지)이 셋을 같은 venv에 설치하므로 **런타임 이미지 안에서는 `apps/api` 프로세스가 worker 모듈을 물리적으로 import 할 수 있다.** 패키지 분리로는 이걸 막지 못한다.

  따라서 집행의 무게중심을 정확히 여기에 둔다:
  1. **`ApiSettings`에 secret 필드가 존재하지 않는다** — api 프로세스는 키를 담을 그릇이 없다 (SEC-01)
  2. **Railway가 `SUPABASE_SECRET_KEY`를 worker 서비스에만 주입한다** — api 프로세스 환경에 값 자체가 없다 (Phase 1 D-12가 이미 세워둠)
  3. ruff banned-api + CI는 **이 둘을 보조하는 조기 경보**이지 1차 방어선이 아니다

  ⚠️ planner는 이 인과를 유지할 것. "import를 막았으니 안전하다"로 서술하면 단일 이미지 사실과 어긋난다. — **Reversibility:** costly — 뒤집으려면 Dockerfile 토폴로지(D-01)와 Railway 서비스 구성이 함께 움직인다.

- **D-07 (Settings 계층):** `packages/core`에 공통 조상 `BaseAppSettings`(pydantic-settings)를 두고 `SUPABASE_URL` · `SUPABASE_PUBLISHABLE_KEY` · `ENVIRONMENT` · `LOG_LEVEL`만 담는다. `ApiSettings`는 그대로 상속, `WorkerSettings`만 `SUPABASE_SECRET_KEY`(+ `OPENROUTER_API_KEY` · `OPENAI_API_KEY` · `DATABASE_URL`)를 **추가로** 선언한다. Phase 1이 이 클래스를 의도적으로 미룬 이유("SEC-01이 Phase 2라 지금 설계하면 두 번 바뀐다")가 여기서 해소된다. 현재 코드는 `os.environ`을 직접 읽고 있다 — `apps/api/src/api/main.py:24`, `apps/api/src/api/routers/health.py`가 교체 대상.

- **D-08 (`service_client()`는 전역 싱글턴이 아니라 팩토리):** `service_client(settings: WorkerSettings)`처럼 **`WorkerSettings`를 인자로 요구**한다. `ApiSettings`로는 타입이 맞지 않아 호출할 수 없고, 모듈 임포트만으로 클라이언트가 생기지도 않는다. 전역 싱글턴을 두면 import 부작용으로 키를 읽으려 시도하게 되어 D-06의 인과가 흐려진다.

- **D-09 (린트·CI):** ruff `lint.flake8-tidy-imports.banned-api`로 `worker.db.service` 경로를 차단하고 `per-file-ignores`로 `apps/worker/**`만 예외 처리한다. 현재 `[tool.ruff.lint]`의 `select`에 `TID`가 없으므로 **추가해야 한다**. CI(GitHub Actions)는 Phase 1에서 명시적으로 이 페이즈로 미뤄둔 항목이며, `pre-commit run --all-files` 재실행 + SEC-05의 클라이언트 번들 grep(`sb_secret_` · `SUPABASE_SECRET_KEY` 문자열)을 실행한다.

- **D-10 (부팅 시 실패):** 필수 env 누락은 **키 이름을 명시하며 즉시 실패**한다(기존 에러 처리 규약: "Config errors fail fast at boot"). worker가 `SUPABASE_SECRET_KEY` 없이 뜨는 상황을 조용히 넘기지 않는다.

### `UserDb` 403 매핑 (SEC-04/06)

- **D-11 (0행 = 403은 *쓰기 경로에만* 적용한다 — 이것이 구분 방법이다):** `UserDb`를 범용 쿼리 래퍼로 만들면 "정상적으로 비어 있는 조회"와 "RLS가 막은 0행"을 구분할 수 없다. 대신 **쓰기 전용 메서드**를 별도로 둔다 — `update_one()` · `delete_one()`이 affected rows를 받아 0이면 `WorkspaceForbidden`을 던진다. 읽기 메서드는 이 규칙을 적용하지 않으므로 빈 목록이 403이 되는 일이 구조적으로 불가능하다. — **Reversibility:** costly — 뒤집으면 모든 라우터의 예외 처리가 흩어지고, SEC-04가 요구하는 "한 곳" 조건이 깨진다.

- **D-12 (존재하지 않는 리소스와 격리 위반을 구분하지 *않는다*):** 둘 다 403. 404를 주면 다른 테넌트의 리소스 존재 여부가 응답 코드로 새어나가 열거 공격이 성립한다. 의도적 결정이며 planner가 "UX상 404가 낫다"로 뒤집지 말 것.

- **D-13 (42501은 별도 경로, 같은 응답):** `WITH CHECK` 위반은 SQLSTATE `42501` 예외로 올라온다. `WorkspaceForbidden`과 `42501` 둘을 **단일 예외 핸들러**가 403으로 렌더한다. 두 경로가 다른 곳에서 처리되면 SEC-04의 "한 곳" 조건이 다시 깨진다.

- **D-14 (SEC-06 테스트 형태):** 워크스페이스 2개 × 사용자 2명 픽스처로 CRUD 전 경로에 교차 접근을 시도하는 파라미터화된 pytest. 새 라우터가 늘 때 이 테이블에 행만 추가하면 되도록 설계한다. ⚠️ 루트 `pyproject.toml`의 `testpaths`에 **`apps/worker/tests`가 빠져 있다** — Phase 2가 worker 테스트를 추가하므로 이 페이즈에서 고쳐야 한다.

### 워커 하트비트 vs 잡 분할 (DOM-08/09)

- **D-15 (스카우트 결과 — STATE.md 블로커 해소):** `supabase/migrations/0003_jobs.sql:55-57` 확인 결과 **`jobs`에 하트비트 컬럼이 없다.** `locked_at`은 claim 시점에 한 번만 찍히고 갱신되지 않으며 `reap_stale_jobs`는 그 나이만 본다. 즉 현재 스키마에서 긴 잡은 "살아있음"을 알릴 수단이 없다.

- **D-16 (하트비트 컬럼을 추가하지 *않는다* — 잡 분할로 간다):** DOM-09가 "없으면 컴파일을 더 작은 잡으로 분할"이라는 조건부 지시를 이미 주었고, COMP-04가 `parse → compile → link_sync → embed` 분할을 독립적으로 요구한다. 근거 셋:
  1. 잡 분할이 각 단계를 짧게 만들어 reap 윈도우 초과 가능성 자체를 줄인다
  2. 하트비트를 도입하면 워커가 주기적 UPDATE를 돌려야 하는데, 이는 **"`jobs`를 직접 UPDATE하지 말라"**는 기존 규약과 충돌해 `heartbeat_job()` 함수를 새로 만들어야 한다 — 큐 계약 표면이 넓어진다
  3. 컬럼 추가는 되돌리기 싼 변경이다. Phase 3에서 LLM 실측 후 부족하면 그때 넣는다

  — **Reversibility:** reversible — 나중에 `0008`에서 `heartbeat_at` + `heartbeat_job()`을 추가하면 되고, 기존 잡 처리 경로를 깨지 않는다.

- **D-17 (reap 타임아웃은 Phase 2에서 *잠정치*, Phase 3에서 확정):** Phase 2가 실제로 측정할 수 있는 것은 `noop` 잡의 큐 오버헤드(claim→complete 왕복)뿐이며 LLM 잡의 p99는 알 수 없다. 그러므로 Phase 2는 **측정 장치를 심고 큐 오버헤드 기준선을 실측**하되, 최종 타임아웃은 첫 LLM 잡이 도는 Phase 3에서 재측정해 확정한다. ⚠️ ROADMAP 성공기준 5의 "추측이 아니라 실측 p99"는 Phase 2 범위 안에서는 **noop 기준 실측**으로 충족되며, planner는 이 한계를 문서에 명시할 것 — 숨기고 넘어가면 Phase 3가 근거 없는 숫자를 물려받는다.

- **D-18 (graceful shutdown과 attempts 반납 — `0007`에 `release_job()` 추가):** SIGTERM 수신 시 새 claim을 멈추고 진행 중인 잡의 완료를 기다리되, Railway grace period보다 짧은 상한을 둔다. 상한 초과 시 잡을 `queued`로 **반납**한다. 그런데 `attempts`는 claim 시점에 증가하므로(`0003_jobs.sql`) 그냥 반납하면 자발적 종료가 독약 잡 카운트를 소모한다. 따라서 `0007`에 **`release_job(p_job_id)`** 를 추가해 `attempts`를 되돌리며 락을 해제한다. `fail_job`을 재사용하면 재배포 세 번에 정상 잡이 `dead`로 떨어진다.

### Claude's Discretion

사용자가 "추천안대로 진행"으로 위임한 영역. 아래는 SPEC 제약과 기존 관례에 맞춰 내가 정한 값이며 **planner/researcher가 뒤집을 수 있다 — 다만 뒤집을 때 이유를 남길 것.**

- **D-19 (토크나이저 버전 문자열 형식, DOM-05):** `tsv_tokenizer_version` 값은 `bigram-nfkc-cf-v1` 형태로 **알고리즘 · 정규화 형식 · casefold 여부 · 버전**을 한 문자열에 인코딩한다. DOM-05가 "정규화 형식까지 인코딩"을 요구하는 이유가 재색인 범위를 좁히기 위함이므로, 정규화만 바뀌어도 값이 달라져야 한다. `normalize()`는 NFKC + casefold + 공백 정규화를, `bigram()`은 **정규화된 입력만** 받는다(정규화되지 않은 입력을 받으면 assert 실패 — 조용한 불일치가 이 프로젝트에서 가장 비싼 버그다).

- **D-20 (슬러그 생성 규칙, DOM-07):** `normalize()` 결과에서 한글을 **로마자화하지 않고 그대로 유지**하고, 공백→하이픈, 허용 문자 외 제거, 길이 상한 적용, 충돌 시 `-2` · `-3` 접미. 버전 태그 `slug_v1`. 로마자화를 배제한 이유는 한국어 표기 변환 규칙이 여러 표준으로 갈려 "결정적 순수 함수"라는 DOM-07 요구와 충돌하기 때문. **LLM은 `title`만 내고 슬러그를 소유하지 않는다.** 페이지 생성 전에 기존 슬러그와 `wiki_links.target_slug` 양쪽에 대해 해소한다.

- **D-21 (`0007` 구성 순서):** 마이그레이션 하나에 넣되 파일 내 번호 섹션으로 분리 — (1) 검색 함수(트랜스포트 결정에 종속), (2) `jobs_dedup_idx`, (3) `complete_job_and_chain()`, (4) `release_job()` [D-18], (5) `verified_by`/`verified_at`/`expires_at`, (6) `embedding_version`/`chunker_version`. ⚠️ (1)이 D-03 스파이크 결과에 종속되므로 **스파이크가 `0007` 작성보다 먼저 끝나야 한다** — planner는 이 의존을 태스크 순서에 반영할 것.

- **D-22 (`.env.sample` 정합성):** Phase 1이 미뤄둔 `LLM_MODEL` 기본값 불일치(`.env.sample`은 `anthropic/claude-3.5-sonnet`, PROJECT.md는 `claude-sonnet-4-6`)는 **Phase 2에서 건드리지 않는다** — LLM 호출이 없어 검증 수단이 없고, Phase 3(COMP-01)에서 실제 OpenRouter 슬러그를 확인하며 함께 정리하는 것이 맞다. 단 `WorkerSettings`가 이 키를 선언하게 되므로 planner는 기본값을 하드코딩하지 말고 env에서만 읽을 것.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

ROADMAP.md의 Phase 2 항목에는 `Canonical refs:` 줄이 없다. 아래는 스카우트와 논의에서 누적한 목록이다.

### 이 페이즈의 계약
- `.planning/ROADMAP.md` §Phase 2 (74-88행) — 5개 성공 기준. 성공기준 3이 스파이크 판정 기준(`create function ... SET hnsw.iterative_scan`이 RPC로 실제 적용되는지)을 명시
- `.planning/REQUIREMENTS.md` §Security (SEC-01~06) · §Data Access & Shared Domain (DOM-01~09) — 15개 요구사항 원문
- `.planning/REQUIREMENTS.md` §Retrieval RTV-03 — **GUC 3종 전부** 요구. D-03 tie-break의 근거
- `.planning/REQUIREMENTS.md` §Compile COMP-04 — 잡 분할 요구. D-16의 근거
- `.planning/PROJECT.md` §Constraints, §Key Decisions — 하이브리드 DB 접근, `service_role` = BYPASSRLS, 리전 불변성

### 선행 페이즈에서 물려받은 결정
- `.planning/phases/01-bootstrap-and-ground-truth/01-CONTEXT.md` > **D-01** — 단일 Dockerfile · 단일 이미지. **D-06의 "import로는 막지 못한다"는 인과의 출처**
- `.planning/phases/01-bootstrap-and-ground-truth/01-CONTEXT.md` > **D-11** — `health_check.py`가 트랜스포트 교체 지점 한 곳으로 격리됨. Phase 2가 트랜스포트를 정하면 여기만 바뀐다
- `.planning/phases/01-bootstrap-and-ground-truth/01-CONTEXT.md` > **D-12** — Railway 서비스별 env 스코프. SEC-01의 물리적 집행 지점
- `.planning/phases/01-bootstrap-and-ground-truth/01-SPEC.md` §Out of scope — Settings 공통 조상 클래스를 Phase 2로 미룬 근거

### 기존 스키마 (재구현 금지 — 이미 적용·검증 완료)
- `supabase/migrations/0003_jobs.sql:44-70` — `jobs` 컬럼 정의. **하트비트 컬럼 부재 · `jobs_lock_consistency` CHECK**를 여기서 확인
- `supabase/migrations/0003_jobs.sql:103-212` — `claim_job`/`complete_job`/`fail_job`/`reap_stale_jobs` 계약. `attempts`가 **claim 시점에** 증가 (D-18의 근거)
- `supabase/migrations/0004_rls_policies.sql:44-95` — `is_workspace_member` · `workspace_role` · `has_workspace_role`. 셋 다 `security definer stable set search_path = public`
- `supabase/migrations/0002_search_schema.sql:30` — pgvector가 `extensions` 스키마에 설치됨. 모든 참조가 schema-qualified — 스파이크 SQL도 이 규약을 따를 것
- `supabase/migrations/0005_storage.sql` — Phase 1에서 추가됨

### 현재 코드 (교체·확장 대상)
- `apps/api/src/api/main.py:24` — `os.environ` 직접 읽기. `ApiSettings`로 교체 대상 (D-07)
- `apps/api/src/api/health_check.py` — D-11의 트랜스포트 교체 지점. 스파이크 결과가 여기에 착지
- `packages/core/src/nexuswiki_core/logging.py` — 공용 structlog. 토크나이저/슬러그 모듈이 들어갈 같은 패키지
- `pyproject.toml` — `[tool.ruff.lint] select`에 **`TID` 없음** (D-09가 추가), `testpaths`에 **`apps/worker/tests` 없음** (D-14가 추가)

### 코드베이스 맵 (2026-08-01 기준)
- `.planning/codebase/CONCERNS.md` — 알려진 우려. 보안 페이즈의 1차 참조
- `.planning/codebase/INTEGRATIONS.md` — DB 접근 모델(`user_client`/`service_client`) · 잡 큐 계약
- `.planning/codebase/CONVENTIONS.md` — SQL 소문자 키워드 · 한국어 주석 · 파일 헤더에 태스크 ID + `checklists.json` 결정 키 인용
- `.planning/codebase/ARCHITECTURE.md` — 레이어 구조 · RLS 위반이 0행으로 돌아온다는 사실

### 산출물 경로
- `docs/ops/db-transport-spike.md` — D-05가 지정한 스파이크 결과 문서 (Phase 1의 `docs/ops/rtt-baseline.md`와 대칭)
- `checklists.json > decisions.db_transport` — 트랜스포트 결정의 잠금 위치 (D-05)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`packages/core/src/nexuswiki_core/logging.py`**: 이미 워크스페이스 공용 패키지가 서고 `apps/api`가 `nexuswiki-core = { workspace = true }`로 소비 중. 토크나이저(DOM-05)·슬러그(DOM-07)·`BaseAppSettings`(D-07)가 들어갈 자리가 이미 배선되어 있다
- **`apps/api/src/api/health_check.py`**: `ReadinessResult` 데이터클래스 + 명시적 타임아웃 패턴이 확립됨. 트랜스포트 어댑터가 같은 형태를 따를 수 있다
- **`0004`의 RLS 헬퍼 3종**: `security definer` + `authenticated` grant 상태 — `0007`의 검색 함수가 그대로 호출 가능하다. 새 멤버십 로직 불필요
- **`0003`의 큐 함수 4종**: `release_job()`(D-18)만 추가하면 되고 나머지는 그대로 소비

### Established Patterns
- **`⚠️` 접두사 = "무시하면 데이터/보안이 조용히 깨지는 지점"**. Phase 2는 이 마커가 가장 많이 붙을 페이즈다 — D-04(GUC 누락 시 조용한 격리 해제), D-19(정규화 불일치)가 대표
- **"정책이 없어서 못 한다"가 이 프로젝트의 관용구** — `raw_sources`·storage UPDATE 정책 부재. D-06의 "필드가 없어서 못 한다"가 같은 논리의 애플리케이션 계층 판본
- **파일 헤더에 태스크 ID + 결정 키 인용, 근거는 재서술하지 않음.** 프로젝트 수명 결정은 `checklists.json > decisions.<key>`, 페이즈 한정 결정은 `02-CONTEXT.md > D-XX`
- **마이그레이션 번호 = 적용 순서**, `NNNN_snake_case_topic.sql`. `0007`이 다음 번호
- **모든 주석·커밋 메시지·문서는 한국어**, 식별자·키워드·파일명은 영문

### Integration Points
- **`pyproject.toml` `[tool.ruff.lint]`** — `TID` 미선택 (D-09), `testpaths`에 worker 누락 (D-14). 둘 다 이 페이즈에서 고침
- **`apps/api/src/api/main.py` lifespan** — Settings 주입 지점. `create_app()`이 `ApiSettings`를 받도록 바뀐다
- **단일 Dockerfile (Phase 1 D-01)** — D-06의 제약 출처. api/worker가 같은 venv를 공유한다는 사실이 격리 설계를 규정한다
- **Railway 서비스별 env 스코프 (Phase 1 D-12)** — SEC-01의 실제 집행 지점. 코드가 아니라 인프라 설정
- **GitHub Actions (아직 없음)** — Phase 1이 명시적으로 이 페이즈로 미룸. SEC-03·SEC-05가 여기서 처음 CI를 세운다

</code_context>

<specifics>
## Specific Ideas

- **스파이크의 진짜 위험은 "판정 실패"가 아니라 "변별력 없는 통과"다** — 사용자가 합성 적대적 분포(D-02)를 고른 이유가 이것. 코퍼스가 작으면 RPC와 asyncpg가 똑같이 통과해 스파이크가 아무것도 결정하지 못한 채 "검증했다"는 착각만 남는다. planner는 타깃 워크스페이스 비율(1~2%)을 수용기준에 박을 것
- **EXPLAIN을 판정에 쓰기로 한 것은 Phase 4에 대한 선투자다** — RTV-08이 요구하는 EXPLAIN 회귀 테스트와 같은 장치다. 스파이크용 일회성 스크립트로 쓰고 버리지 말 것
- **"역량 부재"의 위치를 틀리면 안 된다** — 단일 이미지라 import는 막히지 않는다. 막히는 것은 **키**다. 이 문장이 Phase 2 보안 서술의 중심축이며, planner가 "패키지를 분리해 import를 차단한다"로 쓰면 사실과 어긋난다
- **0행 = 403을 쓰기 경로에만 적용하는 것이 SEC-04의 유일한 온전한 해법** — 범용 래퍼로는 정상 빈 조회와 RLS 차단을 원리적으로 구분할 수 없다
- **403 vs 404는 UX가 아니라 정보 누출 문제** — D-12를 편의로 뒤집으면 테넌트 간 리소스 존재 여부가 새어나간다

</specifics>

<deferred>
## Deferred Ideas

- **`jobs` 하트비트 컬럼 (`heartbeat_at` + `heartbeat_job()`)** — D-16에서 이번엔 넣지 않기로 함. Phase 3에서 LLM 잡 p99를 실측한 뒤 잡 분할만으로 부족하면 `0008`로 추가. 되돌리기 싼 변경이라 미루는 비용이 낮다
- **`reap_stale_jobs` 최종 타임아웃 확정** — D-17. Phase 2는 noop 기준 큐 오버헤드만 실측 가능. 첫 LLM 잡이 도는 Phase 3에서 재측정해 확정
- **`LLM_MODEL` 기본값 불일치 정리** — D-22. Phase 3(COMP-01)에서 실제 OpenRouter 슬러그 검증과 함께
- **`relaxed_order` vs `strict_order` 벤치마크 (RTV-04)** — Phase 2 스파이크는 `strict_order`가 *적용되는지*만 판정한다. 실제 코퍼스로 둘을 비교해 선택 근거를 남기는 것은 Phase 4의 일
- **골든 질의 세트 (RTV-06)** — Phase 4. Phase 2의 합성 코퍼스는 트랜스포트 판정용이지 검색 품질 판정용이 아니다. 둘을 섞지 말 것
- **`checklists.json` / `CLAUDE.md`의 `apps/fastapi-backend` 경로 표기** — Phase 1 D-09에서 갱신 대상으로 지목됨. Phase 1에서 처리되지 않았다면 Phase 2가 이어받아 정리 (planner가 현재 상태를 확인할 것)

</deferred>

---

*Phase: 2-Security Spine and Shared Domain*
*Context gathered: 2026-08-05*
