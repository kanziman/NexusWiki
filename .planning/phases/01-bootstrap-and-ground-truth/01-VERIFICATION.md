---
phase: 01-bootstrap-and-ground-truth
verified: 2026-08-05T07:08:00Z
status: gaps_found
score: 14/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "구조화 로그가 사용자 이메일, Authorization/JWT, API 키, 소스 원문을 어떤 중첩 payload에서도 평문으로 출력하지 않는다"
    status: failed
    reason: "공용 redactor가 mapping 안의 list/tuple을 순회하지 않아 배열 내부의 민감 키 값이 그대로 렌더링된다. 직접 회귀 프로브가 exit 1로 실패했다."
    artifacts:
      - path: "packages/core/src/nexuswiki_core/logging.py"
        issue: "_redact_mapping()은 MutableMapping만 재귀 처리하고 sequence element는 처리하지 않는다."
      - path: "packages/core/tests/test_logging_redaction.py"
        issue: "중첩 mapping만 검사하며 list/tuple 또는 다중 sequence 회귀 테스트가 없다."
    missing:
      - "mapping과 list/tuple element를 모두 재귀 순회하는 value redactor"
      - "list of mappings 및 다중 sequence nesting에 대한 회귀 테스트"
---

# Phase 1: Bootstrap and Ground Truth Verification Report

**Phase Goal:** 나중에 바꿀 수 없거나 매주 비싸지는 결정이 전부 확정되고, `api`와 `worker` 두 서비스가 클라우드에서 실제로 기동한다
**Verified:** 2026-08-05T07:08:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

ROADMAP 성공 기준과 8개 PLAN의 중복 must-have를 요구사항 단위의 관측 가능한 진실로 합쳤다. SUMMARY의 합격 주장은 판정 근거로 사용하지 않았고, 코드·테스트·live read-only probe와 재실행 가능한 운영 기록을 대조했다.

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Singapore Supabase에 `0001`~`0006`이 순서대로 적용되고 `sources` private bucket 및 3개 정책이 존재한다 | ✓ VERIFIED | `supabase migration list --linked`가 local/remote `0001`~`0006` 일치를 반환했다. `0005_storage.sql`은 private bucket과 select/insert/delete 정책을 실체화한다. |
| 2 | Storage 경로는 정확히 UUID/UUID/filename이며 비멤버·2-segment·잘못된 UUID가 정책으로 거부된다 | ✓ VERIFIED | `bash scripts/verify_storage_policies.sh`를 직접 실행해 정상 insert와 세 거부 케이스가 모두 통과(`storage_policies: ok`, exit 0). |
| 3 | Supabase CLI와 cloud bootstrap 선택은 최초 push에 안전한 상태다 | ✓ VERIFIED | CLI `2.111.0`; cloud record에 push 전 빈 ledger/public schema와 `ap-southeast-1`, 신규 키 접두 판정이 있으며 live linked ledger가 현재 6개 순서를 확인한다. |
| 4 | 루트 uv workspace 한 번의 frozen sync로 API, worker, core가 동일 lockfile에서 import된다 | ✓ VERIFIED | `[tool.uv.workspace]` 3 members, 각 앱의 workspace dependency, committed `uv.lock`; `uv sync --frozen` exit 0과 세 package import 성공. |
| 5 | API는 lifespan으로 기동하며 `/health` 200, `/health/ready` bounded roundtrip을 제공한다 | ✓ VERIFIED | `FastAPI(lifespan=...)`, shared 2-second `httpx` timeout; `bash scripts/smoke_tracer.sh` exit 0; live Railway `/health` 200 및 `/health/ready` 200. |
| 6 | API와 worker는 공용 structlog 모듈을 쓰며 `job_id`/`workspace_id` context가 JSON에 실린다 | ✓ VERIFIED | 양 엔트리포인트가 `nexuswiki_core.logging`을 import; `test_bound_job_context_is_rendered_as_json` 포함 core/API suite 7 tests pass; smoke tracer pass. |
| 7 | 구조화 로그는 민감 값을 중첩 payload에서도 평문으로 출력하지 않는다 | ✗ FAILED | 직접 입력 `{"payloads":[{"authorization":"Bearer real-secret"}]}` 및 nested list email이 그대로 남아 assertion 실패(exit 1). Plan 01-01의 test-tier prohibition과 직접 충돌한다. |
| 8 | worker는 Python PID 1 경계에서 SIGTERM에 정상 종료한다 | ✓ VERIFIED | exec-form module entrypoint와 signal handlers 존재; source smoke tracer가 종료 코드와 제한시간을 검증해 exit 0. |
| 9 | ruff/prettier pre-commit, `.editorconfig`, README의 범위가 동작한다 | ✓ VERIFIED | `uv run pre-commit run --all-files`에서 ruff check/format/prettier 전부 pass; config 범위는 Python apps/packages와 dashboard만 대상으로 한다. |
| 10 | Next.js 15.5.22+, Tailwind 4 CSS-first, strict TS, 정확히 2개 Vitest가 동작한다 | ✓ VERIFIED | declared/resolved Next `15.5.22`; `tsc --noEmit` exit 0; Vitest 2 files/2 tests pass; PostCSS Tailwind plugin + `@import "tailwindcss"`, 별도 Tailwind config 없음. |
| 11 | Railway Singapore의 API/worker가 단일 Dockerfile과 동일 source/runtime 판정으로 실행된다 | ✓ VERIFIED | 단일 runtime Dockerfile/`railway.json`; deployment record는 두 서비스 `asia-southeast1`, 동일 commit/Dockerfile/runtime SHA 및 service별 start command를 특정 deployment IDs에 묶는다. Live API는 최신 SHA와 200을 반환했다. |
| 12 | API에는 secret service key가 없고 worker에만 service-scoped로 배치된다 | ✓ VERIFIED | runtime source에는 API secret setting이 없고 deployment record의 변수-name inspection이 API 부재/worker 전용/공유 그룹 부재를 기록한다. 값은 기록되지 않았다. |
| 13 | 프로덕션과 로컬 Auth가 최소 12자·email confirmation으로 hardening된다 | ✓ VERIFIED | local config는 `minimum_password_length = 12`, email confirmation true; cloud HTTP record는 6-char signup 422 `weak_password`, unconfirmed login 400 `email_not_confirmed`, cleanup 후 users=0을 기록한다. 검증 스크립트가 동일 판정을 구현한다. |
| 14 | Railway↔Supabase deployed RTT에 cold, warmup, N≥50, p50/p95, ×5가 기록된다 | ✓ VERIFIED | worker probe는 readiness와 같은 PostgREST request, 5 warmups, 50 samples, nearest-rank percentile을 구현하고 targeted worker tests 5/5 pass; baseline은 cold 851.138ms, p50 29.093ms, p95 37.610ms, N=50, ×5를 기록한다. |
| 15 | cloud readiness와 bootstrap ledger의 open question이 닫힌다 | ✓ VERIFIED | live `/health/ready` 200; `checklists.json`과 RTT baseline은 open question #2 해소 및 measured baseline을 연결한다. |

**Score:** 14/15 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact group | Expected | Status | Details |
| --- | --- | --- | --- |
| Python workspace | root/member `pyproject.toml`, `uv.lock`, API/worker/core code | ✓ EXISTS + SUBSTANTIVE + WIRED | frozen sync/imports and runnable smoke verified |
| Logging | shared configuration, context binding, redaction tests | ✗ SUBSTANTIVE BUT SECURITY-INCOMPLETE | shared wiring works; sequence recursion missing |
| Storage | migration, SQL policy test, shell probe | ✓ EXISTS + SUBSTANTIVE + WIRED | direct local policy probe passed |
| Dashboard | package lock/config/app/component/tests/smoke | ✓ EXISTS + SUBSTANTIVE + WIRED | TS and two Vitest checks passed |
| Deployment | Dockerfile, railway config, deploy record | ✓ EXISTS + SUBSTANTIVE + WIRED | live health/readiness plus recorded deployment IDs |
| Auth | local config, verification script, cloud record | ✓ EXISTS + SUBSTANTIVE + WIRED | local values and cloud rejection evidence align |
| RTT | worker probe/tests/baseline | ✓ EXISTS + SUBSTANTIVE + WIRED | entrypoint invokes probe; tests and measured record align |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| API + worker | core logging | direct imports/configure at process startup | ✓ WIRED | both share processor chain and context helpers |
| logging processor | nested secret payload | `_redact_mapping` recursion | ✗ NOT WIRED | recursion stops at sequences; direct exploit-shaped probe fails |
| API readiness | Supabase PostgREST | shared bounded `httpx` client | ✓ WIRED | live readiness 200 |
| worker startup | RTT measurement | `measure_rtt()` invocation | ✓ WIRED | configuration-gated startup call and structured result event |
| migration 0005 | existing membership helpers | policy predicates | ✓ WIRED | `is_workspace_member` / `has_workspace_role`; policy probe pass |
| pre-commit | local formatters | scoped hook commands | ✓ WIRED | all hooks pass on all files |
| Railway services | root container | single Dockerfile + service start commands | ✓ WIRED | code configuration and deployment record agree |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `/health/ready` | DB readiness + elapsed time | live PostgREST request | Yes | ✓ FLOWING |
| worker RTT log | cold/p50/p95/sample/failures | deployed PostgREST requests | Yes | ✓ FLOWING |
| dashboard health badge | status prop | static scaffold/test input | Scaffold intent; no Phase 1 API fetch required | ✓ VERIFIED FOR PHASE SCOPE |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Python default suite | `uv run pytest -q` | 7 passed | ✓ PASS |
| Worker RTT suite | `uv run pytest apps/worker/tests/test_rtt.py -q` | 5 passed | ✓ PASS |
| Dashboard behavior | `pnpm --dir apps/dashboard test -- --run` | 2 tests passed | ✓ PASS |
| TypeScript strict | `pnpm --dir apps/dashboard exec tsc --noEmit` | exit 0 | ✓ PASS |
| Commit gate | `uv run pre-commit run --all-files` | 3 hooks passed | ✓ PASS |
| API/worker lifecycle | `bash scripts/smoke_tracer.sh` | `smoke_tracer: ok` | ✓ PASS |
| Live API | `curl` public `/health`, `/health/ready` | 200 / 200 | ✓ PASS |
| Nested sequence redaction | direct `redact_sensitive()` assertions | leaked authorization/email; exit 1 | ✗ FAIL |

### Probe Execution

| Probe | Command | Result | Status |
| --- | --- | --- | --- |
| Storage policy | `bash scripts/verify_storage_policies.sh` | `storage_policies: ok` | PASS |
| Tracer | `bash scripts/smoke_tracer.sh` | `smoke_tracer: ok` | PASS |

Auth hardening was not replayed because the strong-password branch creates/deletes a real cloud user. Its implementation and dated cloud evidence were inspected without introducing new external mutations.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence / Blocking issue |
| --- | --- | --- | --- |
| BOOT-01 | 01-02 | ✓ SATISFIED | migration plus direct cross-workspace/path policy probe |
| BOOT-02 | 01-03 | ✓ SATISFIED | Singapore/new-key cloud record and live linked project evidence |
| BOOT-03 | 01-02 | ✓ SATISFIED | CLI 2.111.0 and ordered linked ledger |
| BOOT-04 | 01-01 | ✓ SATISFIED | workspace config, lock, frozen sync/imports |
| BOOT-05 | 01-07 | ✓ SATISFIED | all pre-commit hooks pass; docs/config exist |
| BOOT-06 | 01-01 | ✗ BLOCKED | health/context logging work, but explicit sensitive-log prohibition fails for sequence-nested values |
| BOOT-07 | 01-05 | ✓ SATISFIED | Next/Tailwind/strict TS/Vitest verified |
| BOOT-08 | 01-06 | ✓ SATISFIED | single Dockerfile and paired Singapore deployments; live health 200 |
| BOOT-09 | 01-08 | ✓ SATISFIED | deployed measured RTT baseline and probe tests |
| BOOT-10 | 01-04 | ✓ SATISFIED | local config and recorded cloud rejection checks |

**Coverage:** 9/10 requirements satisfied; no orphaned Phase 1 requirement IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `packages/core/src/nexuswiki_core/logging.py` | 37-43 | sequence containers bypass recursive redaction | 🛑 Blocker | credentials/content may reach production structured logs |
| `pyproject.toml` | 20-22 | default pytest omits worker tests | ⚠️ Warning | RTT regressions can pass the default Python gate |
| `apps/dashboard/package.json` | 10 | `eslint .` without ESLint 9 flat config | ⚠️ Warning | declared lint command exits 2 before linting |
| `Dockerfile` | 6 | mutable `uv:latest` builder input | ⚠️ Warning | clean builds are not byte/reviewer reproducible |
| `scripts/smoke_tracer.sh` | 15-18 | fixed container names and unconditional cleanup | ⚠️ Warning | concurrent/unrelated container collision risk |
| `apps/dashboard/lib/workspace-path.ts` | 1-6 | workspace segment not encoded/validated | ⚠️ Warning | malformed external IDs can alter route/query/fragment |

No unreferenced `TBD`/`FIXME`/`XXX` blocker markers were found in phase source artifacts.

### Human Verification Required

The plans contained deferred dashboard checks for Railway service state/variable scoping, Supabase Auth dashboard settings, and deployment-specific RTT logs. Their recorded outcomes are consistent with live health/migration probes and the implementation, but external dashboard state cannot be fully reconstructed from repository code. These do not change the current result because the deterministic redaction failure already sets the stricter `gaps_found` status.

## Gaps Summary

### Critical Gap

1. **Sequence-nested sensitive data is not redacted**
   - `redact_sensitive()` protects direct and mapping-nested keys but not mappings inside lists/tuples.
   - This is not merely the review's generic quality concern: it violates Plan 01-01's explicit test-tier prohibition and weakens BOOT-06's production logging boundary.
   - Fix by introducing a recursive value walker for mappings and sequences and add regression tests for one-level and multi-level sequence nesting.

### Recommended Fix Plan

**01-09-PLAN.md: Recursive logging redaction gap closure**

1. Add fail-first tests for list/tuple nested mappings and multiple sequence levels.
2. Implement recursive mapping/sequence redaction while preserving safe scalar values and container semantics.
3. Run the focused logging tests, default workspace suite, ruff, and tracer smoke.

**Estimated scope:** Small

---

_Verified: 2026-08-05T07:08:00Z_
_Verifier: the agent (gsd-verifier)_
