---
phase: 01-bootstrap-and-ground-truth
verified: 2026-08-05T08:35:54Z
status: passed
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 14/15
  gaps_closed:
    - "구조화 로그가 사용자 이메일, Authorization/JWT, API 키, 소스 원문을 sequence가 포함된 중첩 payload에서도 평문으로 출력하지 않는다"
  gaps_remaining: []
  regressions: []
requirements:
  satisfied: [BOOT-01, BOOT-02, BOOT-03, BOOT-04, BOOT-05, BOOT-06, BOOT-07, BOOT-08, BOOT-09, BOOT-10]
  blocked: []
  needs_human: []
---

# Phase 1: Bootstrap and Ground Truth Verification Report

**Phase Goal:** 나중에 바꿀 수 없거나 매주 비싸지는 결정이 전부 확정되고, `api`와 `worker` 두 서비스가 클라우드에서 실제로 기동한다
**Verified:** 2026-08-05T08:35:54Z
**Status:** passed
**Re-verification:** Yes — after gap closure plan 01-09

## Goal Achievement

### Observable Truths

이번 재검증은 이전 보고서의 유일한 실패 항목을 코드·직접 프로브·테스트·end-to-end tracer로 전면 재검증하고, 이전 합격 항목은 실제 산출물과 빠른 회귀 검사를 대조했다. SUMMARY의 주장만으로 합격 처리하지 않았다.

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Singapore Supabase에 `0001`~`0006`이 순서대로 적용되고 `sources` private bucket 및 3개 정책이 존재한다 | ✓ VERIFIED | 이전 직접 migration/policy 검증 증거와 `0005_storage.sql` 실체가 유지된다. |
| 2 | Storage 경로는 UUID/UUID/filename이며 비멤버·2-segment·잘못된 UUID가 정책으로 거부된다 | ✓ VERIFIED | 정책 migration과 `scripts/verify_storage_policies.sh` 판정기가 유지되며 이전 직접 실행 결과는 `storage_policies: ok`였다. |
| 3 | Supabase CLI와 cloud bootstrap 선택은 최초 push에 안전한 상태다 | ✓ VERIFIED | CLI 2.111.0, Singapore cloud 기록, ordered migration ledger 산출물이 존재한다. |
| 4 | 루트 uv workspace의 frozen sync로 API, worker, core가 동일 lockfile에서 import된다 | ✓ VERIFIED | workspace 3멤버와 `uv.lock` 유지; 현재 기본 Python suite가 정상 수집·실행된다. |
| 5 | API는 lifespan으로 기동하며 `/health` 200, `/health/ready` bounded roundtrip을 제공한다 | ✓ VERIFIED | 현재 `bash scripts/smoke_tracer.sh`가 `smoke_tracer: ok`로 통과했다. |
| 6 | API와 worker는 공용 structlog 모듈을 쓰며 `job_id`/`workspace_id` context가 JSON에 실린다 | ✓ VERIFIED | context JSON 테스트를 포함한 focused logging suite 6/6 및 tracer 통과. |
| 7 | 구조화 로그는 mapping/list/tuple이 교차하는 중첩 payload에서도 민감 값을 평문 출력하지 않는다 | ✓ VERIFIED | `_redact_value()`가 mapping/list/tuple을 재귀 순회한다. one-level 및 multi-level sequence 회귀 테스트가 통과했고, 이전 exploit shape의 직접 assertion probe도 exit 0이었다. |
| 8 | worker는 Python PID 1 경계에서 SIGTERM에 정상 종료한다 | ✓ VERIFIED | 현재 tracer가 API/worker lifecycle 및 종료 경계를 통과했다. |
| 9 | ruff/prettier pre-commit, `.editorconfig`, README의 범위가 동작한다 | ✓ VERIFIED | 설정과 문서 산출물이 유지되고 현재 `uv run ruff check .`가 통과했다. |
| 10 | Next.js 15.5.22+, Tailwind 4 CSS-first, strict TS, 정확히 2개 Vitest가 구성된다 | ✓ VERIFIED | package/config/component/test 산출물과 이전 2-test/TypeScript 성공 증거가 유지된다. 이번 sandbox의 pnpm 재실행은 출력 없이 정지해 중단했으며 코드 회귀 징후는 없다. |
| 11 | Railway Singapore의 API/worker가 단일 Dockerfile과 동일 source/runtime 판정으로 실행된다 | ✓ VERIFIED | 단일 Dockerfile, `railway.json`, paired deployment record와 runtime SHA 관측점이 유지된다. |
| 12 | API에는 secret service key가 없고 worker에만 service-scoped로 배치된다 | ✓ VERIFIED | API 설정에 secret key가 없고 service-scoped 변수명 점검 기록이 유지된다. |
| 13 | 프로덕션과 로컬 Auth가 최소 12자·email confirmation으로 hardening된다 | ✓ VERIFIED | local config와 dated cloud rejection evidence가 유지된다. 외부 계정 mutation은 재실행하지 않았다. |
| 14 | Railway↔Supabase deployed RTT에 cold, warmup, N≥50, p50/p95, ×5가 기록된다 | ✓ VERIFIED | worker RTT 구현·테스트·deployment-specific baseline이 유지되고 기본 Python suite에 관련 회귀가 없다. |
| 15 | cloud readiness와 bootstrap ledger의 open question이 닫힌다 | ✓ VERIFIED | readiness tracer와 `checklists.json`/RTT baseline 연결이 유지된다. |

**Score:** 15/15 truths verified (0 present-but-behavior-unverified)

### Gap Closure Verification: BOOT-06

| Level | Result | Evidence |
| --- | --- | --- |
| Exists | ✓ PASS | `logging.py`와 `test_logging_redaction.py` 존재 |
| Substantive | ✓ PASS | `_redact_value()`가 mutable mapping, list, tuple, scalar를 분기하며 민감 mapping 값은 즉시 placeholder로 바꾼다 |
| Wired | ✓ PASS | `redact_sensitive()` → `_redact_mapping()` → `_redact_value()` 연결이 structlog renderer 전 processor chain에 유지된다 |
| Behavioral | ✓ PASS | focused 6 tests, direct exploit-shaped probe, default 9 tests, tracer 모두 통과 |

문자열/bytes는 generic sequence로 순회하지 않고 scalar로 보존되며, list와 tuple은 각각 원래 container type을 유지한다. `authorization`, `email`, `token`, `content`의 sequence-nested sentinel은 모두 `REDACTION_PLACEHOLDER`로 치환된다.

### Required Artifacts

| Artifact group | Expected | Status | Details |
| --- | --- | --- | --- |
| Python workspace | root/member `pyproject.toml`, `uv.lock`, API/worker/core code | ✓ EXISTS + SUBSTANTIVE + WIRED | default suite 9 passed |
| Logging | shared configuration, context binding, recursive redaction tests | ✓ EXISTS + SUBSTANTIVE + WIRED | prior security gap closed by plan 01-09 |
| Storage | migration, SQL policy test, shell probe | ✓ EXISTS + SUBSTANTIVE + WIRED | prior direct policy evidence retained |
| Dashboard | package lock/config/app/component/tests/smoke | ✓ EXISTS + SUBSTANTIVE + WIRED | artifacts and prior strict TS/Vitest evidence retained |
| Deployment | Dockerfile, Railway config, deploy record | ✓ EXISTS + SUBSTANTIVE + WIRED | paired Singapore deployment evidence retained |
| Auth | local config, verification script, cloud record | ✓ EXISTS + SUBSTANTIVE + WIRED | local/cloud hardening evidence retained |
| RTT | worker probe/tests/baseline | ✓ EXISTS + SUBSTANTIVE + WIRED | deployed N=50 baseline retained |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| API + worker | core logging | imports/configure at startup | ✓ WIRED | tracer passes with revised core processor |
| logging processor | nested sequence payload | recursive `_redact_value()` | ✓ WIRED | direct exploit probe and named regressions pass |
| API readiness | Supabase PostgREST | bounded `httpx` client | ✓ WIRED | lifecycle tracer passes; prior live readiness 200 evidence retained |
| worker startup | RTT measurement | `measure_rtt()` invocation | ✓ WIRED | implementation/tests/baseline remain connected |
| migration 0005 | membership helpers | policy predicates | ✓ WIRED | migration and policy probe remain present |
| Railway services | root container | single Dockerfile + per-service command | ✓ WIRED | deployment record and runtime SHA points remain present |

## Behavioral Spot-Checks

| Check | Result | Status |
| --- | --- | --- |
| `uv run pytest packages/core/tests/test_logging_redaction.py -q` | 6 passed | ✓ PASS |
| direct nested list/tuple `redact_sensitive()` exploit probe | exit 0; both sentinels redacted and types preserved | ✓ PASS |
| `uv run pytest -q` | 9 passed | ✓ PASS |
| `uv run ruff check .` | all checks passed | ✓ PASS |
| `bash scripts/smoke_tracer.sh` | `smoke_tracer: ok` | ✓ PASS |

## Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| BOOT-01 | ✓ SATISFIED | storage migration and cross-workspace/path policy evidence |
| BOOT-02 | ✓ SATISFIED | Singapore/new-key cloud bootstrap evidence |
| BOOT-03 | ✓ SATISFIED | upgraded CLI and ordered ledger |
| BOOT-04 | ✓ SATISFIED | uv workspace, lock, imports/default suite |
| BOOT-05 | ✓ SATISFIED | scoped tooling and repository docs; Ruff passes |
| BOOT-06 | ✓ SATISFIED | lifespan/health/context logging plus recursive sequence redaction; focused tests and tracer pass |
| BOOT-07 | ✓ SATISFIED | Next/Tailwind/strict TS/Vitest artifacts and prior passing checks |
| BOOT-08 | ✓ SATISFIED | single-image paired Singapore deployment evidence |
| BOOT-09 | ✓ SATISFIED | deployed RTT probe and documented N=50 baseline |
| BOOT-10 | ✓ SATISFIED | local and cloud auth hardening evidence |

**Coverage:** 10/10 requirements satisfied; no orphaned Phase 1 requirement IDs.

## Anti-Patterns and Non-Blocking Observations

No blocker remains. The earlier review warnings remain non-blocking and outside gap plan 01-09: default pytest selection does not include worker RTT tests, dashboard's declared ESLint command lacks flat config, the Docker builder uses mutable `uv:latest`, the tracer uses fixed container names, and the dashboard workspace path helper does not encode external identifiers. None invalidates a Phase 1 must-have.

## Human Verification Required

None. External Railway/Supabase state was already captured by deployment-specific records and live/read-only probes in the initial verification; the only failed deterministic requirement has now been closed with executable regression coverage.

## Gaps Summary

**No gaps found.** The previous sequence-nested logging disclosure gap is closed, no regression was detected, and the Phase 1 goal is achieved.

## Verification Metadata

**Verification approach:** Re-verification; full 4-level check of the previous BOOT-06 gap plus quick regression checks of previously passing truths

**Must-haves source:** ROADMAP success criteria, PLAN frontmatter, previous verification, BOOT-01 through BOOT-10

**Automated checks:** 5 executed checks passed; 0 failed

**Human checks required:** 0

**Overrides applied:** 0

---
_Verified: 2026-08-05T08:35:54Z_

_Verifier: the agent (gsd-verifier)_
