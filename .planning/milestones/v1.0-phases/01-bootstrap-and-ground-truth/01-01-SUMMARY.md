---
phase: 01-bootstrap-and-ground-truth
plan: 01
subsystem: infra
tags: [uv, fastapi, structlog, httpx, pytest]

requires: []
provides:
  - Python 3.12 기반 uv 3멤버 워크스페이스와 단일 lockfile
  - API/worker 공용 구조화 로깅과 민감정보 마스킹
  - liveness/readiness 엔드포인트와 SIGTERM smoke tracer
affects: [phase-02-security-domain, railway, docker, api, worker]

actuals:
  tokens: 17643
  tasks: 3
  commits: 3

tech-stack:
  added: [uv, FastAPI 0.141.1, uvicorn 0.52.0, httpx 0.28.1, structlog 26.1.0, orjson 3.11.9, pytest 9.1.1]
  patterns: [uv workspace, src layout, shared structured logging, FastAPI lifespan, readiness adapter]

key-files:
  created:
    - pyproject.toml
    - uv.lock
    - packages/core/src/nexuswiki_core/logging.py
    - apps/api/src/api/main.py
    - apps/api/src/api/health_check.py
    - apps/worker/src/worker/__main__.py
    - scripts/smoke_tracer.sh
  modified:
    - .env.sample

key-decisions:
  - "Python 3.12와 src 레이아웃을 3개 uv workspace member 전체에 동일하게 적용했다."
  - "readiness DB 왕복은 Phase 2 트랜스포트를 선점하지 않는 httpx/PostgREST 어댑터로 격리했다."
  - "production JSON 출력은 orjson bytes와 맞는 structlog BytesLoggerFactory를 사용한다."

patterns-established:
  - "공용 로깅: API와 worker는 nexuswiki_core.logging만 사용한다."
  - "헬스 분리: /health는 무의존 liveness, /health/ready는 2초 제한 DB readiness다."

requirements-completed: [BOOT-04, BOOT-06]

coverage:
  - id: D1
    description: "단일 uv.lock으로 재현되는 Python 3.12 3멤버 워크스페이스"
    requirement: BOOT-04
    verification:
      - kind: integration
        ref: "clean clone: uv sync --frozen"
        status: pass
    human_judgment: false
  - id: D2
    description: "API와 worker가 공유하는 민감정보 마스킹 구조화 로깅"
    requirement: BOOT-06
    verification:
      - kind: unit
        ref: "packages/core/tests/test_logging_redaction.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "DB 없이 동작하는 liveness와 2초 제한 readiness"
    requirement: BOOT-06
    verification:
      - kind: unit
        ref: "apps/api/tests/test_health.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "API 기동과 worker 정상 SIGTERM 종료를 관통하는 tracer"
    requirement: BOOT-06
    verification:
      - kind: e2e
        ref: "bash scripts/smoke_tracer.sh"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-08-03
status: complete
---

# Phase 1 Plan 1: Bootstrap Tracer Summary

**단일 uv lockfile 위에서 공용 structlog를 쓰는 FastAPI와 worker가 기동하고, readiness와 SIGTERM 종료까지 검증되는 tracer를 구축했다.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-03T09:10:00Z
- **Completed:** 2026-08-03T09:24:16Z
- **Tasks:** 3
- **Files modified:** 20

## Accomplishments

- Python 3.12 고정과 `src/` 레이아웃을 사용하는 uv workspace 3개를 단일 `uv.lock`으로 재현했다.
- API와 worker가 같은 structlog 설정을 사용하고 민감 키 및 중첩 값을 렌더링 전에 마스킹한다.
- `/health` liveness, 2초 제한 `/health/ready`, API/worker SIGTERM smoke tracer를 구현했다.

## Task Commits

1. **Task 1: Python 패키지 정당성 확인** - 사용자 승인 (커밋 없음)
2. **Task 2: uv 워크스페이스 · 공용 로깅 · api/worker 기동** - `aca5881` (feat)
3. **Task 3 RED: readiness와 마스킹 계약 테스트** - `c2c6e37` (test)
4. **Task 3 GREEN: readiness 어댑터와 JSON 로깅** - `0d71538` (feat)

## Files Created/Modified

- `pyproject.toml` / `uv.lock` - 루트 workspace와 재현 가능한 의존성 해상도
- `packages/core/src/nexuswiki_core/logging.py` - 공용 로깅, contextvar, 재귀 마스킹
- `apps/api/src/api/main.py` - FastAPI lifespan과 공유 HTTP client
- `apps/api/src/api/routers/health.py` - liveness와 readiness 라우터
- `apps/api/src/api/health_check.py` - 제한 시간과 사유 코드가 고정된 DB 왕복 어댑터
- `apps/worker/src/worker/__main__.py` - asyncio signal handler 기반 정상 종료
- `scripts/smoke_tracer.sh` - API/worker end-to-end 판정기
- `packages/core/tests/test_logging_redaction.py` / `apps/api/tests/test_health.py` - 7개 회귀 테스트

## Decisions Made

- 계획의 D-04, D-09, D-11, D-13을 그대로 적용했다.
- `orjson.dumps`가 bytes를 반환하므로 production logger factory는 `BytesLoggerFactory`로 맞췄다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] workspace 멤버의 build backend 명시**
- **Found during:** Task 2
- **Issue:** 새 `src/` 패키지를 uv가 editable build할 backend가 계획에 명시되지 않았다.
- **Fix:** 각 멤버에 hatchling build-system을 추가했다.
- **Files modified:** `packages/core/pyproject.toml`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`
- **Verification:** 클린 clone에서 `uv sync --frozen` 통과
- **Committed in:** `aca5881`

**2. [Rule 1 - Bug] uv wrapper SIGTERM 상태가 smoke 판정을 조기 종료**
- **Found during:** Task 2
- **Issue:** API는 정상 종료했지만 `uv run` wrapper의 143 상태를 `set -e`가 실패로 처리했다.
- **Fix:** API는 계획대로 10초 내 종료 여부만 판정하고 wrapper 상태는 무시했다. worker 종료 코드 0 판정은 유지했다.
- **Files modified:** `scripts/smoke_tracer.sh`
- **Verification:** `bash scripts/smoke_tracer.sh` → `smoke_tracer: ok`
- **Committed in:** `aca5881`

**3. [Rule 1 - Bug] orjson bytes가 문자열 표현으로 출력됨**
- **Found during:** Task 3 GREEN
- **Issue:** 기본 PrintLogger가 orjson bytes를 `b'...'` 형태로 출력해 JSON 파싱이 실패했다.
- **Fix:** production에서 `BytesLoggerFactory`를 사용하도록 설정했다.
- **Files modified:** `packages/core/src/nexuswiki_core/logging.py`
- **Verification:** `test_bound_job_context_is_rendered_as_json` 통과
- **Committed in:** `0d71538`

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking issue).
**Impact on plan:** 모두 계획된 구조를 실제 실행 가능하게 만든 최소 수정이며 범위 확장은 없다.

## Issues Encountered

- `.env.sample`은 기존 `.gitignore`의 `.env.*` 규칙에 포함되어 강제 staging이 필요했다. 샘플 값만 포함하며 실제 시크릿은 없다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Docker와 Railway 계획이 재사용할 API/worker 엔트리포인트와 smoke tracer가 준비됐다.
- Phase 2는 `health_check.py` 한 곳에서 DB 트랜스포트를 교체할 수 있다.

## Self-Check: PASSED

- 생성 산출물 존재 및 task commit 3개 확인
- 클린 clone `uv sync --frozen` 통과
- `bash scripts/smoke_tracer.sh` 통과
- `uv run pytest -q`: 7 passed

---
*Phase: 01-bootstrap-and-ground-truth*
*Completed: 2026-08-03*
