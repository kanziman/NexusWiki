---
phase: 02-security-spine-and-shared-domain
plan: 07
subsystem: backend
tags: [job-queue, worker, graceful-shutdown, dead-letter, idempotency, postgrest, tdd]

# Dependency graph
requires:
  - phase: 02-security-spine-and-shared-domain
    provides: "02-03의 service_client(settings) 팩토리와 ServiceDb 큐 RPC 4종"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-06의 0007 release_job(p_job_id, p_worker_id)과 jobs_dedup_idx, 그리고 ServiceDb.release_job의 worker_id 필수화"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-02의 WorkerSettings — 필수 secret 누락 시 부팅 실패"
provides:
  - "worker.handlers.HANDLERS — 사실상의 잡 종류 열거. Phase 3은 여기에 행만 추가한다"
  - "worker.handlers.JobHandler Protocol — workspace_id를 기본값 없는 키워드 전용 인자로 못 박는다"
  - "worker.handlers.UnknownJobTypeError / resolve_handler — 미등록 type 검증 지점"
  - "worker.handlers.noop.handle_noop — LLM 비용 0의 성공 핸들러"
  - "worker.queue.run_queue_loop / process_next_job — claim→핸들러→complete 루프"
  - "worker.queue.WORKER_GRACE_SECONDS(20s) < PLATFORM_GRACE_SECONDS(30s) — SIGTERM 상한"
  - "worker.queue.sanitize_error — last_error 정제 훅 (Phase 3 OPS가 채운다)"
  - "worker.__main__이 큐 루프를 기동한다 — RTT 프로브와 SIGTERM/SIGINT 등록은 그대로"
  - "scripts/enqueue_noop.sql — Phase 2의 유일한 인큐 수단"
  - "ServiceDb._rpc가 0행 composite RPC를 None으로 정규화한다"
  - "apps/worker/tests/test_queue.py의 로컬 통합 픽스처 — 사용자·워크스페이스·잡을 만들고 cascade로 지운다"
affects: [02-08, phase-03]

# Actuals (#2632)
actuals:
  tokens: 5500
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "대역(FakeQueue)이 SQL 함수의 계약을 그대로 흉내 내고, 그 이해가 맞는지는 같은 파일의 실제 DB 통합 테스트가 검증한다 — 대역만 있으면 틀린 이해가 그대로 통과한다"
    - "통합 테스트 픽스처가 실제 배치의 권한 경계를 그대로 밟는다: 워크스페이스는 요청자 JWT로, 잡은 service key로"
    - "로컬 전용 통합 테스트는 loopback 가드와 NEXUSWIKI_LOCAL_* 전용 변수로 클라우드 오염을 구조적으로 막는다"

key-files:
  created:
    - apps/worker/src/worker/handlers/__init__.py
    - apps/worker/src/worker/handlers/noop.py
    - apps/worker/src/worker/queue.py
    - apps/worker/tests/test_handlers.py
    - apps/worker/tests/test_queue.py
    - scripts/enqueue_noop.sql
  modified:
    - apps/worker/src/worker/__main__.py
    - apps/worker/src/worker/db/service.py
    - apps/worker/tests/test_service_client.py

key-decisions:
  - "claim에 type 필터를 걸지 않는다 — 필터를 걸면 레지스트리 밖 type이 큐에 남아 영원히 아무도 집지 않는다. 전부 집어와 명시적으로 데드레터로 보내는 것이 0003:31-36이 워커에 지운 책임이다"
  - "즉시 dead는 현재 SQL 표면으로 불가능하다 — dead는 fail_job/reap_stale_jobs 양쪽에서 attempts >= max_attempts로만 도달한다. jobs 직접 UPDATE는 금지 경로이므로 fail_job(backoff=0)으로 대기 없이 수렴시킨다"
  - "grace 상한은 stop이 세워진 뒤에만 적용한다 — 정상 운영 중 상한은 하트비트 대신 잡 분할을 택한 D-16의 전제를 깬다"
  - "반납 후 그 잡 참조를 버린다. complete_job은 locked_by를 보지 않으므로 SQL이 막아주지 않는다 — 부르지 않는 것이 유일한 방어다"
  - "0행 composite RPC의 all-null 레코드를 ServiceDb._rpc가 None으로 정규화한다 — 정규화가 없으면 at-least-once 재호출 no-op이 성공으로 기록된다"

patterns-established:
  - "경합 테스트가 방어를 단언한 뒤, 마지막에 그 방어가 없을 때 실제로 무엇이 깨지는지를 같은 테스트가 재현한다 — 계약의 주체가 SQL이 아니라 애플리케이션임을 못 박는 법"
  - "통합 픽스처의 자원 해제는 생성 실패 경로까지 덮는 중첩 try/finally여야 한다 — 안쪽에만 두면 실패한 실행마다 고아 계정이 쌓인다"

requirements-completed: [DOM-08]

coverage:
  - id: D1
    description: "service_role로 insert된 noop 잡이 claim→complete로 통과한다"
    requirement: DOM-08
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue.py#test_noop_job_claim_to_complete"
        status: pass
      - kind: integration
        ref: "apps/worker/tests/test_queue.py#test_reprocessing_a_finished_job_converges_to_succeeded (로컬 DB 실제 왕복, 잡이 succeeded)"
        status: pass
    human_judgment: false
  - id: D2
    description: "SIGTERM에서 진행 중 잡이 유실되지 않고 queued로 반납되며 attempts가 증가하지 않는다"
    requirement: DOM-08
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue.py#test_job_exceeding_grace_is_released_without_consuming_an_attempt"
        status: pass
      - kind: integration
        ref: "apps/worker/tests/test_queue.py#test_late_completion_after_release_does_not_overwrite_another_worker (실제 release_job 후 attempts == 0, status == queued)"
        status: pass
    human_judgment: false
  - id: D3
    description: "알 수 없는 job type이 last_error와 함께 dead가 된다"
    requirement: DOM-08
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue.py#test_unknown_type_is_dead_lettered_with_the_type_in_last_error"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_queue.py#test_unknown_type_never_reaches_a_handler"
        status: pass
    human_judgment: false
  - id: D4
    description: "같은 잡을 두 번 처리해도 상태가 succeeded로 수렴하고, 이미 끝난 잡에 complete_job을 불러도 예외가 나지 않는다"
    requirement: DOM-08
    verification:
      - kind: integration
        ref: "apps/worker/tests/test_queue.py#test_reprocessing_a_finished_job_converges_to_succeeded (재호출이 None, 상태·attempts 불변)"
        status: pass
    human_judgment: false
  - id: D5
    description: "release_job() 이후 그 워커가 같은 잡을 완료 처리해도 다른 워커의 진행을 덮어쓰지 않는다"
    requirement: DOM-08
    verification:
      - kind: integration
        ref: "apps/worker/tests/test_queue.py#test_late_completion_after_release_does_not_overwrite_another_worker (A 반납 → B claim → 잡이 running/locked_by=B)"
        status: pass
    human_judgment: false
  - id: D6
    description: "graceful shutdown 상한이 플랫폼 grace period보다 짧고, 초과 시 release_job()으로 반납한다"
    requirement: DOM-08
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue.py#test_grace_is_shorter_than_the_platform_grace_period"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_queue.py#test_job_finishing_within_grace_completes_normally (상한 안에서는 정상 complete, release 없음)"
        status: pass
    human_judgment: false
  - id: D7
    description: "queue.py가 jobs 이외의 어떤 테이블에도 workspace_id 없이 접근하지 않으며, 클레임한 잡의 workspace_id를 핸들러에 전달한다 (prohibitions)"
    requirement: DOM-08
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue.py#test_handler_receives_workspace_scope"
        status: pass
      - kind: integration
        ref: "apps/worker/tests/test_queue.py#test_real_job_delivers_its_workspace_scope_to_the_handler"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_handlers.py#test_every_registered_handler_requires_workspace_id"
        status: pass
    human_judgment: false
  - id: D8
    description: "bind_job_context / clear_job_context가 잡마다 짝을 이루고 핸들러 예외에도 finally가 컨텍스트를 지운다 (T-02-45)"
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue.py#test_job_context_is_bound_and_always_cleared"
        status: pass
    human_judgment: false
  - id: D9
    description: "실제 Railway 컨테이너에서 SIGTERM → 20초 상한 → release_job 경로가 그대로 도는지"
    verification: []
    human_judgment: true
    rationale: "여기서 증명한 것은 로컬 이벤트 루프 안에서의 상한과 반납이다. Railway가 실제로 주는 grace period(코드가 30초로 가정)와 컨테이너 종료 순서는 배포된 프로세스에서만 관측된다. 02-08이 큐 기준선을 실측할 때 함께 확인해야 하며, 플랫폼 grace가 20초 이하라면 WORKER_GRACE_SECONDS를 낮춰야 한다."

# Metrics
duration: 12min
completed: 2026-08-07
status: complete
---

# Phase 02 Plan 07: 워커 큐 계약 — noop 왕복·SIGTERM 반납·데드레터 Summary

**LLM 비용 0인 상태에서 claim→complete 왕복 · `attempts`를 소모하지 않는 SIGTERM 반납 · 미등록 type의 데드레터 세 경로를 고정했고, 그 과정에서 0행 RPC가 성공으로 읽히던 어댑터 결함을 잡았다**

## Performance

- **Duration:** 약 12분 (첫 커밋 01:15 → 마지막 커밋 01:26)
- **Completed:** 2026-08-07
- **Tasks:** 3 (TDD 2 + 통합 검증 1)
- **Files:** 신규 6, 수정 3
- **Tests:** 128 → 133 (worker 33 → 49: 핸들러 5 + 큐 16 + service_client 2 추가)

## Accomplishments

- **`HANDLERS`가 `jobs.type`의 CHECK 자리를 실제로 지킨다.** `0003_jobs.sql:31-36`이 잡 종류의 열거를 DB가 아니라 워커 레지스트리에 맡겼고, 이 플랜이 그 나머지 절반을 채웠다. `claim_job`에 type 필터를 **걸지 않는 것**이 핵심이다 — 필터를 걸면 레지스트리 밖 type이 큐에 남아 아무도 집지 않는 상태가 되고, 그것은 데드레터보다 나쁘다(조용하기 때문이다).
- **SIGTERM 반납이 `attempts`를 소모하지 않는다.** 테스트가 단언하는 것은 "상태가 `queued`로 돌아왔다"가 아니라 "`attempts`가 claim 이전 값과 같다"이다. `fail_job`을 재사용했다면 상태는 똑같이 돌아오지만 재배포 세 번에 정상 잡이 `dead`로 떨어진다 — D-18이 `release_job`을 따로 만든 유일한 이유이며, 이 플랜이 그것을 처음 실제로 부른 곳이다.
- **반납 이후의 경합을 실제 DB에서 재현했다.** 워커 A가 반납 → 워커 B가 같은 잡을 claim → A가 뒤늦게 `complete_job`. 테스트는 먼저 루프가 그 완료를 시도하지 않아 B의 진행(`running`/`locked_by='B'`/`attempts=1`)이 살아 있음을 단언하고, **그다음 `complete_job`을 직접 불러 실제로 `succeeded`가 되는 것을 보여준다**. `complete_job`은 `locked_by`를 보지 않으므로 SQL은 이것을 막지 않는다 — 부르지 않는 것이 유일한 방어이고, 그 주체는 워커 코드다.
- **0행 RPC가 성공으로 읽히던 결함을 실제 왕복이 드러냈다.** `returns public.jobs` 함수가 0행이면 PostgREST는 `null`이 아니라 **모든 필드가 `null`인 레코드**를 돌려준다. 큐 함수들은 `where … and status = 'running'` 덕분에 재호출이 정상적으로 0행이고(at-least-once라 재호출이 정상 경로다), 그것을 그대로 돌려주면 호출부의 `if row:`가 no-op을 성공으로 읽는다. 단위 테스트만 있었다면 영원히 드러나지 않았을 종류의 버그다.
- **grace 상한이 `stop` 이후에만 적용된다.** 정상 운영 중 상한으로 긴 잡을 죽이면, 하트비트 대신 잡 분할을 택한 D-16의 전제(분할 전까지는 긴 잡이 그대로 돈다)가 무너진다. 상수는 `WORKER_GRACE_SECONDS(20s) < PLATFORM_GRACE_SECONDS(30s)`이며 이 부등식 자체를 테스트가 고정한다.
- **통합 픽스처가 실제 권한 경계를 그대로 밟는다.** `service_role`은 `workspaces`에 SELECT만 갖는다(0007 섹션 8). 그래서 픽스처는 사용자 → 요청자 JWT → 워크스페이스 생성 순서를 밟고, 잡만 service key로 다룬다. `jobs`에는 어느 롤도 DELETE 권한이 없으므로 정리는 워크스페이스 삭제의 cascade가 유일한 경로다.

## Task Commits

1. **Task 1: 핸들러 레지스트리와 noop 핸들러** — `6d456df` (test, RED) → `a5f0c70` (feat, GREEN)
2. **Task 2: claim→complete 루프와 SIGTERM graceful shutdown** — `d01f2d8` (test, RED) → `667984d` (feat, GREEN)
3. **Task 3: 실제 DB 통합 검증 — 멱등성과 경합** — `13d4ee0` (test, 어댑터 이탈 수정 포함)

## Files Created/Modified

### 신규

- `apps/worker/src/worker/handlers/__init__.py` — `HANDLERS` · `JobHandler` Protocol · `UnknownJobTypeError` · `resolve_handler`. Protocol 위의 `⚠️`가 `workspace_id` 필수화의 근거(BYPASSRLS)를 담는다.
- `apps/worker/src/worker/handlers/noop.py` — `handle_noop`. `except`가 하나도 없다 — 재시도/데드레터 판정은 큐 루프의 몫이다.
- `apps/worker/src/worker/queue.py` — 상태 전이도가 헤더에 있고, 이 모듈이 `jobs`를 직접 UPDATE하지 않는다는 사실을 그 위에 적었다. `sanitize_error`가 `last_error` 정제 훅 자리를 잡는다.
- `apps/worker/tests/test_handlers.py` (5 tests) · `apps/worker/tests/test_queue.py` (16 tests: 단위 13 + 통합 3)
- `scripts/enqueue_noop.sql` — `payload`에 `target_id`를 실어 `jobs_dedup_idx`를 만족시키고, `supabase/migrations/`에 두면 안 되는 이유를 헤더에 적었다.

### 수정

- `apps/worker/src/worker/__main__.py` — `await stop.wait()` 자리를 `run_queue_loop`으로 바꿨다. SIGTERM/SIGINT 등록, RTT 프로브, `finally: clear_job_context()`는 그대로다.
- `apps/worker/src/worker/db/service.py` — `_rpc`가 all-null 레코드를 `None`으로 정규화한다 (이탈 3).
- `apps/worker/tests/test_service_client.py` — 위 정규화의 회귀 테스트 2건.

## Decisions Made

- **`claim_job`에 type 필터를 넘기지 않는다.** `p_types`는 필터일 뿐이라 레지스트리 밖 type을 걸러내면 그 잡이 큐에 영구히 남는다. 전부 집어와 명시적으로 데드레터로 보내는 쪽이 `0003:31-36`의 계약이고, 오타가 `last_error`로 드러나는 경로도 그것뿐이다.
- **grace 상한은 `stop` 이후에만.** `asyncio.wait`로 핸들러와 `stop`을 함께 기다리고, `stop`이 먼저 오면 그때부터 `wait_for`로 상한을 건다. 정상 경로에는 상한이 없다.
- **반납한 잡의 참조를 즉시 버린다.** `release_job` 직후 `return`하며, 그 잡에 대한 `complete_job`/`fail_job`은 어떤 경로로도 호출되지 않는다. 단위 테스트가 두 호출의 부재를 단언한다.
- **`_rpc`의 all-null 정규화 위치는 어댑터다.** `queue.py`에서만 막으면 Phase 3의 모든 새 호출부가 같은 함정을 다시 밟는다. `setof` 함수는 빈 배열로 오므로 영향받지 않는다.
- **로컬 통합 테스트의 키는 `NEXUSWIKI_LOCAL_*` 전용 변수로만 읽는다.** `.env.local`에는 실제 클라우드 키가 들어 있어 `SUPABASE_URL` 계열 이름을 쓰면 사고 한 번으로 프로덕션 큐에 잡을 만들게 된다. loopback 가드가 이것을 assert로 못 박고, 스택이 죽어 있으면 skip한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 0행 composite RPC가 all-null 레코드로 돌아와 no-op이 성공으로 읽힘**

- **Found during:** Task 3 (멱등성 통합 테스트)
- **Issue:** `complete_job` 재호출은 `where … and status = 'running'` 때문에 0행이어야 하고 호출부는 그것을 `None`으로 봐야 한다. 그런데 PostgREST는 `returns public.jobs` 함수의 0행을 `{"id": null, "status": null, …}` 레코드로 돌려준다. `ServiceDb._rpc`가 그것을 그대로 반환하므로 `if row:`가 참이 되어, at-least-once 큐에서 "두 번 처리해서 두 번 다 성공"으로 기록된다.
- **Fix:** `_rpc`가 모든 값이 `None`인 dict를 `None`으로 정규화한다. 실제 잡 행은 `id`가 항상 non-null이므로 오탐이 없다.
- **Files modified:** `apps/worker/src/worker/db/service.py`, `apps/worker/tests/test_service_client.py`
- **Verification:** `test_all_null_record_from_a_zero_row_composite_function_becomes_none` · `test_a_real_row_survives_the_zero_row_normalisation` · 멱등성 통합 테스트 통과
- **Committed in:** `13d4ee0`
- ⚠️ `db/service.py`는 이 플랜의 `files_modified` 밖이다. 02-06이 같은 이유(호출부 불일치를 만든 쪽이 같은 페이즈)로 이 파일을 고친 선례를 따랐다. 넘겼다면 Phase 3의 모든 새 호출부가 같은 함정을 다시 밟는다.

**2. [Rule 1 - Bug] 통합 픽스처가 워크스페이스 생성 실패 시 auth 사용자를 유출**

- **Found during:** Task 3 (첫 실행이 403으로 실패한 뒤 `auth.users`에 3건 잔류)
- **Issue:** 사용자 삭제가 안쪽 `try/finally`에만 있어, 워크스페이스 생성이 터진 실행마다 고아 계정이 쌓이고 아무도 지우지 않는다.
- **Fix:** 사용자 생성 직후를 감싸는 바깥 `try/finally`를 추가했다. 삭제 순서는 워크스페이스(→ jobs cascade) → 사용자다 — `workspaces.owner_id`가 `on delete restrict`이기 때문이다.
- **Files modified:** `apps/worker/tests/test_queue.py`
- **Verification:** 고아 3건 정리 후 전체 스위트 2회 연속 실행 — `auth.users` 0건, `public.jobs` 0건
- **Committed in:** `13d4ee0`

### 계획과의 차이 (자동 수정 아님)

**3. 미등록 type이 "한 번에" `dead`가 되지는 않는다 — 그럴 수 있는 SQL 프리미티브가 없다**

플랜 Task 2 `<behavior>` Test 3과 `<action>` 5번은 "재시도 없이 곧바로 `dead`"를 요구한다. 실제 표면을 확인한 결과 **현재 함수 집합으로는 불가능하다**:

- `fail_job`은 `case when attempts >= max_attempts then 'dead' else 'failed' end`로만 `dead`에 도달한다.
- `reap_stale_jobs`도 같은 게이트를 쓴다.
- `0007`은 `release_job`·`complete_job_and_chain`을 더했을 뿐 강제 `dead` 경로가 없다.
- 남은 길은 `jobs`를 직접 UPDATE하는 것뿐인데, 그것은 `0003:92-98`과 `CLAUDE.md` Anti-Patterns가 금지한 경로다. `attempts` 회계와 `jobs_lock_consistency` 검사가 함수 안에만 있기 때문이다.

**택한 것:** `fail_job(backoff = '0 seconds')`. `run_after = now()`가 되어 잡은 **대기 없이** 다시 claim 대상이 되고, 핸들러는 한 번도 돌지 않은 채 `max_attempts` 안에 `dead`로 수렴한다. 관측 가능한 종착 상태(`dead` + `last_error`에 type 문자열)는 플랜이 요구한 그대로이며, 백오프 대기도 핸들러 실행도 없다. 대신 "한 번의 왕복"은 아니다.

**택하지 않은 것과 이유:**
- *새 마이그레이션 `0008`에 `dead_letter_job()` 추가* — 이 플랜의 `files_modified` 밖이고, 로컬에만 적용하면 02-06이 맞춰 놓은 로컬/클라우드 원장 일치가 깨진다. 클라우드 `db push`는 이 실행의 체크포인트 경계 밖이다.
- *워커가 그 잡만 재-claim하며 즉시 소진* — `claim_job`은 id로 지정할 수 없어 **다른 잡을 집게 된다**. 명백히 위험하다.

**후속:** `0008`의 `dead_letter_job(p_job_id, p_error)`가 이 자리를 닫는다. `.planning/WINDOWS.md`에 `deviation`으로 기록했고, `queue.py`의 `_dead_letter` docstring이 같은 사실을 코드 옆에 남긴다. Phase 3이 잡 종류를 늘리기 전에 처리하는 것이 좋다 — 종류가 늘수록 오타 type도 늘어난다.

**4. `test_queue.py`가 플랜의 9개 `<behavior>`를 13개 단위 테스트로 나눴다**

Test 3(데드레터)과 Test 4(핸들러 실패)가 각각 두 축(상태 판정 / 핸들러 도달 여부, 재시도 남음 / 소진)을 갖고 있어 한 테스트에 묶으면 실패 시 어느 축이 깨졌는지 알 수 없다. 상수 부등식과 워커 식별자도 별도 테스트로 뺐다. 덮는 계약은 플랜과 동일하다.

---

**Total deviations:** 2 auto-fixed (bug 2) + 2 문서화된 차이
**Impact on plan:** 산출물 목록은 플랜 그대로다. 확대된 것은 `db/service.py` 정규화 한 곳이며, 축소된 것은 데드레터의 "한 번에"라는 성질 하나다 — 종착 상태는 그대로다.

## Issues Encountered

- **`service_role`은 `workspaces`를 INSERT할 수 없다.** 통합 픽스처의 첫 시도가 403으로 막혔다. `0007` 섹션 8의 최소권한 매트릭스가 `service_role`에 `workspaces` SELECT만 주었기 때문이며, 이것은 결함이 아니라 설계다(워크스페이스 생성은 사용자 경로). 픽스처를 실제 배치 순서로 고쳤고, 그 과정에서 02-06이 만든 매트릭스가 실제 경로에서 처음으로 검증됐다 — 02-06-SUMMARY의 D11(human_judgment)이 예고한 "라우터와 워커가 실제로 도는 곳에서 처음 드러난다"가 여기서 한 건 소진됐다.
- **pre-commit이 커밋을 두 번 되돌렸다.** ruff-format이 `queue.py`와 `test_queue.py`의 줄바꿈을 고쳤다. 재-stage 후 재커밋으로 해소했으며 `--no-verify`는 쓰지 않았다.

## Known Stubs

없음. 아래 셋은 스텁이 아니라 **의도적으로 다음 단계에 남긴 경계**다.

- **`handle_noop`은 일을 하지 않는다.** 그것이 목적이다 — LLM 비용 0으로 큐 계약을 증명한다(D-17). Phase 3은 `HANDLERS`에 행을 더한다.
- **`sanitize_error`는 타입+메시지 절단만 한다.** Phase 2에는 provider 호출이 없어 마스킹할 대상이 없다. 훅 자리와 `⚠️` 근거만 남겼고 Phase 3 OPS가 채운다(T-02-44).
- **`PLATFORM_GRACE_SECONDS = 30.0`은 가정이다.** Railway의 실제 grace period를 관측한 값이 아니다. 02-08이 배포 기준선을 실측할 때 함께 확인해야 한다.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: missing-primitive | `apps/worker/src/worker/queue.py` | T-02-43(미등록 type 무한 재시도)의 완화가 부분적이다. 잡은 `max_attempts` 안에 `dead`로 수렴하지만 그 사이 `max_attempts`번의 claim 왕복이 발생한다. 잡 종류가 늘어나면 오타 type도 늘어나므로 `0008`의 `dead_letter_job()`으로 닫는 것이 맞다 |
| threat_flag: unverified-assumption | `apps/worker/src/worker/queue.py` | T-02-42의 근거인 `PLATFORM_GRACE_SECONDS = 30.0`이 관측값이 아니다. 실제 grace가 20초 이하라면 반납이 시작되기 전에 SIGKILL이 오고 잡이 15분 묶인다 |

## User Setup Required

`user_setup: []` — 새 패키지도 외부 서비스 설정도 없다. 통합 테스트는 로컬 스택이 떠 있으면 돌고, 없으면 skip한다.

## Next Phase Readiness

**준비된 것**

- **02-08이 이 루프 위에서 claim→complete 왕복을 실측할 수 있다.** `process_next_job`이 잡 하나의 왕복을 캡슐화하므로 그 둘레를 재면 된다. 인큐는 `scripts/enqueue_noop.sql`이다.
- **Phase 3은 `HANDLERS`에 행만 추가하면 된다.** 시그니처는 `async def h(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None`이며, `workspace_id`를 빠뜨리면 `test_every_registered_handler_requires_workspace_id`가 red가 된다.
- **`ServiceDb`의 반환값을 이제 `if row is None`으로 판정해도 된다.** 0행이 `None`으로 정규화됐다.

**확인이 필요한 것**

- ⚠️ **실제 Railway 컨테이너에서 SIGTERM 경로가 도는 것을 본 적은 없다.** 여기서 증명한 것은 로컬 이벤트 루프 안의 상한과 반납이다.
- ⚠️ **미등록 type의 데드레터는 `max_attempts`번의 claim을 소비한다** (이탈 3). `0008`이 닫기 전까지 이 성질이 남는다.
- ⚠️ **`0007` 권한 매트릭스가 Phase 3의 실제 경로에 맞는지는 여전히 미지다.** 이 플랜이 `workspaces` INSERT 한 건을 확인했고(service_role 불가 = 의도대로), 나머지는 라우터와 실제 핸들러가 도는 곳에서 드러난다.

## Self-Check: PASSED

- 신규 6개 파일 전부 디스크에 존재 (`handlers/__init__.py`, `handlers/noop.py`, `queue.py`, `test_handlers.py`, `test_queue.py`, `enqueue_noop.sql`)
- 커밋 5개 전부 git 이력에 존재 (`6d456df`, `a5f0c70`, `d01f2d8`, `667984d`, `13d4ee0`)
- 플랜 `<verification>` 6개 항목 전부 통과: `uv run pytest -q` 133 passed · SIGTERM 반납에서 `attempts` 불변 단언 · 미등록 type이 `last_error`에 type 문자열과 함께 `dead` · 재처리 후 `succeeded` 수렴 및 무예외 · `release_job` 이후 B의 진행 유지 · `uv run ruff check apps packages` exit 0
- Task 1·2·3 수용기준 전부 통과: `HANDLERS`에 `noop` · `handle_noop`에 `workspace_id` · `noop.py`의 `except` 0건 · `__init__.py`에 `decisions.db_access`와 `⚠️` · `^WORKER_GRACE_SECONDS` 1건 · `release_job` 4건 · `job_dead_lettered` 1건 · `bind_job_context`/`clear_job_context` 각 2건이며 후자가 `finally` 안 · `^[a-z_]+ = service_client` 0건 · `__main__`에 `run_queue_loop`과 `add_signal_handler` 유지 · `enqueue_noop.sql`에 `supabase/migrations` 문자열
- 전체 스위트 2회 연속 exit 0, 두 번 다 종료 후 `select count(*) from public.jobs` = 0, `auth.users` = 0

---
*Phase: 02-security-spine-and-shared-domain*
*Completed: 2026-08-07*
