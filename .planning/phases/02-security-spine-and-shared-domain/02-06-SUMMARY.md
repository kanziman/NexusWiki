---
phase: 02-security-spine-and-shared-domain
plan: 06
subsystem: database
tags: [migration, pgvector, hnsw, job-queue, rls, grants, least-privilege, supabase-cloud]

# Dependency graph
requires:
  - phase: 02-security-spine-and-shared-domain
    provides: "02-01이 트랜스포트를 rpc로 잠금 + supabase/spike/0002_search_fn_rpc.sql의 검색 함수 시그니처 원형 + 권한 공백 발견"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-05의 TSV_TOKENIZER_VERSION 문자열과 그것이 open_questions에 올린 컬럼 타입 불일치"
provides:
  - "public.search_chunks — security invoker + hnsw GUC 3종, 요청자 JWT 전용 벡터 최근접 검색"
  - "public.release_job(p_job_id, p_worker_id) — attempts 되돌림 + locked_by 술어, 02-07의 SIGTERM 반납 경로"
  - "public.complete_job_and_chain(p_job_id, p_next_type, p_next_payload) — 완료와 인큐를 한 트랜잭션에"
  - "jobs_dedup_idx — payload->>'target_id' 부분 유니크, Phase 3 ING-01의 중복 인큐 방지"
  - "wiki_pages.verified_by/verified_at/expires_at (DOM-03)"
  - "source_chunks·wiki_embeddings의 embedding_version, source_chunks.chunker_version (DOM-04)"
  - "tsv_tokenizer_version 두 컬럼이 text — Phase 3의 색인 쓰기가 성립한다"
  - "9개 테이블 × 3개 롤 최소권한 매트릭스 — 0004의 RLS 정책이 처음으로 실제 효력을 갖는다"
  - "로컬·원격 마이그레이션 원장 일치 (0001~0007 7행 전부)"
affects: [02-04, 02-07, phase-03, phase-04]

# Actuals (#2632)
actuals:
  tokens: 12898
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "마이그레이션을 단일 트랜잭션으로 감싼다 — 부분 적용이 남기는 '스키마는 새 값을 받는데 그 값을 쓸 롤이 없는' 상태를 구조적으로 불가능하게 만든다"
    - "이미 적용된 마이그레이션은 소급 편집하지 않고 앞으로 나아가며 정정한다 (섹션 7이 0002를, 섹션 8이 0004의 머리말 전제를)"
    - "권한은 revoke all로 바닥을 만든 뒤 테이블·동작을 열거해 올린다 — grant all은 어느 롤에도 쓰지 않는다"

key-files:
  created:
    - supabase/migrations/0007_search_and_queue_extensions.sql
    - supabase/tests/0007_queue_functions.sql
    - docs/ops/migration-0007-record.md
  modified:
    - checklists.json
    - .claude/CLAUDE.md
    - apps/worker/src/worker/db/service.py
    - apps/worker/tests/test_service_client.py

key-decisions:
  - "섹션 5에 verified CHECK를 걸지 않았다 — verified_by의 on delete set null이 그 CHECK를 위반해 계정 삭제가 23514로 실패한다"
  - "섹션 8을 플랜의 문자적 범위(새 함수 revoke/grant)를 넘어 9개 테이블 최소권한 매트릭스로 확대했다 — 그것 없이는 0004의 정책 20여 개가 무력한 채 남는다"
  - "세 롤이 갖고 있던 TRUNCATE를 함께 회수했다 — TRUNCATE는 RLS를 우회한다"
  - "jobs_dedup_idx의 식별 키를 payload->>'target_id' 한 곳으로 고정하고, target_id 없는 잡은 중복이 막히지 않는다는 사실을 계약으로 명시했다"
  - "release_job의 attempts − 1을 greatest()로 감싸지 않았다 — running 잡은 claim을 거쳐 attempts >= 1이므로, 아니라면 CHECK가 소란스럽게 막는 편이 낫다"

patterns-established:
  - "새 DB 함수를 만들면 그 함수를 이미 부르고 있는 애플리케이션 호출부의 시그니처를 같은 페이즈에서 맞춘다 — 불일치를 다음 페이즈로 넘기면 런타임 404로 처음 드러난다"
  - "권한 검증은 '부여했다'가 아니라 롤별 건수를 세어 매트릭스와 대조한다"

requirements-completed: [DOM-02, DOM-03, DOM-04]

coverage:
  - id: D1
    description: "0007이 검색 함수 · jobs_dedup_idx · complete_job_and_chain을 추가한다 (DOM-02)"
    requirement: DOM-02
    verification:
      - kind: integration
        ref: "pg_proc 조회 — complete_job_and_chain, release_job, search_chunks 3종 존재 (로컬·원격 양쪽)"
        status: pass
      - kind: integration
        ref: "pg_indexes 조회 — jobs_dedup_idx 존재 (로컬·원격 양쪽)"
        status: pass
    human_judgment: false
  - id: D2
    description: "wiki_pages에 verified_by / verified_at / expires_at이 추가된다 (DOM-03)"
    requirement: DOM-03
    verification:
      - kind: integration
        ref: "information_schema.columns — wiki_pages의 세 컬럼 count = 3"
        status: pass
    human_judgment: false
  - id: D3
    description: "embedding_version / chunker_version이 추가되고 타입이 text다 (DOM-04)"
    requirement: DOM-04
    verification:
      - kind: integration
        ref: "information_schema.columns — source_chunks.embedding_version, source_chunks.chunker_version, wiki_embeddings.embedding_version"
        status: pass
    human_judgment: false
  - id: D4
    description: "release_job()이 attempts를 1 되돌리며 락을 해제하고, locked_by가 다른 워커면 아무 행도 바꾸지 않는다"
    requirement: DOM-02
    verification:
      - kind: integration
        ref: "supabase/tests/0007_queue_functions.sql 계약 1·2 (w1 반납 1행/attempts 0, w2 반납 0행/상태 불변)"
        status: pass
    human_judgment: false
  - id: D5
    description: "complete_job_and_chain 재호출이 0행 no-op이며 다음 잡을 증식시키지 않는다"
    requirement: DOM-02
    verification:
      - kind: integration
        ref: "supabase/tests/0007_queue_functions.sql 계약 4 (재호출 0행, type='noop-next' 잡 수 1 유지)"
        status: pass
    human_judgment: false
  - id: D6
    description: "0007이 단일 트랜잭션으로 감싸져 부분 적용이 불가능하다"
    verification:
      - kind: integration
        ref: "첫 비주석 행 begin; / 마지막 비주석 행 commit; · db push 출력이 migrations 배열에 0007 단일 항목"
        status: pass
    human_judgment: false
  - id: D7
    description: "tsv_tokenizer_version 두 컬럼이 smallint에서 text로 바뀌어 TSV_TOKENIZER_VERSION 문자열을 담을 수 있다"
    verification:
      - kind: integration
        ref: "information_schema.columns — text 2개 / smallint 0개 (로컬·원격 양쪽)"
        status: pass
    human_judgment: false
  - id: D8
    description: "supabase db push로 ap-southeast-1에 반영되고 migration list의 로컬/원격 목록이 일치한다"
    verification:
      - kind: integration
        ref: "supabase migration list --linked — 0001~0007 7행 전부 local==remote"
        status: pass
    human_judgment: false
  - id: D9
    description: "새 함수 전부가 anon·authenticated로부터 EXECUTE를 회수하고 service_role에만 부여한다 (검색 함수는 예외적으로 authenticated 대상)"
    verification:
      - kind: integration
        ref: "pg_proc.proacl — release_job/complete_job_and_chain = service_role=X, search_chunks = authenticated=X, anon 부재"
        status: pass
    human_judgment: false
  - id: D10
    description: "권한 공백이 닫혀 0004의 RLS 정책이 실제 효력을 갖는다"
    verification:
      - kind: integration
        ref: "role_table_grants — anon 0건 / authenticated 23건 / service_role 25건, 매트릭스와 정확히 일치 (로컬·원격 양쪽)"
        status: pass
    human_judgment: false
  - id: D11
    description: "부여한 매트릭스가 Phase 3~5의 실제 경로에 대해 넓지도 좁지도 않다"
    verification: []
    human_judgment: true
    rationale: "건수와 열거는 기계적으로 확인했지만, 각 동작이 실제로 필요한지/빠진 것이 없는지는 라우터와 워커가 실제로 도는 02-04와 Phase 3에서 처음 드러난다. 좁게 틀리면 42501로 소란스럽게 막히고 넓게 틀리면 조용하다 — 후자를 피하려고 anon 무권한과 service_role 열거를 택했다."

# Metrics
duration: 1h
completed: 2026-08-07
status: complete
---

# Phase 02 Plan 06: 마이그레이션 0007 — 검색 함수·큐 확장·최소권한 매트릭스 Summary

**이후 페이즈가 딛고 설 스키마를 `0007` 한 파일에 담아 단일 트랜잭션으로 로컬과 `ap-southeast-1`에 같은 순서로 올렸고, 그 과정에서 `0004`의 RLS 정책 20여 개를 무력하게 만들고 있던 권한 공백을 닫았다**

## Performance

- **Duration:** 약 1시간
- **Completed:** 2026-08-07
- **Tasks:** 3 (auto 2 + blocking 체크포인트 경유 1)
- **Files:** 신규 3, 수정 4
- **Commits:** 4

## Accomplishments

- **`0007`이 여덟 개 번호 섹션을 단일 트랜잭션으로 담았다.** D-21이 정한 여섯 섹션 + 토크나이저 버전 컬럼 타입 정정 + 권한. 저장소에서 마이그레이션이 자기 자신을 `begin`/`commit`으로 감싼 첫 사례이며, 그 이유는 SPEC R7의 "부분 적용 불가"다. 특히 섹션 7만 적용되고 섹션 8이 빠지는 조합 — 스키마는 새 값을 받을 수 있는데 그 값을 쓸 롤이 여전히 `42501`을 받는 상태 — 이 구조적으로 불가능해졌다.
- **`0004`의 RLS 정책이 처음으로 실제 효력을 갖는다.** 02-01 스파이크가 발견한 대로 `pg_default_acl`은 세 롤에 `Dxtm`만 주고 `arwd`를 하나도 주지 않았다. RLS는 이미 가진 권한을 좁힐 뿐이므로 정책 20여 개가 장식이었고 모든 실제 질의가 `42501`로 떨어졌다. 섹션 8이 9개 테이블에서 세 롤의 권한을 전부 회수한 뒤 테이블·동작을 열거해 다시 부여했다. `anon`은 아무것도 받지 않는다.
- **`TRUNCATE`가 사라졌다.** 회수 전 `anon`·`authenticated`·`service_role` 셋 다 9개 테이블에 `TRUNCATE`를 갖고 있었다. `TRUNCATE`는 RLS를 우회하므로, 로그인 사용자가 그 경로를 하나라도 얻으면 자기 워크스페이스가 아니라 테이블 전체가 사라진다. 플랜이 명시적으로 요구하지 않았지만 같은 revoke가 함께 걷어냈다.
- **02-05가 넘긴 타입 불일치를 창이 열려 있는 동안 닫았다.** `TSV_TOKENIZER_VERSION`은 `bigram-nfkc-cf-v1` 문자열인데 두 컬럼은 `smallint`였다. 두 테이블의 행이 0개인 지금이 `alter … type text`가 `using` 절 없이 한 줄로 끝나는 유일한 창이었고, 미뤘다면 `0008` 하나와 첫 색인 INSERT에서 막히는 `P2-ING-02`가 비용으로 남았다.
- **`release_job`의 락 소유자 술어가 SQL 테스트로 고정됐다.** `w1`이 점유한 잡을 `w2`가 반납하려 하면 0행이고 잡 상태는 그대로 `running`/`locked_by='w1'`이다. 이것이 "다른 워커의 진행을 덮어쓰지 않는다"(SPEC R10)의 SQL 수준 증명이며, 술어가 빠지면 종료 중인 워커가 살아 있는 워커의 잡을 큐로 되돌려 같은 잡이 두 번 처리된다.
- **로컬과 클라우드가 같은 순서로 존재한다.** `supabase migration list --linked`가 `0001`~`0007` 7행 전부에서 Local과 Remote가 일치한다. SPEC R7이 요구하는 것은 push의 성공이 아니라 두 목록의 일치다.

## Task Commits

1. **Task 1: `0007` 작성 — 8개 번호 섹션, 단일 트랜잭션** — `b5ba33e` (feat)
2. **Task 2: `release_job` 계약을 SQL 테스트로 고정** — `9b3ed31` (test)
   - 이탈 수정: **`ServiceDb.release_job` 시그니처 정정** — `3e52cbe` (fix)
3. **Task 3: 로컬 reset 재확인 후 클라우드 `db push` + 원장 정정** — `35449fd` (docs)

## Files Created/Modified

### 신규

- `supabase/migrations/0007_search_and_queue_extensions.sql` — 8개 번호 섹션. 헤더에 `0003`의 상태 전이도를 다시 그리되 `release` 화살표(attempts −1)를 추가했다.
- `supabase/tests/0007_queue_functions.sql` — 계약 4건. `supabase/migrations/` 밖에 있어 `db reset`이 적용하지 않으며 `rollback`으로 끝나 잔여 행이 0이다.
- `docs/ops/migration-0007-record.md` — `## 적용 일시` / `## 로컬` / `## 클라우드` / `## 한계와 되돌리기` 4절. 클라우드 절에 `migration list` 로컬/원격 대조표와 롤별 권한 건수 대조를 담았다.

### 수정

- `checklists.json` — `P2-JOB-01`에 `deviations_from_plan` 5건, `open_questions` 3건 종결(권한 공백 2건 + 토크나이저 타입 1건). `decisions`는 11개 그대로 건드리지 않았다.
- `.claude/CLAUDE.md` — Platform Requirements의 한 줄. `1 insertion / 1 deletion`.
- `apps/worker/src/worker/db/service.py` · `apps/worker/tests/test_service_client.py` — `release_job`이 `p_worker_id`를 함께 보내도록 정정.

## Decisions Made

- **섹션 5에 `verified` CHECK를 걸지 않았다.** 플랜은 "CHECK를 걸지, 애플리케이션에 맡길지 결정하고 근거를 남기라"고 열어 두었다. `verification_status = 'verified'`일 때 `verified_by is not null`을 요구하는 CHECK를 걸면, `verified_by`가 `auth.users`를 `on delete set null`로 참조하므로 계정 삭제가 발동시키는 `set null`이 곧바로 그 CHECK를 위반해 삭제가 `23514`로 실패한다. 계정 삭제는 Supabase가 관리하는 경로라 막으면 안 된다. 세 컬럼을 한 UPDATE로 함께 쓰는 책임은 `P2-QC-01`에 있다.
- **`jobs_dedup_idx`의 식별 키를 `payload ->> 'target_id'` 하나로 고정했다.** 잡 종류마다 대상이 다르므로(수집은 `raw_source_id`, 컴파일은 `wiki_id`) 컬럼을 늘리는 대신 인큐 측 계약으로 뒀다. ⚠️ `target_id`가 없는 잡은 중복이 막히지 않는다 — 유니크 인덱스에서 NULL은 서로 다른 값이기 때문이다. `nulls not distinct`(PG15+)로 막을 수도 있었지만 그러면 같은 종류의 정당한 병렬 잡까지 하나로 묶인다. 탈출구가 아니라 계약이라는 사실을 ⚠️ 주석으로 명시했다.
- **`release_job`의 `attempts − 1`을 `greatest()`로 감싸지 않았다.** `running` 잡은 claim을 거쳤으므로 `attempts >= 1`이다. 그렇지 않은 행이 여기 도달했다면 그것 자체가 버그이니 `attempts >= 0` CHECK가 소란스럽게 막는 편이 낫다. `greatest()`는 그 버그를 조용히 삼킨다.
- **검색 함수는 `search_chunks` 하나만 만들었다.** 나머지 4개 채널의 함수는 융합 가중치와 `k`가 정해지는 Phase 4(RTV-06 골든 질의 세트)의 일이다. 지금 시그니처를 고정하면 `0008`, `0009`로 계속 되돌아온다. 트랜스포트가 `rpc`라 검색 쿼리 변경이 곧 마이그레이션이라는 대가는 `decisions.db_transport`가 인지한 상태에서 감수한 것이다.
- **`service_role`에는 `search_chunks` EXECUTE를 주지 않았다.** `security invoker` + 요청자 JWT가 이 함수의 격리 수단인데, BYPASSRLS인 `service_role`이 부르면 워크스페이스 필터가 애플리케이션 코드 한 줄에만 의존하게 된다. 이 함수만 권한 방향이 반대인 이유를 주석에 남겼다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] 섹션 8을 9개 테이블 최소권한 매트릭스로 확대**

- **Found during:** Task 1
- **Issue:** 플랜의 섹션 8은 **새 함수의** `revoke`/`grant`만 지시한다. 그러나 `STATE.md` 블로커, `02-01-SUMMARY.md`, `checklists.json > open_questions` 5·6번이 모두 권한 공백의 영구 수정 소유자를 `0007`로 지정하고 있었다. 그것 없이 `0007`을 적용하면 새 `search_chunks`가 `authenticated`에게 곧바로 `42501`을 던지고, `0004`의 정책 20여 개는 계속 무력하다.
- **Fix:** 섹션 8에 `revoke all on all tables in schema public from anon, authenticated, service_role` 후 테이블·동작 열거 `grant`를 추가했다. `anon` 무권한, `grant all` 없음, `0003`의 큐 함수 revoke 경계 유지 — `open_questions` 6번이 명시한 형태 그대로다.
- **Files modified:** `supabase/migrations/0007_search_and_queue_extensions.sql`
- **Verification:** 로컬·원격 양쪽 `role_table_grants` — `anon` 0건, `authenticated` 23건, `service_role` 25건. 두 수가 매트릭스 산술과 정확히 일치.
- **Committed in:** `b5ba33e`
- **승인:** 사용자가 blocking 체크포인트에서 이 확대를 명시적으로 승인했다.

**2. [Rule 2 - Missing Critical] `TRUNCATE` 회수**

- **Found during:** Task 1 (권한 실측 중)
- **Issue:** `pg_default_acl`이 준 `Dxtm`에는 `TRUNCATE`가 들어 있다. `TRUNCATE`는 RLS를 우회하므로 로그인 사용자가 그 경로를 얻으면 워크스페이스가 아니라 테이블 전체가 사라진다. 플랜의 위협 모델에도 없던 표면이다.
- **Fix:** 위 `revoke all`이 함께 걷어낸다. 왜 이것이 위험한지를 ⚠️ 주석으로 남겼다.
- **Files modified:** `supabase/migrations/0007_search_and_queue_extensions.sql`
- **Verification:** 회수 전 세 롤 × 9개 테이블 = 27건의 `TRUNCATE`, 회수 후 0건.
- **Committed in:** `b5ba33e`

**3. [Rule 1 - Bug] `ServiceDb.release_job`이 `p_worker_id`를 보내지 않음**

- **Found during:** Task 2
- **Issue:** 02-03이 만든 호출부는 `{"p_job_id": job_id}` 하나만 보낸다. `0007` 섹션 4의 `public.release_job`은 2인자라 PostgREST가 함수를 해소하지 못한다. 02-03-SUMMARY가 "`0007` 전에 호출하면 404"라고 예고했지만, `0007`이 생긴 뒤에도 인자 수가 달라 여전히 해소되지 않는다.
- **Fix:** `release_job(self, job_id, *, worker_id)`로 올렸다. 기본값을 주지 않은 것은 의도다 — 기본값은 락 소유자 검사를 우회할 길을 남긴다.
- **Files modified:** `apps/worker/src/worker/db/service.py`, `apps/worker/tests/test_service_client.py`
- **Verification:** `uv run pytest -q` 88 passed, `uv run ruff check apps packages` 통과
- **Committed in:** `3e52cbe`
- ⚠️ 이 두 파일은 이 플랜의 `files_modified` 밖이다. 그러나 불일치를 만든 것이 이 플랜의 DDL이므로 같은 페이즈에서 고쳤다. 넘겼다면 02-07의 SIGTERM 경로에서 런타임 404로 처음 드러났을 것이다.

### 계획과의 차이 (자동 수정 아님)

**4. 플랜 Task 3의 수용기준이 서로 모순된다**

- 한 기준은 `open_questions`의 `tsv_tokenizer_version` 항목이 `[해소 …]` 접두로 닫힐 것을 요구하고, 마지막 기준은 `open_questions`가 **변경되지 않았을 것**을 요구한다. 둘을 동시에 만족할 수 없다.
- 플랜 `<action>` 본문이 항목을 닫으라고 명시하고 "`decisions`는 건드리지 않는다"만 불변 대상으로 지목하므로 `<action>`을 권위로 삼았다. `decisions` 11개는 그대로이고 `open_questions`만 갱신했다.
- 이 모순 자체를 `checklists.json`의 `deviations_from_plan`에 이탈로 기록했다.

**5. `open_questions` 3건을 닫았다 (플랜은 1건만 지시)**

- 플랜은 `tsv_tokenizer_version` 항목만 닫으라고 했다. 그러나 섹션 8이 권한 공백을 실제로 해소했으므로 5·6번(권한 공백과 그 수정 형태)을 열어 두면 원장이 사실과 어긋난다. 사용자가 체크포인트 응답에서 이 세 건 종결을 명시적으로 지시했다.
- 종결은 삭제가 아니라 기존 관례대로 `[해소 2026-08-07]` 접두 + 무엇으로 해소됐는지를 같은 줄에 남기는 방식이다. 9건 중 4건이 미해결로 남는다.

---

**Total deviations:** 3 auto-fixed (2 missing critical, 1 bug) + 2 문서화된 차이
**Impact on plan:** 산출물 목록은 플랜 그대로다. 확대된 것은 섹션 8의 내용(플랜의 8개 섹션 수는 유지)과 `open_questions` 종결 범위 두 가지이며, 둘 다 상위 원장이 이미 `0007`에 배정한 일이다.

## Issues Encountered

- **pre-commit이 worker 시그니처 커밋을 한 번 거부했다.** ruff가 `_rpc` 호출을 한 줄로 되접어 파일을 수정했고 훅이 커밋을 중단시켰다. 재-stage 후 재커밋으로 해소했으며 `--no-verify`는 쓰지 않았다.
- **`supabase db push`는 대화형 프롬프트 없이 통과했다.** `SUPABASE_ACCESS_TOKEN`은 설정되어 있지 않지만 저장된 CLI 세션이 있어 `supabase projects list`가 비대화형으로 응답한다. 플랜의 precondition이 요구한 조건은 토큰의 존재가 아니라 비대화형 동작이므로 충족이다.

## Known Stubs

없음. 다만 아래 두 가지는 스텁이 아니라 **의도적으로 다음 페이즈에 남긴 경계**다.

- **검색 함수는 5채널 중 1채널뿐이다.** 나머지 4개는 융합 가중치가 정해지는 Phase 4의 일이며, `0007` 섹션 1 주석이 왜 지금 만들지 않는지를 밝힌다.
- **`reap_stale_jobs` 최종 타임아웃은 여전히 잠정치다.** D-17이 정한 대로 Phase 3에서 LLM 잡 p99를 실측한 뒤 확정한다. `0007`은 이 값을 건드리지 않았다.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: resolved | `supabase/migrations/0004_rls_policies.sql` | 02-01이 올린 `privilege-gap` 플래그가 `0007` 섹션 8로 닫혔다. `0004:12-13`의 "이미 전권 GRANT를 가진다"는 머리말 전제는 여전히 파일 안에서 사실이 아니지만, 소급 편집 대신 `0007` 섹션 8 주석이 앞으로 나아가며 정정한다 |
| threat_flag: rls-bypass-surface | `supabase/migrations/0007_search_and_queue_extensions.sql` | 앞으로 만들 테이블은 `pg_default_acl`에서 다시 `Dxtm`(`TRUNCATE` 포함)을 물려받는다. 테이블을 추가하는 모든 마이그레이션이 자기 테이블에 대해 revoke/grant 쌍을 반복해야 하며, 빠뜨리면 조용히 열린다. 섹션 8 말미에 ⚠️로 명시했다 |
| threat_flag: null-dedup | `supabase/migrations/0007_search_and_queue_extensions.sql` | `payload`에 `target_id`가 없는 잡 종류를 추가하면 `jobs_dedup_idx`가 조용히 아무 일도 하지 않는다. Phase 3의 인큐 경로가 이 계약을 지키는지 확인해야 한다 |

## User Setup Required

`user_setup: []` — 없다. 클라우드 push는 이미 링크된 CLI 세션으로 수행되었다.

## Next Phase Readiness

**준비된 것**

- **02-07이 `release_job()`을 SIGTERM 반납 경로에 그대로 쓸 수 있다.** 호출부 시그니처는 `ServiceDb.release_job(job_id, *, worker_id="…")`이며 `worker_id`는 `claim_job`에 넘긴 것과 같은 값이어야 한다 — 다르면 0행이 돌아오고 잡은 `running`으로 남는다.
- **02-04의 실제 HTTP 왕복 테스트가 이제 의미를 갖는다.** 02-03-SUMMARY가 "권한 공백이 닫히기 전에는 어떤 실제 질의도 `42501`로 떨어진다"고 예고한 그 선행 조건이 충족됐다.
- **Phase 3의 색인 쓰기가 성립한다.** `tsv_tokenizer_version`이 `text`이므로 `TSV_TOKENIZER_VERSION`을 그대로 넣을 수 있고, `embedding_version`·`chunker_version`도 같은 타입이다.
- **Phase 3의 인큐 경로가 중복을 DB에서 막을 수 있다.** `payload`에 `target_id`를 싣고 `on conflict do nothing`으로 받으면 된다.

**확인이 필요한 것**

- ⚠️ **권한 매트릭스가 실제 경로에 맞는지는 아직 모른다.** 건수와 열거는 대조했지만 각 동작이 실제로 필요한지, 빠진 것이 없는지는 라우터와 워커가 실제로 도는 02-04와 Phase 3에서 처음 드러난다. 좁게 틀렸다면 `42501`로 소란스럽게 막히므로 발견은 쉽다. 넓게 틀린 경우가 조용한데, `anon` 무권한과 `service_role` 열거가 그 위험을 낮춘다.
- ⚠️ **원격에서 실제 요청자 JWT로 `search_chunks`를 왕복시켜 본 적은 없다.** 로컬 스파이크가 같은 형태의 함수로 확인했고 원격은 스키마 동일성만 확인했다.
- ⚠️ **이제 `0007` 이하 번호의 마이그레이션은 영구히 추가할 수 없다.** `0007`의 내용을 바꾸려면 `0008` 보정이 필요하다. 특히 섹션 7의 타입 변경은 다음에 되돌리려 할 때 실제 데이터가 있을 것이므로 사실상 편도다. 상세는 `docs/ops/migration-0007-record.md` §한계와 되돌리기.

## Self-Check: PASSED

- 신규 3개 파일 전부 디스크에 존재 (`0007_search_and_queue_extensions.sql`, `0007_queue_functions.sql`, `migration-0007-record.md`)
- 커밋 4개 전부 git 이력에 존재 (`b5ba33e`, `9b3ed31`, `3e52cbe`, `35449fd`)
- 플랜 `<verification>` 5개 항목 전부 통과: `db reset` exit 0 (`0001`~`0007`) · SQL 테스트 exit 0 · `migration list` 로컬/원격 7행 일치 · 첫/마지막 비주석 행 `begin;`/`commit;` · `checklists.json` 유효 JSON이며 이탈 기록됨
- Task 1·2·3의 수용기준 전부 통과 (섹션 8개, 대문자 SQL 키워드 0, `0002` 미수정, `text` 2 / `smallint` 0, `raise exception` 14건, 잔여 행 0, `CLAUDE.md` stale 0건 · diff 2줄)
- `uv run pytest -q` 88 passed, `uv run ruff check apps packages` 통과

---
*Phase: 02-security-spine-and-shared-domain*
*Completed: 2026-08-07*
