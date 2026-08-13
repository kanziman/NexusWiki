---
phase: 03-ingest-and-compile-pipeline
plan: 02
subsystem: database
tags: [migration, queue, cost-cap, rls, acl, contract-test, cancellation]
requires:
  - "supabase/migrations/0003_jobs.sql (jobs 정의 · claim_job 술어 · jobs_lock_consistency)"
  - "supabase/migrations/0004_rls_policies.sql (has_workspace_role 등 definer 헬퍼 3종)"
  - "supabase/migrations/0007_search_and_queue_extensions.sql (release_job 형태 · jobs_dedup_idx · §8 권한 방향)"
  - "supabase/migrations/0008_embedding_dimension.sql (search_chunks ACL — 이 플랜이 정정)"
  - "supabase/tests/0007_queue_functions.sql · scripts/verify_search_contract.sh (계약 러너 관례)"
provides:
  - "public.dead_letter_job(uuid, text, text) · public.cancel_job(uuid, text) — service_role, 락 소유자 술어"
  - "public.enqueue_source_job(uuid, uuid) — definer, 사용자 경로의 유일한 인큐 통로 + 인큐 시점 비용 상한"
  - "public.request_job_cancel(uuid) · public.retry_dead_job(uuid) — definer, authenticated"
  - "public.enum_check_values(text, text) — 워커 기동 시 enum 대조 가드용 카탈로그 읽기"
  - "public.usage_events (12컬럼 · RLS · 멤버 SELECT 정책) + workspaces.monthly_budget_micros"
  - "jobs.status 'canceled' + jobs.cancel_requested_at (협조적 취소)"
  - "SQLSTATE 계약 53400(상한 초과) · 42501(멤버십/소유권) 재사용"
  - "supabase/tests/0009_pipeline_ops.sql + scripts/verify_pipeline_ops.sh (단언 19블록)"
  - "docs/ops/migration-0009-record.md (로컬·클라우드 관측 기록 + 한계 6건)"
affects:
  - "03-03 이후 워커 플랜 — queue.py의 _dead_letter가 dead_letter_job으로 대체될 수 있다"
  - "ING-01 인큐 라우터 — service_client 없이 사용자 JWT로 enqueue_source_job RPC를 부른다"
  - "ING-07 잡 라우터 — retry_dead_job · request_job_cancel이 그 표면의 실물"
  - "COMP-02 워커 기동 가드 — enum_check_values가 대조 대상을 돌려준다"
  - "03-08 사용량 기록 헬퍼 — usage_events INSERT의 유일한 소유자"
  - "0010+ 모든 마이그레이션 — 함수 revoke에 service_role을 명시하는 형태가 이 파일에서 관례가 됐다"
tech-stack:
  added: []
  patterns:
    - "단일 트랜잭션 마이그레이션 (0007이 세운 관례)"
    - "security definer RPC + 본문 내 has_workspace_role 확인 = 사용자 쓰기 경로의 격리 수단"
    - "새 함수는 revoke all from public, anon, authenticated, service_role 후 필요한 롤에만 grant"
    - "definer 함수의 SQL 계약 테스트는 set local role authenticated + request.jwt.claims 컨텍스트에서"
    - "계약 러너는 종료 코드를 먼저 받아 진단 출력을 보존한다 (03-01이 세운 형태)"
key-files:
  created:
    - supabase/migrations/0009_pipeline_ops.sql
    - supabase/tests/0009_pipeline_ops.sql
    - scripts/verify_pipeline_ops.sh
    - docs/ops/migration-0009-record.md
  modified:
    - checklists.json
    - .planning/WINDOWS.md
decisions:
  - "D-P1 인큐 권한 모델은 security definer RPC — jobs에 INSERT 정책을 만들면 그 경로가 비용 상한을 건너뛴다"
  - "D-P2 비용 단위는 micro-dollar 정수(bigint), 기본 상한 $5.00/월/워크스페이스 — open question 해소"
  - "D-P3 취소는 jobs.status에 canceled를 더하고 running 잡은 협조적으로 — CHECK는 파일 번호와 달리 되돌릴 수 있다"
  - "월 경계 비교식에 at time zone 'utc'를 다시 씌워 timestamptz로 고정 — 암묵 캐스트가 세션 TZ에 의존하는 것을 막는다"
  - "enum_check_values는 ANY (ARRAY[ 형태의 CHECK만 본다 — 같은 컬럼을 언급하는 다른 CHECK의 리터럴 오염을 구조적으로 배제"
  - "모든 함수 revoke에 service_role을 명시 — 클라우드 pg_default_acl이 로컬보다 넓다"
metrics:
  duration: "25m"
  completed: 2026-08-08
actuals:
  tokens: 20055
  tasks: 3
  commits: 3
status: complete
---

# Phase 3 Plan 02: 파이프라인 운영 표면 Summary

`0009`가 큐 함수 2종·사용자 definer RPC 3종·카탈로그 함수 1종과 `usage_events`·월 비용 상한을 한
트랜잭션으로 세웠고, 로컬 `db reset`과 클라우드 `db push`까지 이 플랜 안에서 끝났다 — 그리고 `0008`이
클라우드에만 남겨 둔 `service_role` EXECUTE를 원격 관측으로 닫았다.

## 무엇을 했나

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | `supabase/migrations/0009_pipeline_ops.sql` — 단일 트랜잭션, 함수 6종·테이블 1개·컬럼 2개·CHECK 확장 1건 + 권한 | `ede6dff` |
| 2 | SQL 계약 러너 한 쌍 — `do $t` 단언 19블록, red 검증 포함 | `4adcf5c` |
| 3 | 로컬 reset · 계약 러너 3종 · 클라우드 push · 원격 권한 전수 관측 + 기록 | `5d425bb` |

## 관측 결과

로컬·클라우드 양쪽에서 동일하게 관측된 것:

- `jobs_status_check` = 6값 (`queued`/`running`/`succeeded`/`failed`/`dead`/`canceled`)
- `jobs.cancel_requested_at` = `timestamptz` · `workspaces.monthly_budget_micros` = `bigint default 5000000`
- `usage_events` RLS 활성 / 정책 1종 · `enum_check_values('jobs','status')`가 6값을 그대로 반환

원격 권한 전수 (이 플랜의 핵심 관측 — 로컬 러너로는 잡히지 않는 항목):

| 대상 | anon | authenticated | service_role |
|---|---|---|---|
| `usage_events` SELECT | false | **true** | **true** |
| `usage_events` INSERT | false | false | **true** |
| `usage_events` UPDATE/DELETE/TRUNCATE | false | false | false |
| `dead_letter_job` · `cancel_job` · `enum_check_values` | false | false | **true** |
| `enqueue_source_job` · `request_job_cancel` · `retry_dead_job` | false | **true** | false |
| `search_chunks` | false | **true** | **false ← 정정됨** |

게이트: `verify_pipeline_ops.sh` exit 0 (`pipeline_ops: ok`, 단언 19블록) · `verify_queue_functions.sh`
exit 0 · `verify_search_contract.sh` exit 0 (기존 계약 2종 회귀 없음) · `uv run pytest -rs` 147 passed ·
`pre-commit run --all-files` 통과 · `migration list` 원격 열 `0001`~`0009` 전부 일치.

**러너가 red가 되는 것까지 확인했다** — T7 단언의 기대값을 일부러 틀리게 바꾼 사본은 exit `3`,
`pipeline_ops: ok` 토큰 0회, 그리고 깨진 단언의 이름과 실제값을 인쇄했다. 통과가 조용한 통과가 아니다.

전체 관측값 표와 방법, 한계 6건은 `docs/ops/migration-0009-record.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 월 경계 비교식이 세션 TimeZone에 의존했다**

- **Found during:** Task 1 (섹션 6a 작성)
- **Issue:** 플랜이 지시한 `occurred_at >= date_trunc('month', now() at time zone 'utc')`에서
  `now() at time zone 'utc'`는 `timestamp`(무 tz)를 낳고, 그것을 `timestamptz` 컬럼과 비교하면 세션
  `TimeZone`으로 암묵 캐스트된다. 세션이 UTC가 아닌 순간 월 경계가 **오류 없이** 어긋난다. must_haves가
  요구한 "경계와 정확히 같은 시각의 행이 포함된다"가 환경에 따라 참이 되기도 거짓이 되기도 하는 상태였다.
- **Fix:** `(date_trunc('month', now() at time zone 'utc') at time zone 'utc')`로 다시 감싸 명시적으로
  `timestamptz`로 되돌렸다. 계약 테스트 T7이 같은 식을 써서 경계 포함/1마이크로초 이전 제외를 고정한다.
  이유는 함수 본문에 `⚠️` 주석으로 남겼다.
- **Files modified:** `supabase/migrations/0009_pipeline_ops.sql`, `supabase/tests/0009_pipeline_ops.sql`
- **Commit:** `ede6dff`

**2. [Rule 2 - Missing critical functionality] `enum_check_values`가 관계없는 CHECK의 리터럴을 삼켰다**

- **Found during:** Task 1 (섹션 7 작성)
- **Issue:** 플랜은 "정의 문자열이 `p_column`을 단어 경계로 포함하는 CHECK"에서 작은따옴표 리터럴을 뽑으라고
  했다. 그런데 `jobs_lock_consistency`(`0003:65-68`)도 `status`를 언급하며 `'running'`을 담고 있어 열거의
  일부처럼 딸려 나온다. 지금은 `'running'`이 이미 6값 안에 있어 결과가 우연히 맞지만, 우연에 기댄 가드는
  다음 CHECK 하나가 워커 기동을 깬다. 소비자가 기동 시 enum 대조 가드(COMP-02)라 오탐이 곧 crash-loop다.
- **Fix:** 대상을 `ANY (ARRAY[` 형태를 가진 CHECK로 좁혔다 — Postgres가 `in (...)` 열거를 렌더하는 형태이며
  `jobs_lock_consistency`는 이 형태가 아니다. 이제 T9의 `jobs.status` 단언이 우연이 아니라 구조적으로 참이다.
  대가(값이 하나뿐인 열거는 `= 'a'::text`로 렌더되어 빈 배열이 된다)는 기록 문서 §한계 6에 남겼다.
- **Files modified:** `supabase/migrations/0009_pipeline_ops.sql`
- **Commit:** `ede6dff`

**3. [Rule 2 - Missing critical functionality] 함수 revoke 대상에 `service_role`을 추가**

- **Found during:** Task 1 (섹션 8 작성)
- **Issue:** 플랜 섹션 8은 워커 전용 함수에 `revoke all … from public, anon, authenticated`, 사용자 RPC에
  `revoke all … from public, anon`을 지시했다. 이는 `0003`·`0007`·`0008`의 형태를 그대로 옮긴 것인데,
  03-01이 실측으로 밝혔듯 **클라우드의 `pg_default_acl`은 새 함수에 `service_role` EXECUTE를 기본 부여한다**
  (로컬에는 그 항목이 없다). 플랜대로 썼으면 사용자 RPC 3종이 클라우드에서만 `service_role`에 열린 채
  남아 `0008`과 똑같은 버그를 재생산했을 것이다.
- **Fix:** 여섯 함수 전부 `revoke all … from public, anon, authenticated, service_role` 후 필요한 롤에만
  grant하는 형태로 통일했다. 원격 관측에서 `service_role / enqueue_source_job` 등 3종이 `false`임을 확인했다.
- **Files modified:** `supabase/migrations/0009_pipeline_ops.sql`
- **Commit:** `ede6dff`

**4. [Rule 2 - Missing critical functionality] `enqueue_source_job`의 null 레코드 방어**

- **Found during:** Task 1
- **Issue:** 플랜의 본문 순서는 삽입이 충돌하고 조회도 0행일 때 `return next v_job`이 **모든 필드가 null인
  레코드**를 돌려주게 되어 있었다. 이는 `ServiceDb._rpc`가 이미 방어하고 있는 PostgREST 함정
  (`0행 → all-null 레코드`)을 DB 쪽에서 새로 만드는 것이다.
- **Fix:** `if v_job.id is null then return; end if;` 한 줄로 0행으로 끝내게 했다.
- **Files modified:** `supabase/migrations/0009_pipeline_ops.sql`
- **Commit:** `ede6dff`

### 플랜 대비 형태를 바꾼 것

**5. [형태 변경] 러너를 `verify_queue_functions.sh`가 아니라 `verify_search_contract.sh`에서 복사**

플랜 Task 2는 `scripts/verify_queue_functions.sh`를 복사하라고 했다. 그 원본은 03-01이 발견한 결함
(`set -e` 하에서 명령 치환 대입이 실패하면 `printf` 이전에 종료해 psql 출력이 통째로 사라진다)을 갖고 있다.
어느 단언이 깨졌는지 알 수 없는 게이트를 새로 만들 이유가 없어, 그 결함을 이미 고친
`scripts/verify_search_contract.sh`를 원본으로 삼았다. `ON_ERROR_STOP=1`과 출력 grep은 그대로다.

**6. [형태 변경] 플랜 frontmatter의 요구사항 4건을 Complete로 표시하지 않았다**

플랜 frontmatter는 `requirements: [ING-01, ING-07, OPS-01, COMP-02]`를 선언하고, 실행 절차는 그것을
`requirements mark-complete`에 넘기라고 한다. 실제로 넘겨 봤더니 네 항목이 전부 `Complete`가 됐고 그 상태는
**거짓**이다 — 넷 다 이 플랜이 만들지 않은 소비자를 요구한다:

| 요구사항 | 이 플랜이 만든 것 | 아직 없는 것 |
|---|---|---|
| ING-01 | `enqueue_source_job` RPC | 202를 돌려주는 인큐 라우터 |
| ING-07 | `retry_dead_job` RPC | 잡 라우터 |
| COMP-02 | `enum_check_values` | 워커 기동 시 대조 어서션 |
| OPS-01 | `usage_events` · 인큐 시점 상한 · 취소 경로 | **입력 크기 상한**(라우터의 Pydantic `Field(max_length=…)`) |

그래서 `git checkout -- .planning/REQUIREMENTS.md`로 네 항목을 `Pending`으로 되돌렸다. 라우터·워커 가드를
소유한 뒤 플랜이 자기 몫을 끝낼 때 표시한다. 이 프로젝트의 기록 규율(관측하지 않은 것을 적지 않는다)이
워크플로 기본 동작보다 우선이며, 특히 OPS-01은 네 조건의 AND라 셋만 참일 때 Complete로 적으면 남은 하나가
영원히 조용히 빠진다.

**7. [precondition] `SUPABASE_ACCESS_TOKEN`은 설정되어 있지 않다**

Task 3의 precondition은 토큰이 셸에 있을 것을 요구했으나 환경변수는 없었다. CLI의 저장된 세션으로
`supabase migration list --linked`와 `supabase db push --linked` 모두 비대화형으로 동작했고, precondition의
나머지 절반(원격 원장 마지막 항목이 `0008`)은 push 직전에 직접 확인했다. `0007`·`0008` 적용 때와 같은
조건이므로 진행했다. 03-01이 같은 판단을 기록했다.

## Known Stubs

없음. 이 플랜은 스텁을 남기지 않았다.

`supabase/migrations/0009_pipeline_ops.sql`이 만든 6개 함수는 전부 완전한 구현이며, 아직 호출자가 없는 것은
스텁이 아니라 **소비자가 뒤 플랜에 있는 것**이다(`queue.py` 교체는 03-03+, 인큐 라우터는 ING-01,
워커 기동 가드는 COMP-02, `usage_events` 기록 헬퍼는 03-08). 각 함수는 SQL 계약 테스트로 행동이 고정되어
있어 호출자 없이도 계약이 검증된 상태다.

## Threat Flags

없음.

이 플랜이 만든 표면은 `<threat_model>`의 T-03-07 ~ T-03-14가 이미 덮고 있고, 완화 dispositon이 붙은 7건은
전부 구현 + 계약 테스트로 고정됐다(T-03-07/08/09는 42501 raise와 T4 단언, T-03-10은 락 소유자 술어와 T1,
T-03-11은 `jobs`에 INSERT 권한 부재와 T10, T-03-12는 `metadata` 컬럼 주석, T-03-13은 UPDATE/DELETE/TRUNCATE
부재와 원격 전수 관측). `accept`로 처분된 T-03-14(협조적 취소의 잔여 비용)는
`docs/ops/migration-0009-record.md` §한계 3에 기록했다.

새로 발견된 보안 표면은 없다. 다만 **`monthly_budget_micros`를 바꾸는 사용자 경로가 없다**는 것은 위협이
아니라 의도된 제약이며(사용자가 스스로 상한을 올릴 수 있으면 상한이 아니다) 기록 문서 §한계 2에 있다.

## Self-Check: PASSED

- `supabase/migrations/0009_pipeline_ops.sql` FOUND
- `supabase/tests/0009_pipeline_ops.sql` FOUND
- `scripts/verify_pipeline_ops.sh` FOUND (실행 비트 있음)
- `docs/ops/migration-0009-record.md` FOUND (non-empty)
- 커밋 `ede6dff` · `4adcf5c` · `5d425bb` FOUND
- `checklists.json` 유효한 JSON이며 월 상한 항목이 `[해소 2026-08-08]`로 시작
- `.planning/WINDOWS.md` 5번 `fixed` (open_count 5 → 4)
