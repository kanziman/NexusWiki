# Phase 1: Bootstrap and Ground Truth - Context

**Gathered:** 2026-08-02
**Status:** Ready for planning

<domain>
## Phase Boundary

저장소를 "SQL 마이그레이션 + 기획 문서"에서 "두 Python 서비스가 클라우드에서 도는 monorepo"로 바꾸는 인프라 부트스트랩. 되돌릴 수 없거나 매주 비싸지는 결정(리전 · 키 체계 · `0005` 순서 · monorepo 형태 · 배포 토폴로지)을 확정하고, `api`(web)와 `worker`(resident)를 동일 이미지로 Railway `asia-southeast1`에 띄우며, `0001`~`0006`을 Supabase Cloud `ap-southeast-1`에 순서대로 적용한다.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**10 requirements are locked.** See `01-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `01-SPEC.md` before planning or implementing. Requirements are not duplicated here. SPEC.md also carries **10개 엣지 커버리지 행**과 **4개 금지사항(must-NOT)** — 후자는 부정 수용기준이므로 계획에 반드시 반영한다.

**In scope (from SPEC.md):**
- `supabase/migrations/0005_storage.sql` (버킷 + `storage.objects` 정책)
- Supabase Cloud 프로젝트 리전·키 체계 검증, `0001`~`0006` 클라우드 적용
- Supabase CLI 업그레이드 + `config.toml` 호환 수정
- uv 워크스페이스 monorepo (`packages/core` · `apps/api` · `apps/worker`) + 커밋된 `uv.lock`
- `packages/core`의 공용 structlog 로깅 모듈 (이 페이즈에서 core가 담는 유일한 실질 내용)
- pre-commit(ruff + prettier) · `.editorconfig` · 루트 `README.md`
- FastAPI `lifespan` + `/health` + `/health/ready`
- Next.js 15.5.22+ 스캐폴딩 (Tailwind 4 · TS strict · Vitest 2 테스트)
- Railway 가입 · Hobby 구독 · 프로젝트 1개 + 서비스 2개 배포 (`asia-southeast1`)
- RTT 실측 문서
- Supabase Auth 하드닝 (12자 · 이메일 확인)

**Out of scope (from SPEC.md):**
- JWT 인증 · 워크스페이스 컨텍스트 · `user_client`/`service_client` 분리 · `UserDb` 403 매핑 — Phase 2 (SEC-01~06)
- `/health`·`/health/ready` 외의 모든 라우터 — Phase 3~5
- 실제 잡 처리 로직 · `claim_job` 폴링 루프 — Phase 2 (DOM-08)
- 마이그레이션 `0007` — Phase 2 (DOM-02~04)
- 한국어 토크나이저(`normalize()`/`bigram()`) — Phase 2 (DOM-05)
- Next.js 배포(Vercel) — Phase 6
- 설정(Settings) 공통 조상 클래스 — SEC-01이 Phase 2라 지금 설계하면 두 번 바뀐다
- RSC 테스트 전략 — Phase 6

</spec_lock>

<decisions>
## Implementation Decisions

### Dockerfile 구조와 서비스 분기

- **D-01:** 단일 Dockerfile · Root Directory `/`. `CMD` 기본값은 `api`이고 **worker 서비스에만 Railway Custom Start Command**를 지정한다. 이미지가 문자 그대로 하나라 SPEC R8의 1차 판정(두 서비스 다이제스트 일치)이 자연히 통과한다. 멀티스테이지 타깃 2개(`--target api`/`--target worker`)는 **구조적으로 다이제스트가 달라져 1차 판정을 불가능하게 만들므로 배제**했다. — **Reversibility:** costly — 바꾸면 Dockerfile · Railway 두 서비스 설정 · SPEC R8 수용기준이 함께 움직인다.

- **D-02:** 멀티스테이지 빌드. builder 스테이지에서 `uv sync --frozen --no-dev`로 `/app/.venv`를 만들고, 런타임 스테이지에는 **venv만 COPY**한다. 런타임 이미지에 uv 바이너리가 없어 이미지가 작고, SPEC R4의 `uv sync --frozen` 클린클론 검증과 **동일한 lockfile 경로**를 탄다.

- **D-03:** exec form `CMD`를 유지하고 **uvicorn을 파이썬 엔트리포인트에서 프로그래밍 방식으로 기동**하며 `os.environ["PORT"]`를 읽는다. 이유는 두 가지가 겹친다 — exec form은 `$PORT`를 확장하지 못하고, shell form이나 `entrypoint.sh`를 쓰면 shell이 PID 1이 되어 **SIGTERM이 자식 프로세스에 전달되지 않는다**. worker의 graceful shutdown이 정확히 여기에 걸린다. 이 결정으로 PID 1이 파이썬이 되어 SIGTERM이 직접 도달한다. — **Reversibility:** costly — `sh -c` + `exec`도 정답이지만 `exec` 키워드를 빠뜨리면 조용히 깨지고, 증상이 "Railway 재배포 시 잡 유실"로만 나타나 진단이 어렵다.

- **D-04:** Python 3.12로 고정. `requires-python = ">=3.12"`, `.python-version` 커밋, 이미지는 `python:3.12-slim`. 호스트가 3.11.5지만 uv가 로컬에 3.12를 자동 설치하므로 호스트/이미지 드리프트가 사라진다. 3.13은 후속 페이즈 의존성(`pypdf`·asyncpg 등) 휠 호환성이 덜 검증되어 배제.

### `0005` Storage 정책

- **D-05:** 전용 헬퍼 `public.storage_path_workspace(text) returns uuid`를 `0005`에 만든다. 정규식으로 `UUID/UUID/파일명` 3세그먼트 형태를 검사하고 불일치 시 `null`을 반환한다. `(storage.foldername(name))[1]::uuid` 직접 캐스팅은 첫 세그먼트가 UUID가 아닐 때 **22P02 예외를 던져 "거부"가 아니라 "에러"가 되므로** 배제했다. 정책 4개가 짧아지고 검사 로직이 한 곳에 모인다. — **Reversibility:** one-way — 정책 술어가 이 함수에 의존하므로 시그니처 변경에는 새 마이그레이션이 필요하고, 그때는 이미 클라우드에 적용된 뒤다.

- **D-06:** 역할 등급을 `0004_rls_policies.sql`의 베이스라인과 대칭시킨다 — SELECT = `is_workspace_member(ws)`, INSERT = `has_workspace_role(ws,'editor')`, DELETE = `has_workspace_role(ws,'owner')`. 세 헬퍼는 이미 `security definer stable set search_path = public`이고 `authenticated`에 `grant execute`되어 있어 storage 정책에서 그대로 호출 가능하다.

- **D-07:** **UPDATE 정책을 만들지 않는다.** `raw_sources`가 UPDATE 정책 부재로 불변인 것과 대칭이다. 원본 파일 덮어쓰기가 불가능해져 "불변 원본 보존" 약속이 관례가 아니라 **정책 부재로 강제**된다. — **Reversibility:** one-way — 나중에 UPDATE를 허용하면 `content_hash` 멱등성(OPS-03)과 원본 추적성이 함께 깨지고, 이미 업로드된 파일의 이력은 복구되지 않는다.

- **D-08:** 버킷은 `insert into storage.buckets (...) on conflict (id) do nothing`으로 멱등 생성. `public = false`, `file_size_limit` 50MiB. **MIME allowlist는 버킷에 두지 않고** Phase 3 애플리케이션 계층에서 검증한다 — 버킷 레벨 `allowed_mime_types`는 타입을 하나 늘릴 때마다 새 마이그레이션이 필요해 Phase 3 수집 확장을 막는다.

### Claude's Discretion

사용자가 논의하지 않기로 한 영역들. 아래는 내가 SPEC 제약과 기존 관례에 맞춰 정한 값이며, **planner/researcher가 뒤집을 수 있다** — 다만 뒤집을 때 이유를 남길 것.

- **D-09 (monorepo 레이아웃):** uv 워크스페이스 멤버는 `packages/core` · `apps/api` · `apps/worker` 셋(SPEC 확정). Python 패키지는 **`src/` 레이아웃**을 쓴다(임포트 섀도잉 방지, uv 권장). Next.js 앱은 **`apps/dashboard`** — SPEC이 JS 앱 이름을 잠그지 않았고 `CLAUDE.md`·`checklists.json`이 이미 이 이름을 쓰므로 기존 문서와 일치시킨다. `apps/dashboard`는 **uv 워크스페이스 멤버가 아니다**.
  - ⚠ 문서 간 이름 충돌 주의: `CLAUDE.md`와 `checklists.json`은 Python 쪽을 `apps/fastapi-backend`로 부른다. **SPEC/ROADMAP/REQUIREMENTS의 `apps/api` + `apps/worker`가 이깁니다.** 이 페이즈에서 `CLAUDE.md`와 `checklists.json`의 경로 표기를 갱신할 것.

- **D-10 (pnpm workspace 미도입):** JS 패키지가 `apps/dashboard` 하나뿐이므로 workspace를 만들지 않고 단독 `package.json`으로 간다. REQUIREMENTS가 Turborepo/Nx를 "JS 패키지가 하나뿐"이라는 이유로 배제한 것과 같은 논리다.

- **D-11 (`/health/ready`의 DB 접근 경로) — 검증 필요:** Phase 1은 **DB 트랜스포트를 결정하지 않는다**(DOM-01은 Phase 2 스파이크). readiness 체크는 asyncpg도 `supabase-py`도 커밋하지 않고, `httpx`로 Supabase REST(PostgREST)에 얇은 요청 하나를 보내 실제 Postgres 왕복을 만든다. 명시적 2초 타임아웃, 초과 시 503. 체크 함수는 얇은 어댑터 뒤에 두어 Phase 2가 트랜스포트를 정한 뒤 교체 지점이 한 곳이 되게 한다.
  - **researcher가 확인할 것:** PostgREST 요청이 SPEC R6의 "DB 왕복"을 만족하는지, 그리고 인증 없이(publishable key만으로) 안정적인 헬스 신호가 되는지. 아니라면 대안을 제시하되 **Phase 2 트랜스포트 결정을 선점하지 말 것**.

- **D-12 (Railway 설정과 환경변수 스코프):** `railway.json`을 저장소에 커밋해 빌드/배포 설정을 코드화하되 **시크릿은 절대 넣지 않는다**(UI/CLI로만 주입). 환경변수는 **공유 스코프를 쓰지 않고 서비스별 스코프**로 설정한다 — SPEC 금지사항 P1(`api`가 `SUPABASE_SECRET_KEY`에 닿지 않음)이 강제되는 지점이 정확히 여기다. `GIT_SHA`는 Railway 내장 `RAILWAY_GIT_COMMIT_SHA`를 앱이 읽어 로그/응답에 노출한다(SPEC R8 2차 판정용). 배포는 GitHub 연동 자동 배포.

- **D-13 (structlog 프로세서 체인):** `structlog.contextvars.merge_contextvars`를 체인 앞에 두고 `bind_contextvars(job_id=…, workspace_id=…)`로 바인딩한다. 렌더러는 `ENVIRONMENT` env로 분기 — 로컬 `ConsoleRenderer`, 프로덕션 `JSONRenderer`. 금지사항 P2의 마스킹은 **키 기반 denylist 프로세서**(`password`, `authorization`, `token`, `api_key`, `secret`, `email`, `access_token`, `content` 등)로 구현한다. allowlist가 더 안전하지만 구조화 로그의 이벤트 필드가 자유롭게 늘어나는 성격과 맞지 않는다 — 대신 denylist 키 목록 자체를 단위 테스트로 고정해 회귀를 막는다.

- **D-14 (RTT 측정 실행 경로):** SPEC R9는 "배포된 api에서 측정"을 요구하는데 SPEC 경계는 새 라우터를 금지한다. 그래서 **Phase 1의 `worker` 엔트리포인트가 기동 시 RTT 측정을 1회 수행하고 결과를 구조화 로그로 출력**한다 — worker는 이 페이즈에서 잡 루프가 없으므로(경계상 제외) 기동·로깅·graceful shutdown만 하며, 여기에 측정 1회를 붙이면 라우터 없이 배포 환경에서 측정된다. 워밍업 후 N≥50회, p50/p95 + 콜드 첫 요청. 결과 문서는 **`docs/ops/rtt-baseline.md`** — 금지사항 P4의 grep 대상이 이 경로다.
  - `railway run`은 **로컬에서** Railway 환경변수만 주입해 실행하므로 "배포된 api에서 측정"을 만족하지 못한다. 이 함정을 피하려고 위 방식을 택했다.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

ROADMAP.md의 Phase 1 항목에는 `Canonical refs:` 줄이 없다. 아래는 스카우트와 논의에서 누적한 목록이다.

### 이 페이즈의 계약
- `.planning/phases/01-bootstrap-and-ground-truth/01-SPEC.md` — **Locked requirements — MUST read before planning.** 10개 요구사항 · 경계 · 24개 수용기준 · 엣지 커버리지 10행 · 금지사항 4건(부정 수용기준)
- `.planning/ROADMAP.md` §Phase 1 — 5개 성공 기준
- `.planning/REQUIREMENTS.md` §Bootstrap (BOOT-01~10) + §Out of Scope — Gunicorn·Fly.io·Render·서울 리전·Turborepo/Nx 배제 근거
- `.planning/PROJECT.md` §Constraints, §Key Decisions — 리전 불변성, 하이브리드 DB 접근, OpenRouter 경유

### 기존 스키마 (재구현 금지 — 이미 적용·검증 완료)
- `supabase/migrations/0001_core_schema.sql:107-110` — `storage_path` 경로 규약 `{workspace_id}/{raw_source_id}/{filename}`이 **주석으로만** 존재. `0005`가 이걸 강제로 바꾼다
- `supabase/migrations/0004_rls_policies.sql:44-95` — `is_workspace_member(uuid)` · `workspace_role(uuid)` · `has_workspace_role(uuid, text)`. 셋 다 `security definer stable set search_path = public` + `grant execute … to authenticated` → **storage 정책에서 그대로 호출 가능**
- `supabase/migrations/0003_jobs.sql` — `claim_job`/`complete_job`/`fail_job`/`reap_stale_jobs` 계약. Phase 1은 호출하지 않지만 worker 스켈레톤이 이 계약을 깨지 않아야 함
- `supabase/config.toml` — 로컬 포트 544xx(`zettlink`가 543xx 점유), Postgres major 17, `[storage] file_size_limit = "50MiB"`, `[auth]` 현재 최소 비밀번호 6자 · 이메일 확인 off (SPEC R10이 바꿀 대상)

### 코드베이스 맵 (2026-08-01 기준)
- `.planning/codebase/STACK.md` — 현재 스택과 [PLANNED] 항목, 로컬 포트 표, Known Stack Risks(`0005` 시퀀스 구멍)
- `.planning/codebase/INTEGRATIONS.md` — Supabase Auth 현재 설정값, DB 접근 모델(`user_client`/`service_client`), 잡 큐 계약, 프롬프트 템플릿 계약
- `.planning/codebase/ARCHITECTURE.md` — 레이어 구조 (Phase 2 이후 참조)
- `.planning/codebase/CONVENTIONS.md` — 네이밍·주석·커밋 규약. **SQL은 소문자 키워드, 주석은 한국어, 파일 헤더에 태스크 ID + `checklists.json` 결정 키 인용**
- `.planning/codebase/CONCERNS.md` — 알려진 우려. 보안 관련 페이즈에서 참조

### 환경·핸드오프
- `.env.sample` — 필요한 env 키 전체 목록. **단, `LLM_MODEL` 기본값이 `anthropic/claude-3.5-sonnet`으로 PROJECT.md(`claude-sonnet-4-6`)와 불일치.** Phase 1에서 정합성을 맞추거나 Phase 3으로 미룰지 판단할 것
- `HANDOFF.md` — 세션 핸드오프 §3~3e(마이그레이션 검증 결과), §5(벡터 검색 쿼리 요구사항)
- `checklists.json` — 32개 태스크 · 10개 확정 결정 · **open question #2(RTT)가 SPEC R9로 해소 대상**. `P0-INIT-00`~`P0-INIT-04`가 이 페이즈에 대응

### 디자인 (Next.js 스캐폴딩용)
- `docs/design-systems/design-tokens.css` · `design-tokens.json` — 이미 존재하는 디자인 토큰. Tailwind 4 설정이 이걸 소비하도록 연결할 수 있음(Phase 6 UI 작업의 선행 자산)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`is_workspace_member` / `has_workspace_role` (0004)**: `security definer` + `authenticated` grant 상태라 `0005`의 `storage.objects` 정책에서 재사용 가능. 새 멤버십 로직을 쓸 필요가 없다
- **`design-tokens.css` / `design-tokens.json` (`docs/design-systems/`)**: Next.js 스캐폴딩의 Tailwind 4 테마로 바로 연결 가능
- **`.env.sample`**: env 키 목록이 이미 정리되어 있음. `apps/api`/`apps/worker` 설정 모듈의 출발점
- **`.gitignore`**: `.env`, `.env.*`(단 `!.env.example`), `supabase/.env`, `.ruff_cache/`, `.mypy_cache/`, `node_modules/`, `.next/`를 이미 커버. Python/Node 툴링 추가 시 대부분 그대로 유효

### Established Patterns
- **SQL 스타일**: 소문자 키워드, 2-space 들여쓰기, `-- ---` 구분선, 파일 헤더에 태스크 ID + `checklists.json` 결정 키. `⚠️` 접두사는 "무시하면 데이터/보안이 조용히 깨지는" 지점. `0005`는 이 형식을 그대로 따라야 한다
- **마이그레이션 번호 = 적용 순서**: `NNNN_snake_case_topic.sql`. `0005`가 시퀀스 구멍이며 **클라우드 첫 `db push` 이전에** 들어가야 한다
- **커밋 규약**: `type(scope): <주제> — <구체적 변경>`. 한 태스크 = 한 커밋. 주제는 수량화(`9개 테이블 전체`)
- **모든 주석·커밋 메시지·문서는 한국어**, 식별자·키워드·파일명은 영문

### Integration Points
- **`supabase/migrations/0005_storage.sql`** — 새 파일. `0004`의 헬퍼를 소비하고 `0006`보다 먼저 적용됨
- **`supabase/config.toml` `[auth]` 섹션** — SPEC R10(12자 + 이메일 확인)이 여기와 클라우드 대시보드 양쪽에 반영되어야 함. 로컬만 바꾸면 프로덕션이 기본값으로 남는다
- **Railway 서비스 2개** — 금지사항 P1의 집행 지점. 환경변수 스코프가 여기서 결정된다
- **`CLAUDE.md` · `checklists.json`** — `apps/fastapi-backend` 경로 표기가 SPEC의 `apps/api`+`apps/worker`와 불일치. 이 페이즈에서 갱신 대상

</code_context>

<specifics>
## Specific Ideas

- **"start command만 다르게"가 R8 판정을 좌우한다** — 사용자가 멀티스테이지 타깃을 배제한 이유는 취향이 아니라 SPEC R8 1차 판정(다이제스트 일치)이 구조적으로 불가능해지기 때문. planner는 이 인과를 유지할 것
- **`entrypoint.sh`를 쓰지 않는 이유는 SIGTERM** — 편의상 나중에 도입하고 싶어질 수 있으나, shell이 PID 1이 되는 순간 worker graceful shutdown이 조용히 깨진다. 도입하려면 `exec`를 반드시 쓸 것
- **22P02 예외 회피가 헬퍼 함수 도입의 진짜 이유** — 정책에서 캐스팅이 예외를 던지면 "조용한 거부"가 아니라 "500 에러"가 된다. 헬퍼가 `null`을 반환하는 설계를 유지할 것
- **UPDATE 정책 부재 = 불변성 강제** — `raw_sources`가 이미 같은 패턴을 쓴다. "정책이 없어서 못 한다"가 이 프로젝트의 관용구다

</specifics>

<deferred>
## Deferred Ideas

- **GitHub Actions CI** — SPEC 범위에 없고 pre-commit만 요구됨. SEC-03(CI가 worker 밖 `service_client` 사용을 탐지해 빌드 실패)이 Phase 2 요구사항이므로 CI 파이프라인은 그때 세우는 것이 자연스럽다. Phase 1에서 만들면 Phase 2가 다시 손대게 된다
- **`.dockerignore` 세부 범위 · 레이어 캐싱 순서 · 비루트 유저** — 사용자가 "관례대로"로 위임. planner 재량이되, `apps/dashboard`·`node_modules`·`.planning`·`docs`는 Python 이미지 빌드 컨텍스트에서 제외해 프론트 커밋이 백엔드 이미지를 재빌드시키지 않게 할 것
- **`LLM_MODEL` 기본값 불일치** — `.env.sample`은 `anthropic/claude-3.5-sonnet`, PROJECT.md는 `claude-sonnet-4-6`. OpenRouter 실제 슬러그도 미검증(`checklists.json` open question). LLM 호출이 없는 Phase 1에서는 실해가 없으나 Phase 3(COMP-01) 이전에 반드시 정리
- **`jobs` 하트비트 컬럼 유무 확인** — STATE.md의 Phase 2 블로커. worker 루프 작성 전에 확인해야 하며 Phase 1의 worker 스켈레톤은 루프가 없으므로 지금은 무관

</deferred>

---

*Phase: 1-Bootstrap and Ground Truth*
*Context gathered: 2026-08-02*
