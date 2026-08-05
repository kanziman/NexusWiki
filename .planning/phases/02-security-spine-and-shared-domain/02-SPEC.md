# Phase 2: Security Spine and Shared Domain — Specification

**Created:** 2026-08-06
**Ambiguity score:** 0.13 (gate: ≤ 0.20)
**Requirements:** 12 locked

## Goal

테넌트 격리가 코드 규약이 아니라 **역량 부재**(api 프로세스에 secret 키를 담을 필드가 없음)로 강제되고,
첫 도메인 라우터가 서기 전에 DB 트랜스포트·공용 토크나이저·결정적 슬러그·워커 큐 계약 네 가지가
반증 가능한 근거와 함께 확정된다.

## Background

Phase 1이 끝난 시점의 실측 상태:

- `packages/core`에는 `logging.py` 하나뿐이다. settings·tokenizer·slug·db 모듈이 전부 없다.
- `apps/api/src/api/main.py:24`가 `os.environ`을 직접 읽는다. `ApiSettings`/`WorkerSettings` 클래스가 없어
  "api는 secret 키를 담을 그릇이 없다"는 SEC-01의 주장이 아직 코드로 존재하지 않는다.
- `apps/api`에 도메인 라우터가 **0개**다. `health` 라우터만 있다. `UserDb`도 예외 핸들러도 없다.
- `apps/worker`에는 `__main__.py`(SIGTERM 대기)와 `rtt.py`뿐이다. `claim_job`을 소비하는 코드가 없다.
- `supabase/migrations/`는 `0001`~`0006`까지다. `0007`이 없다.
- `.github/` 디렉터리 자체가 없다 — CI가 하나도 없다. SEC-03/SEC-05를 집행할 수단이 부재한다.
- 루트 `pyproject.toml`의 `[tool.ruff.lint] select`에 `TID`가 없고, `testpaths`에 `apps/worker/tests`가 빠져 있다.
  후자는 worker 테스트를 작성해도 **조용히 수집되지 않는다**는 뜻이다.
- `docs/ops/`에는 `rtt-baseline.md` 등 4건이 있고 `db-transport-spike.md`는 없다. DB 트랜스포트는 미결이며
  `apps/api/src/api/health_check.py`가 PostgREST httpx 왕복 하나로 임시 대응 중이다(01-CONTEXT.md > D-11).
- `supabase/migrations/0003_jobs.sql:55-57` 확인 결과 `jobs`에 하트비트 컬럼이 없다. `locked_at`은 claim 시점에
  한 번만 찍히고 갱신되지 않는다.

즉 Phase 2는 "보안 기능을 추가"하는 페이즈가 아니라, 이후 모든 페이즈가 딛고 설 **바닥을 만들고 그것이
실제로 딛히는지 증명**하는 페이즈다.

## Requirements

1. **Settings 계층 분리 (SEC-01)**: api 프로세스가 secret 키를 담을 필드를 갖지 않는다.
   - Current: Settings 클래스가 존재하지 않는다. `apps/api/src/api/main.py:24`와 `apps/worker/src/worker/__main__.py`가 각각 `os.environ`을 직접 읽는다
   - Target: `packages/core`에 `BaseAppSettings`(pydantic-settings, `SUPABASE_URL`·`SUPABASE_PUBLISHABLE_KEY`·`ENVIRONMENT`·`LOG_LEVEL`)를 두고, `ApiSettings`는 그대로 상속하며, `WorkerSettings`만 `SUPABASE_SECRET_KEY`·`DATABASE_URL`·`OPENROUTER_API_KEY`·`OPENAI_API_KEY`·`LLM_MODEL`을 추가 선언한다. `create_app()`이 `ApiSettings`를 주입받는다
   - Acceptance: `ApiSettings.model_fields`에 위 4개 secret/DB 키가 하나도 없음을 단언하는 테스트가 통과한다. 필수 키가 누락되거나 **빈 문자열**일 때 해당 키 이름을 포함한 메시지로 기동이 실패한다

2. **service_client 팩토리 격리 (SEC-02)**: service key 클라이언트를 import만으로 만들 수 없다.
   - Current: db 모듈이 없다. `pyproject.toml`의 ruff `select`에 `TID`가 없어 banned-api 규칙이 동작할 수 없다
   - Target: `apps/worker/src/worker/db/service.py`의 `service_client(settings: WorkerSettings)`가 `WorkerSettings` 인스턴스를 **인자로 요구**하는 팩토리이며 모듈 전역 싱글턴을 두지 않는다. 사용자 경로용 `db/user.py`는 별도 모듈이다. ruff `flake8-tidy-imports.banned-api`가 `worker.db.service`를 차단하고 `per-file-ignores`로 `apps/worker/**`만 예외 처리한다
   - Acceptance: `apps/api/**`에 `from worker.db.service import service_client`를 넣은 상태에서 `ruff check`가 non-zero로 종료한다. `service_client()`를 `ApiSettings` 인스턴스로 호출하면 거부된다

3. **CI 보안 게이트 (SEC-03, SEC-05)**: worker 밖의 service key 사용과 클라이언트 번들 유출을 CI가 빌드 실패로 막는다.
   - Current: `.github/` 디렉터리가 없다. 어떤 검사도 PR에서 강제되지 않는다
   - Target: PR 트리거 GitHub Actions 워크플로우 하나가 (a) `pre-commit run --all-files` (b) `apps/worker/**` 밖의 `db.service`/`service_client` 사용 탐지 (c) dashboard 프로덕션 빌드 산출물에 대한 `sb_secret_`·`SUPABASE_SECRET_KEY` 문자열 grep (d) `pytest` 네 가지를 실행한다
   - Acceptance: 네 검사 중 하나라도 실패하면 워크플로우가 실패한다. 의도적 위반 브랜치 2종(worker 밖 service import / 번들에 secret 노출)에서 각각 해당 잡이 red가 됨이 관측된다. grep 대상 빌드 산출물이 존재하지 않으면 pass가 아니라 **fail**로 처리된다

4. **UserDb 403 매핑 단일 지점 (SEC-04)**: 0행과 42501이 한 곳에서 403이 된다.
   - Current: `UserDb`도 `WorkspaceForbidden`도 예외 핸들러도 없다
   - Target: `update_one()`·`delete_one()`이 affected rows를 검사해 0이면 `WorkspaceForbidden`을 던진다. SQLSTATE `42501`(WITH CHECK 위반)과 `WorkspaceForbidden`을 **단일 예외 핸들러**가 403으로 렌더한다. 읽기 메서드에는 이 규칙을 적용하지 않는다
   - Acceptance: 0행 → `WorkspaceForbidden`, `42501` → HTTP 403, 정상 빈 조회 → HTTP 200이 각각 테스트로 확인된다. affected rows가 2 이상이면 예외를 던진다. 라우터 모듈에 403 상태 코드 리터럴이 없음이 grep으로 확인된다

5. **workspaces 최소 라우터와 교차 테넌트 차단 (SEC-06)**: 격리가 실제 HTTP 왕복으로 증명된다.
   - Current: 도메인 라우터가 0개라 "애플리케이션 경로 시도가 403으로 돌아온다"를 증명할 표면이 없다
   - Target: `PATCH /workspaces/{id}`와 `DELETE /workspaces/{id}`가 `UserDb`를 경유하는 최소 라우터로 존재한다. 워크스페이스 2개 × 사용자 2명 픽스처의 파라미터화된 pytest가 교차 접근을 시도한다 (새 라우터가 늘면 테이블에 행만 추가)
   - Acceptance: 모든 교차 시도가 HTTP 403을 받는다. 존재하지 않는 id도 **404가 아니라 403**을 받는다. 자기 워크스페이스에 DELETE를 두 번 호출하면 2회차도 403이며 이것이 D-12의 직접 귀결임이 명시된다. 각 테스트가 고유 워크스페이스/사용자를 생성·정리해 실행 순서와 병렬성에 무관하게 같은 결과를 낸다

6. **DB 트랜스포트 스파이크 (DOM-01)**: 트랜스포트가 추측이 아니라 실행된 계획으로 결정된다.
   - Current: `docs/ops/db-transport-spike.md`가 없다. 트랜스포트 미결이며 `health_check.py`가 PostgREST 왕복 하나로 임시 대응 중이다
   - Target: 합성 코퍼스 **총 50,000행 중 타깃 워크스페이스 750행(1.5%)** 위에서 RPC 경로(`SECURITY INVOKER` 함수 + 요청자 JWT)와 asyncpg + Supavisor session mode 경로를 각각 실행한다. `create function ... SET hnsw.iterative_scan`이 실제로 적용되는지가 판정 대상이다
   - Acceptance: RPC 경로에서 (a) `hnsw.iterative_scan`·`hnsw.ef_search`·`hnsw.max_scan_tuples` 3종이 **전부** 적용 확인 (b) `EXPLAIN (ANALYZE)`에 `HNSW Index Scan` 존재 (c) `k=20` 요청에 **정확히 20행** 반환 — 셋 다 참이면 RPC를 채택하고, 하나라도 거짓이면 asyncpg를 채택한다. 고정 시드 코퍼스에서 3회 반복해 세 번 모두 같은 판정이 나와야 유효하다. 결정이 `checklists.json > decisions.db_transport`에 잠기고 `docs/ops/db-transport-spike.md`와 재현용 SQL이 커밋된다

7. **마이그레이션 0007 (DOM-02, DOM-03, DOM-04)**: 이후 페이즈가 필요로 하는 스키마가 로컬과 클라우드 양쪽에 같은 순서로 존재한다.
   - Current: `0001`~`0006`만 존재한다. `complete_job_and_chain()`·`release_job()`·`jobs_dedup_idx`·검증 메타·버전 컬럼이 없다
   - Target: `0007_*.sql` 한 파일이 번호 섹션으로 (1) 검색 함수(R6 결정 반영) (2) `jobs_dedup_idx` (3) `complete_job_and_chain()` (4) `release_job()` (5) `verified_by`/`verified_at`/`expires_at` (6) `embedding_version`/`chunker_version`을 추가한다. R6 스파이크가 이 파일 작성보다 먼저 끝나야 한다
   - Acceptance: `supabase db reset`이 `0001`~`0007`을 오류 없이 적용한다. `supabase db push`로 `ap-southeast-1`에 반영되고 `supabase migration list`의 로컬/원격 목록이 일치한다. `0007`이 단일 트랜잭션으로 감싸져 부분 적용이 불가능하다. `release_job()`이 `attempts`를 1 되돌리며 락을 해제함이 SQL 테스트로 확인된다

8. **공용 한국어 토크나이저 (DOM-05, DOM-06)**: 색인과 질의가 같은 함수를 쓴다.
   - Current: `packages/core`에 토크나이저가 없다. 색인/질의 토크나이저 불일치는 오류 없이 조용히 실패한다
   - Target: `packages/core`의 **단일** 모듈이 `normalize()`(NFKC + casefold + 공백 정규화)와 `bigram()`을 제공한다. `bigram()`은 정규화된 입력만 받는다. `TSV_TOKENIZER_VERSION = "bigram-nfkc-cf-v1"`이 알고리즘·정규화 형식·casefold 여부·버전을 한 문자열에 인코딩한다
   - Acceptance: 같은 한국어 문장을 NFC·NFD·전각으로 각각 입력한 왕복 자가검색 테스트가 세 형식 모두에서 서로를 검색해낸다. 정규화되지 않은 입력을 `bigram()`에 넣으면 실패한다. 빈 문자열과 1글자 입력에서 `bigram()`이 반환하는 값이 명시되고 예외를 던지지 않음이 테스트로 고정된다

9. **결정적 슬러그 (DOM-07)**: 같은 title이 항상 같은 슬러그를 낸다.
   - Current: 슬러그 코드가 없다. `wiki_pages`의 `(workspace_id, slug)` 업서트 키가 존재하지만 그것을 만드는 함수가 없다
   - Target: `packages/core`의 순수 함수가 `normalize()` 결과에서 한글을 **로마자화하지 않고 유지**하고, 공백→하이픈, 허용 문자 외 제거, 길이 상한 적용, 충돌 시 `-2`·`-3` 접미를 붙인다. 버전 태그 `slug_v1`. LLM은 `title`만 내고 슬러그를 소유하지 않는다
   - Acceptance: 같은 title에 대한 1,000회 호출이 동일 문자열을 낸다. 기존 슬러그와 `wiki_links.target_slug` 양쪽에 대한 충돌 해소가 테스트로 확인된다. 정규화 결과가 비면 결정적 폴백(예: title 해시 접두사)을 쓰고 빈 문자열을 반환하지 않는다

10. **워커 큐 계약 증명 (DOM-08)**: LLM 비용이 발생하기 전에 큐 계약이 증명된다.
    - Current: worker에 큐 루프가 없다. `noop` 잡 타입 핸들러도 없다
    - Target: `noop` 잡 핸들러 + claim→complete 루프 + SIGTERM graceful shutdown(새 claim 중단, Railway grace period보다 짧은 상한, 초과 시 `release_job()`으로 반납) + 알 수 없는 `type`은 `last_error`와 함께 `dead`로. `noop` 잡은 테스트/스크립트가 `service_role`로 직접 insert한다 — 생산자 API는 Phase 3(ING-01)의 일이다
    - Acceptance: insert된 `noop` 잡이 claim→complete로 통과한다. 진행 중 SIGTERM에서 잡이 유실되지 않고 `queued`로 반납되며 `attempts`가 증가하지 않는다. 알 수 없는 type 잡이 `last_error`와 함께 `dead`가 된다. 같은 잡을 두 번 처리해도 상태가 `done`으로 수렴하고 이미 `done`인 잡에 `complete_job`을 불러도 예외가 나지 않는다. `release_job()` 호출 이후 그 워커가 같은 잡을 완료 처리해도 다른 워커의 진행을 덮어쓰지 않는다

11. **reap 타임아웃 기준선 (DOM-09)**: 타임아웃이 추측이 아니라 실측에서 나온다.
    - Current: `jobs`에 하트비트 컬럼이 없음이 확인되었다(`0003_jobs.sql:55-57`). `reap_stale_jobs` 기본 15분에 근거가 없다. 하트비트 컬럼은 **추가하지 않고** 잡 분할로 간다(COMP-04가 독립적으로 요구)
    - Target: Railway `asia-southeast1`의 worker가 `ap-southeast-1` Supabase를 상대로 `noop` claim→complete 왕복을 반복 측정하고, 콜드 요청과 워밍업을 분리한 뒤 백분위를 로그로 남긴다. 그 값에서 유도한 **잠정** `reap_stale_jobs` 타임아웃을 `docs/ops/`에 기록한다
    - Acceptance: 워밍업 제외 성공 표본이 200회 이상이면 p50/p99를, 그보다 적으면 p50/p95만 기록하고 한계를 명시한다. 문서에 잠정 타임아웃과 그 유도 근거, "이 값은 noop 기준이며 LLM 잡 p99는 Phase 3에서 재측정한다"는 한계, 하트비트 컬럼을 추가하지 않은 결정과 근거가 함께 남는다

12. **툴링 정합 (SEC-02·SEC-06 부수)**: 규칙과 테스트가 실제로 실행된다.
    - Current: `[tool.ruff.lint] select`에 `TID`가 없어 R2의 banned-api가 동작할 수 없다. `testpaths`에 `apps/worker/tests`가 없어 R10의 worker 테스트가 조용히 수집되지 않는다
    - Target: 루트 `pyproject.toml`의 `select`에 `TID`를 추가하고 `testpaths`에 `apps/worker/tests`를 추가한다
    - Acceptance: 저장소 루트에서 `pytest --collect-only`가 worker 테스트를 수집한다. `ruff check`가 TID 규칙을 적용한다

## Boundaries

**In scope:**

- `packages/core`의 `BaseAppSettings` · 토크나이저 모듈 · 슬러그 모듈
- `ApiSettings` / `WorkerSettings` 분리와 `create_app()` 주입, `os.environ` 직접 읽기 제거
- `worker/db/service.py`(팩토리) · `db/user.py` 분리, ruff `TID` banned-api 규칙
- GitHub Actions PR 워크플로우 1개 (pre-commit · service 사용 grep · 번들 secret grep · pytest)
- `UserDb`의 쓰기 메서드 2종과 단일 403 예외 핸들러
- `PATCH`/`DELETE /workspaces/{id}` 최소 라우터 (격리 증명 목적)
- 교차 테넌트 파라미터화 pytest (워크스페이스 2 × 사용자 2)
- DB 트랜스포트 스파이크: 합성 코퍼스 생성 → RPC/asyncpg 양쪽 실행 → 판정 → `docs/ops/db-transport-spike.md` + `checklists.json > decisions.db_transport`
- 마이그레이션 `0007` 작성 + 로컬 `db reset` 검증 + 클라우드 `db push`
- 워커 `noop` 핸들러 · claim→complete 루프 · SIGTERM 반납 · dead-letter
- Railway 실측 기반 noop 큐 오버헤드 기준선과 잠정 reap 타임아웃 문서
- 루트 `pyproject.toml`의 `select`/`testpaths` 수정

**Out of scope:**

- 실제 도메인 라우터(sources · wiki · ask · jobs 생산자) — Phase 3~5의 일이며, Phase 2의 workspaces 라우터는 격리 증명 목적의 최소 표면이다
- LLM 호출과 프롬프트 — Phase 3(COMP-01). Phase 2는 LLM 비용이 0인 상태에서 큐 계약을 증명하는 것이 목적이다
- 수집 파이프라인(parse/chunk/embed) — Phase 3
- 검색 융합·RRF·채널 정책 — Phase 4. Phase 2의 합성 코퍼스는 **트랜스포트 판정용**이지 검색 품질 판정용이 아니다
- `relaxed_order` vs `strict_order` 벤치마크(RTV-04) — Phase 4. Phase 2는 `strict_order`가 *적용되는지*만 본다
- 골든 질의 세트(RTV-06) — Phase 4
- `jobs` 하트비트 컬럼(`heartbeat_at` + `heartbeat_job()`) — 이번에 넣지 않는다. Phase 3에서 LLM 잡 p99 실측 후 잡 분할만으로 부족하면 `0008`로 추가 (되돌리기 싼 변경)
- `reap_stale_jobs` 최종 타임아웃 확정 — Phase 3. Phase 2는 noop 기준 잠정치까지다
- `.env.sample`의 `LLM_MODEL` 기본값 불일치 정리 — Phase 3(COMP-01). LLM 호출이 없어 검증 수단이 없다
- 잡 생산자 API(`POST /jobs` 등) — Phase 3(ING-01). Phase 2의 `noop` 잡은 `service_role` 직접 insert로 인큐한다

## Constraints

- **단일 Dockerfile · 단일 이미지**(01-CONTEXT.md > D-01)이므로 api 프로세스가 worker 모듈을 물리적으로 import 할 수 있다. 격리의 1차 방어선은 import 차단이 아니라 **키의 부재**(`ApiSettings`에 필드 없음 + Railway가 worker 서비스에만 secret 주입)다. 이 인과를 뒤집어 서술하면 사실과 어긋난다
- `service_role`은 BYPASSRLS다. worker 코드는 `workspace_id` 필터를 명시해야 한다
- 마이그레이션 번호가 곧 적용 순서다. `0007`은 로컬과 클라우드에 같은 순서로 들어가야 한다
- 스파이크 코퍼스는 **합성·적대적 분포**여야 한다. 코퍼스가 작거나 타깃 비율이 높으면 RPC와 asyncpg가 똑같이 통과해 스파이크가 아무것도 판정하지 못한 채 "검증했다"는 착각만 남는다
- 트랜스포트 결정은 one-way다. 뒤집으면 `0007`의 검색 함수 시그니처 · `UserDb` 구현 · Phase 4 융합 계층이 함께 움직인다. 애매하면 되돌리기 싼 쪽이 아니라 확실한 쪽으로 기운다
- pgvector는 `extensions` 스키마에 설치되어 있다. 스파이크 SQL도 schema-qualified 참조 규약을 따른다
- 색인 시점과 질의 시점 토크나이저가 동일해야 한다. 불일치는 오류 없이 조용히 실패한다
- 로컬 `psql`이 없다 — `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres`
- 모든 주석·커밋 메시지·문서는 한국어, 식별자·키워드·파일명은 영문
- 프로젝트 수명 결정은 `checklists.json > decisions.<key>`, 페이즈 한정 결정은 `02-CONTEXT.md > D-XX`를 인용한다. 같은 근거를 두 계층에 되풀이하지 않는다

## Acceptance Criteria

- [ ] `ApiSettings.model_fields`에 `SUPABASE_SECRET_KEY`·`DATABASE_URL`·`OPENROUTER_API_KEY`·`OPENAI_API_KEY`가 하나도 없다
- [ ] 필수 env가 누락되거나 **빈 문자열**일 때 해당 키 이름을 포함한 메시지로 기동이 실패한다
- [ ] `apps/api/**`에 `worker.db.service` import를 넣으면 `ruff check`가 non-zero로 종료한다
- [ ] `service_client()`가 `WorkerSettings` 인스턴스를 인자로 요구하며 모듈 전역 싱글턴이 없다
- [ ] CI 워크플로우의 네 검사 중 하나라도 실패하면 빌드가 실패한다
- [ ] 의도적 위반 브랜치 2종(worker 밖 service import / 번들 secret 노출)에서 각각 해당 CI 잡이 red가 된다
- [ ] 번들 secret grep의 대상 산출물이 존재하지 않으면 pass가 아니라 fail이 된다
- [ ] `update_one()`·`delete_one()`이 affected rows 0에서 `WorkspaceForbidden`을 던진다
- [ ] `update_one()`·`delete_one()`이 affected rows 2 이상에서도 예외를 던진다
- [ ] SQLSTATE `42501`과 `WorkspaceForbidden`을 단일 예외 핸들러가 403으로 렌더한다
- [ ] 정상적으로 비어 있는 조회가 200을 반환한다 (403이 되지 않는다)
- [ ] 라우터 모듈에 403 상태 코드 리터럴이 없다
- [ ] 교차 테넌트 CRUD 시도 전부가 HTTP 403을 받는다
- [ ] 존재하지 않는 리소스도 404가 아니라 403을 받는다
- [ ] 자기 워크스페이스 DELETE 재호출(2회차)도 403이며 그것이 D-12의 귀결임이 문서에 명시된다
- [ ] 격리 테스트가 실행 순서·병렬성에 무관하게 같은 결과를 낸다 (테스트별 고유 픽스처 생성·정리)
- [ ] 스파이크 코퍼스가 총 50,000행이고 타깃 워크스페이스가 750행(1.5%)이다
- [ ] RPC 경로에서 GUC 3종 전부 적용 · `EXPLAIN`에 `HNSW Index Scan` · `k=20`에 정확히 20행 — 셋 다 참일 때만 RPC를 채택한다
- [ ] 고정 시드 코퍼스에서 3회 반복해 세 번 모두 같은 판정이 나온다
- [ ] 트랜스포트 결정이 `checklists.json > decisions.db_transport`에 잠기고 `docs/ops/db-transport-spike.md` + 재현 SQL이 커밋된다
- [ ] `supabase db reset`이 `0001`~`0007`을 오류 없이 적용한다
- [ ] `0007`이 단일 트랜잭션으로 감싸져 부분 적용이 불가능하다
- [ ] `supabase migration list`의 로컬/원격 목록이 일치한다
- [ ] `release_job()`이 `attempts`를 1 되돌리며 락을 해제한다
- [ ] NFC·NFD·전각으로 각각 입력한 같은 한국어 문장이 서로를 검색해낸다
- [ ] 정규화되지 않은 입력을 `bigram()`에 넣으면 실패한다
- [ ] 빈 문자열과 1글자 입력에 대한 `bigram()` 반환값이 명시되고 예외를 던지지 않는다
- [ ] `TSV_TOKENIZER_VERSION`이 `bigram-nfkc-cf-v1` 형태로 정규화 형식까지 인코딩한다
- [ ] 같은 title 1,000회 호출이 동일 슬러그를 낸다
- [ ] 기존 슬러그와 `wiki_links.target_slug` 양쪽에 대한 충돌 해소가 확인된다
- [ ] 정규화 결과가 빈 title에서 결정적 폴백이 나오고 빈 슬러그가 반환되지 않는다
- [ ] `service_role`로 insert된 `noop` 잡이 claim→complete로 통과한다
- [ ] SIGTERM에서 진행 중 잡이 유실되지 않고 `queued`로 반납되며 `attempts`가 증가하지 않는다
- [ ] 알 수 없는 job type이 `last_error`와 함께 `dead`가 된다
- [ ] 같은 잡을 두 번 처리해도 상태가 `done`으로 수렴하고, 이미 `done`인 잡에 `complete_job`을 불러도 예외가 나지 않는다
- [ ] `release_job()` 이후 그 워커가 같은 잡을 완료 처리해도 다른 워커의 진행을 덮어쓰지 않는다
- [ ] Railway↔Supabase noop 큐 오버헤드가 워밍업을 분리해 측정되고, 표본 200회 이상이면 p50/p99, 미만이면 p50/p95와 한계가 기록된다
- [ ] 잠정 reap 타임아웃과 그 유도 근거, noop 기준이라는 한계, 하트비트 미추가 결정이 `docs/ops/`에 함께 남는다
- [ ] `pytest --collect-only`가 저장소 루트에서 worker 테스트를 수집한다
- [ ] `ruff check`가 TID 규칙을 적용한다

**금지사항 유래 (negative criteria):**

- [ ] `docs/ops/db-transport-spike.md`가 판정 조건 3종의 실측값을 개별 기록하며, 일부만 충족한 것을 "통과"로 적지 않는다
- [ ] reap 잠정치 문서가 noop 기준이라는 한계와 Phase 3 재측정 예정을 생략하지 않는다
- [ ] 교차 테넌트 테스트가 fail-first로 증명된다 — 정책을 느슨하게 만든 상태에서 반드시 red가 된다
- [ ] CI 보안 게이트 스텝에 `continue-on-error`·`|| true`·`set +e`·빈 결과 허용이 없다
- [ ] `service_client` 경로에 `workspace_id` 필터 없는 전역 쿼리가 없다
- [ ] 한국어 title이 해시나 빈 문자열로 퇴화하지 않고 한글을 유지한 슬러그를 낸다

## Edge Coverage

**Coverage:** 14/14 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| unclassified | R1 | ✅ covered | 빈 문자열 env를 누락과 동일하게 취급 — AC "필수 env가 누락되거나 빈 문자열일 때 키 이름을 포함한 메시지로 기동 실패" |
| concurrency | R2 | ⛔ dismissed | `importlib.import_module` 동적 import는 TID를 우회하지만, D-06의 1차 방어선은 lint가 아니라 **키의 부재**다. 모듈을 로드해도 `ApiSettings`에 필드가 없고 Railway가 api에 값을 주입하지 않으므로 실제 달성 경로가 없다 |
| unclassified | R3 | ✅ covered | grep 대상 빌드 산출물 부재를 pass가 아닌 fail로 — AC "번들 secret grep의 대상 산출물이 존재하지 않으면 pass가 아니라 fail" |
| unclassified | R4 | ✅ covered | `delete_one()`의 다중행 매치 — AC "affected rows 2 이상에서도 예외를 던진다" |
| idempotency | R5 | ✅ covered | 자기 워크스페이스 재삭제가 403 — AC "DELETE 재호출(2회차)도 403이며 D-12의 귀결임이 명시" |
| concurrency | R5 | ✅ covered | 픽스처 공유로 인한 위양성/위음성 — AC "실행 순서·병렬성에 무관하게 같은 결과, 테스트별 고유 픽스처 생성·정리" |
| unclassified | R6 | ✅ covered | 랜덤 균등 벡터로 인한 우연 판정 — AC "고정 시드 코퍼스에서 3회 반복해 세 번 모두 같은 판정" |
| unclassified | R7 | ✅ covered | 클라우드 push 부분 적용 — AC "`0007`이 단일 트랜잭션으로 감싸져 부분 적용 불가" + "migration list 로컬/원격 일치" |
| unclassified | R8 | ✅ covered | 빈 문자열·1글자 퇴화 입력 — AC "반환값이 명시되고 예외를 던지지 않는다" |
| unclassified | R9 | ✅ covered | 허용 외 문자만 있는 title의 빈 슬러그 — AC "결정적 폴백이 나오고 빈 슬러그가 반환되지 않는다" |
| idempotency | R10 | ✅ covered | at-least-once 재처리 — AC "두 번 처리해도 `done`으로 수렴, 이미 `done`인 잡에 `complete_job` 호출해도 예외 없음" |
| concurrency | R10 | ✅ covered | `release_job()` 반납 직후 원래 작업 완료 경합 — AC "다른 워커의 진행을 덮어쓰지 않는다" |
| unclassified | R11 | ✅ covered | p99를 주장할 표본 부족 — AC "표본 200회 이상이면 p50/p99, 미만이면 p50/p95와 한계 기록" |
| concurrency | R12 | ⛔ dismissed | 정적 설정 파일 한 번 수정에는 동시 실행·중단 개념이 없다. 분류기의 오판 |

## Prohibitions (must-NOT)

**Coverage:** 6/6 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| 스파이크 결과 문서는 실제 관측되지 않은 것을 관측된 것처럼 서술하거나, 판정 조건 3종 중 일부만 충족한 것을 "통과"로 기록해서는 안 된다 | R6 | resolved | judgment — D-17이 직접 경고한 실패 양식. 조건별 실측값을 개별 기록해야 판정이 재검증 가능하다 |
| reap 잠정치를 기록할 때 noop 기준이라는 한계와 LLM 잡 p99의 Phase 3 재측정 예정을 생략한 채 숫자만 남겨서는 안 된다 | R11 | resolved | judgment — 한계를 숨기면 Phase 3가 근거 없는 숫자를 물려받는다 |
| 교차 테넌트 격리 테스트가 같은 워크스페이스를 두 번 쓰거나 인증 없는 요청을 보내 항상 통과하는 공허한 형태여서는 안 된다 | R5 | resolved | test — 정책을 느슨하게 만든 상태에서 반드시 red가 되는 fail-first 증명 필요. 보안 척추 전체가 이 테스트 하나로 증명되므로 공허한 통과가 이 페이즈의 가장 비싼 실패다 |
| CI 보안 게이트 스텝이 `continue-on-error`·`\|\| true`·`set +e`·빈 결과 허용으로 실패를 삼켜서는 안 된다 | R3 | resolved | test — SEC-03의 요구는 워크플로우의 존재가 아니라 빌드 실패다 |
| `service_client` 경로가 `workspace_id` 필터 없는 전역 쿼리를 돌려서는 안 된다 | R2, R10 | resolved | test — `service_role`은 BYPASSRLS라 38개 정책이 전부 무효가 되고 오류 없이 교차 테넌트를 읽는다 |
| 슬러그 구현이 비-ASCII 제거 폴백으로 한국어 title 전체를 해시나 빈 문자열로 퇴화시켜서는 안 된다 | R9 | resolved | test — D-20이 로마자화를 배제한 만큼, 한국어 사용자만 읽을 수 없는 URL을 받는 결과는 설계 의도의 반대다 |

**canon 참조 (여기서 minting하지 않음):** 시크릿의 로그 노출은 canon — 기존 `packages/core/tests/test_logging_redaction.py`와 `/gsd-secure-phase` 소관. 커밋된 실제 자격증명(스파이크 SQL의 `DATABASE_URL`)은 canon 시크릿 스캐닝 소관. SQL 인젝션·경로 순회는 canon OWASP 소관.

**⚠ 검사 디스크립터 미포착:** 4건의 `test` 티어 금지사항은 아직 존재하지 않는 파일을 대상으로 하므로 `check_kind`/`check_target`/`check_rule`/`check_violation_fixture`/`check_clean_fixture`를 포착하지 않았다(경로를 지어내지 않는다). 이 항목들은 다운스트림에서 fail-closed로 남으며 plan-phase가 실제 검사를 배선할 때 디스크립터를 채운다.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                              |
|--------------------|-------|------|--------|----------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | 15개 요구사항이 12개 반증 가능 항목으로 수렴          |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | 검증 표면·`0007` 적용 범위·인큐 경로가 라운드 1·3에서 확정 |
| Constraint Clarity | 0.85  | 0.65 | ✓      | 코퍼스 규모·타깃 비율·표본 수가 숫자로 고정            |
| Acceptance Criteria| 0.86  | 0.70 | ✓      | 41개 pass/fail 체크박스 + 6개 negative criteria      |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      |                                                    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective     | Question summary                          | Decision locked                                                      |
|-------|-----------------|-------------------------------------------|----------------------------------------------------------------------|
| 1     | Researcher      | 라우터가 0개인데 SEC-04/06을 뭘로 증명?      | `workspaces` 최소 라우터 1개(PATCH/DELETE)를 만들어 실제 HTTP 403 증명   |
| 1     | Researcher      | `0007`을 로컬만? 클라우드까지?               | 로컬 `db reset` + 클라우드 `db push` 둘 다 Phase 2 안에서 완료          |
| 2     | Researcher      | 스파이크 판정 조건의 숫자는?                 | 50,000행 · 타깃 750행(1.5%) · `k=20` 전량 · GUC 3종 전부 — 전부 참일 때만 RPC |
| 2     | Simplifier      | `.github/`가 없는데 CI 최소 범위는?          | 단일 워크플로우 4잡: pre-commit · service grep · 번들 secret grep · pytest |
| 3     | Boundary Keeper | reap 기준선을 어디서 실측?                   | Railway `asia-southeast1` ↔ 클라우드 실측 (로컬은 교차 리전 RTT 누락)     |
| 3     | Boundary Keeper | `noop` 잡은 뭐가 인큐?                       | 테스트/스크립트가 `service_role`로 직접 insert — 생산자 API는 Phase 3    |
| 5.5   | Edge Probe      | 14개 후보 엣지                               | covered 12 · dismissed 2 (R2 동적 import, R12 동시성) · unresolved 0    |
| 5.6   | Prohibition     | recall ~10 → precision 6                    | resolved 6 (test 4 · judgment 2) · unresolved 0 · canon 3건 breadcrumb  |

---

*Phase: 02-security-spine-and-shared-domain*
*Spec created: 2026-08-06*
*Next step: /gsd-discuss-phase 2 — 구현 결정 (이미 `02-CONTEXT.md`가 D-01~D-22로 존재하므로 discuss-phase는 이 SPEC과의 정합만 확인하면 된다)*
