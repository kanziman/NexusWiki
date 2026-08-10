---
phase: 03-ingest-and-compile-pipeline
plan: 05
subsystem: api-database
tags: [sources, storage, jwt, postgres, budget, sqlstate]
requires:
  - "03-04 tracer API and enqueue_source_job RPC"
provides:
  - "File and URL source enqueue endpoints with streaming size limits and duplicate visibility"
  - "NW402 budget SQLSTATE mapped by api.errors to the public 402 response"
  - "Local-stack regression coverage for source request boundaries and budget rejection"
affects:
  - "03-06 extraction"
  - "03-07 job and budget routes"
  - "03-08 worker reliability"
  - "03-09 embedding pipeline"
tech-stack:
  added: []
  patterns:
    - "Project-specific SQLSTATEs pass through PostgREST; HTTP mapping remains in api.errors."
key-files:
  created:
    - supabase/migrations/0010_budget_error_sqlstate.sql
  modified:
    - apps/api/src/api/errors.py
    - apps/api/tests/test_sources_router.py
    - apps/api/tests/conftest.py
    - supabase/tests/0009_pipeline_ops.sql
key-decisions:
  - "Budget refusal uses NW402, not 53400: PostgREST masks SQLSTATE class 53 as opaque 500, while NW402 cannot collide with a PostgreSQL-generated server-resource failure."
  - "HTTP 402 ownership remains at api.errors' single registration point."
requirements-completed: [ING-01, ING-02, ING-03, OPS-01]
actuals:
  tokens: 13700
  tasks: 3
  commits: 3
coverage:
  - id: D1
    description: "File, URL, and text source request boundaries, duplicate responses, and tenant isolation."
    requirement: ING-01
    verification:
      - kind: integration
        ref: "uv run pytest apps/api/tests/test_sources_router.py -q -rs"
        status: pass
    human_judgment: false
  - id: D2
    description: "Budget-capped enqueue returns an explicit 402 without deleting the stored source."
    requirement: OPS-01
    verification:
      - kind: integration
        ref: "uv run pytest apps/api/tests/test_sources_router.py -q -rs"
        status: pass
      - kind: other
        ref: "bash scripts/verify_pipeline_ops.sh"
        status: pass
    human_judgment: false
metrics:
  duration: "1h"
  completed: 2026-08-10
status: complete
---

# Phase 3 Plan 05: 파일·URL 수집 경계 Summary

파일·URL·텍스트 수집 경계와 원본 Storage 보존을 고정했고, 월 예산 상한이 이제 PostgREST를 지나도 사유 있는 `402 {"detail":"budget_exceeded"}`로 도달한다.

## Accomplishments

- 요청자 JWT를 쓰는 Storage 어댑터와 파일명·3세그먼트 경로 규약을 추가했다.
- 파일·URL 수집의 스트림 상한, MIME·URL 검증, 중복 표시, 원본 보존을 구현했다.
- `0010`이 비용 상한 SQLSTATE를 `NW402`로 바꾸고, API의 단일 오류 등록 지점이 이를 402로 렌더한다.
- 로컬 Supabase 왕복 회귀 30건을 포함한 전체 테스트 264건을 통과했다.

## Task Commits

1. **Task 1: UserStorage 어댑터와 경로·파일명 규약** — `5075a3e`
2. **Task 2: 파일·URL 인큐 엔드포인트와 상한 집행** — `5a20a52`
3. **Task 3: 경계·중복·격리 회귀 스위트 및 예산 거부 보정** — `316a9ac`

## Verification

- `supabase migration up --local` — 0010 적용 성공
- `bash scripts/verify_pipeline_ops.sh` — 성공
- `uv run pytest apps/api/tests/test_sources_router.py -q -rs` — 30 passed
- `uv run pytest -q` — 264 passed
- `uv run ruff check apps packages` · `bash scripts/ci_check_service_usage.sh` · `uv run pre-commit run --all-files` — 성공
- `supabase db push` — 연결된 클라우드 DB에 `0010_budget_error_sqlstate.sql` 적용 성공

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PostgREST가 비용 상한 SQLSTATE 53400을 opaque 500으로 마스킹했다.**

- **Issue:** 실제 상한 초과 요청이 `sqlstate=None`, `{"detail":"database_error"}`, HTTP 500으로 돌아왔다.
- **Fix:** 0010에서 `enqueue_source_job`의 거부 코드를 프로젝트 전용 `NW402`로 바꾸고 API 매핑 상수를 함께 변경했다.
- **Why safe:** PostgreSQL이 생성할 수 없는 코드라 실제 DB 자원 오류를 예산 초과로 오인할 수 없다.
- **Verification:** 로컬 RPC 계약 및 API의 텍스트·파일 상한 회귀가 모두 402를 확인했다.

## User Setup Required

None.

## Next Phase Readiness

03-06은 파일 추출과 URL 페치 경로를 이어갈 수 있다. 비용 상한 거부는 클라우드에도 0010으로 적용됐다.
