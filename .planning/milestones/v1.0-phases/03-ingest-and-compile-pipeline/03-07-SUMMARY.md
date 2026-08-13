---
phase: 03-ingest-and-compile-pipeline
plan: 07
subsystem: api
tags: [fastapi, jobs, rls, cancellation, budget]
requires:
  - "03-02 usage_events, budget cap, and user queue RPCs"
  - "03-05 API error rendering and source enqueue surface"
provides:
  - "Source job progress with server-owned labels and chain positions"
  - "Dead-job retry, cooperative cancellation, and display-only budget endpoints"
affects:
  - "03-08 dead-letter error handling"
  - "dashboard job-progress UI"
actuals:
  tokens: 5600
  tasks: 3
  commits: 2
tech-stack:
  added: []
  patterns:
    - "Job responses whitelist UI fields and never disclose payload."
    - "API error types render through api.errors' single registration point."
key-files:
  created:
    - apps/api/src/api/routers/jobs.py
    - apps/api/tests/test_jobs_router.py
  modified:
    - apps/api/src/api/errors.py
    - apps/api/src/api/main.py
key-decisions:
  - "Budget values are display-only; enqueue_source_job remains the authoritative cap decision."
  - "Running-job cancellation reports accepted (202) and preserves already-recorded usage."
requirements-completed: [ING-06, ING-07, OPS-01]
coverage:
  - id: D1
    description: "Source job progress exposes actual job type, server label, chain position, retries, and no payload."
    requirement: ING-06
    verification:
      - kind: integration
        ref: "apps/api/tests/test_jobs_router.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Retry and cancellation distinguish safe no-ops, isolate job IDs, and preserve usage visibility."
    requirement: ING-07
    verification:
      - kind: integration
        ref: "apps/api/tests/test_jobs_router.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Budget endpoint exposes integer display values while SQL remains authoritative at enqueue time."
    requirement: OPS-01
    verification:
      - kind: integration
        ref: "apps/api/tests/test_jobs_router.py"
        status: pass
    human_judgment: false
metrics:
  duration: "35m"
  completed: 2026-08-10
status: complete
---

# Phase 3 Plan 07: 잡 진행·제어·예산 표면 Summary

소스별 잡 진행을 실제 파이프라인 단계로 표시하고, 사용자 RLS 경계 안에서 재시도·취소·표시용 예산 조회를 제공한다.

## Accomplishments

- `parse`·`compile`·`link_sync`·`embed` 체인 위치와 서버 소유 한국어 라벨을 포함한 소스별 잡 목록을 추가했다.
- `dead` 재시도와 queued/failed 즉시 취소·running 협조적 취소를 분리된 409 토큰 및 202 응답으로 노출했다.
- 이번 달 UTC 사용량을 micro-dollar 정수로 표시하고, 이 값이 인큐 판정의 권위가 아님을 명시했다.

## Task Commits

1. **Task 1–2: 잡 진행 조회·재시도·취소·예산 라우터와 오류 렌더링** — `d4d31a1`
2. **Task 3: 잡 표면 로컬 스택 회귀 스위트** — `4173305`

## Verification

- `uv run pytest apps/api/tests/test_jobs_router.py -q -rs` — 11 passed
- `uv run pytest -q -rs` — 306개 수집 전체 스위트 완료 확인
- `uv run ruff check apps packages` — 성공
- `bash scripts/ci_check_service_usage.sh` — 성공
- `uv run pre-commit run --all-files` — 성공

## Decisions Made

- 비용 조회는 `usage_events`를 UTC 월 경계로 제한해 표시용으로 합산하며, 권위 있는 상한 판정은 `enqueue_source_job` SQL에 남겼다.
- 취소 응답은 이미 발생한 비용의 이벤트 수와 합계를 수치로 보여 주며, 취소가 과거 비용을 되돌리지 않음을 UI 문구 없이 표현한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 프로젝트 실행 경로의 pre-commit 이진 파일 부재**
- **Found during:** Task 1 검증
- **Issue:** 셸의 `pre-commit` 명령이 설치되어 있지 않았다.
- **Fix:** 고정된 프로젝트 dev 도구 경로인 `uv run pre-commit run --all-files`를 사용했다.
- **Verification:** ruff check·ruff format·prettier 모두 통과했다.
- **Committed in:** 해당 없음 (도구 실행 방식만 변경)

---

**Total deviations:** 1 auto-fixed (1 blocking environment issue).
**Impact on plan:** 구현 범위와 런타임 의존성은 바뀌지 않았다.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

03-08은 이 라우터가 노출하는 `last_error`를 안전하게 만들 즉시 dead-letter 처리를 배선할 수 있다. 03-09가 `link_sync`·`embed` 핸들러를 등록하면 이미 정한 체인 표가 그대로 해당 단계를 표시한다.

---
*Phase: 03-ingest-and-compile-pipeline*
*Completed: 2026-08-10*
