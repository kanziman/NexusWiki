---
phase: 01-bootstrap-and-ground-truth
plan: 08
subsystem: operations
tags: [railway, supabase, rtt, httpx, observability]
requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: Supabase Cloud schema and Railway api/worker deployment
provides:
  - deployed worker startup RTT probe with cold, p50, and p95 measurements
  - secret-free Singapore Railway-to-Supabase latency baseline
  - closed bootstrap task ledger and region-pairing open question
affects: [phase-04-search, OPS-05, deployment-observability]
actuals:
  tokens: 4600
  tasks: 3
  commits: 3
task-commits: [aaa5b65, 53d246a, 6ff06e8]
tech-stack:
  added: []
  patterns: [startup-one-shot-probe, nearest-rank-percentile, deployment-id-evidence]
key-files:
  created:
    - apps/worker/src/worker/rtt.py
    - apps/worker/tests/test_rtt.py
    - docs/ops/rtt-baseline.md
  modified:
    - apps/worker/src/worker/__main__.py
    - checklists.json
key-decisions:
  - "콜드 요청을 본 표본에서 분리하고 워밍업 5회 뒤 성공 표본 50회의 최근접 순위 p50/p95를 기록한다."
  - "SPEC의 라우터 경계를 지키기 위해 배포된 worker 기동 경로에서 측정하고 D-14 편차를 공개한다."
patterns-established:
  - "Deployment evidence: 새 커밋의 특정 deployment ID가 SUCCESS인 경우에만 그 배포 로그를 근거로 사용한다."
  - "RTT probe: 개별 HTTP 실패는 집계하되 worker 기동과 상주 상태를 막지 않는다."
requirements-completed: [BOOT-09]
coverage:
  - id: D1
    description: "worker가 콜드 요청과 워밍업을 분리해 N=50의 p50/p95를 산출한다."
    requirement: BOOT-09
    verification:
      - kind: unit
        ref: "uv run pytest apps/worker/tests/test_rtt.py -q — 5 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "배포된 Railway worker에서 Singapore Supabase RTT가 실제 측정된다."
    requirement: BOOT-09
    verification:
      - kind: e2e
        ref: "Railway worker deployment d3e07a8a-2f04-4098-9e3e-80de355b43be log worker.rtt_measured"
        status: pass
    human_judgment: false
  - id: D3
    description: "시크릿 없는 RTT 기준선과 갱신된 태스크 원장이 존재한다."
    requirement: BOOT-09
    verification:
      - kind: integration
        ref: "negative secret grep and checklists.json Node acceptance commands"
        status: pass
    human_judgment: false
duration: 15 min
completed: 2026-08-05
status: complete
---

# Phase 01 Plan 08: 배포 RTT 기준선 Summary

**Railway Singapore에서 Supabase Singapore로 향하는 배포 worker 왕복을 실측해 p50 29.093 ms, p95 37.610 ms 기준선과 5채널 환산치를 확정했다.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-05T06:37:00Z
- **Completed:** 2026-08-05T06:52:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- readiness와 같은 PostgREST 요청을 콜드 1회, 워밍업 5회, 본 표본 50회 순서로 측정한다.
- worker deployment `d3e07a8a-2f04-4098-9e3e-80de355b43be`에서 콜드 851.138 ms, p50 29.093 ms, p95 37.610 ms, 실패 0을 관측했다.
- p50 ×5 145.467 ms와 p95 ×5 188.048 ms를 시크릿 없는 운영 문서에 기록했다.
- `checklists.json` open question #2를 해소하고 Phase 1 부트스트랩·Storage 태스크 6건의 검증 결과를 반영했다.

## Task Commits

1. **Task 1: worker 기동 RTT 프로브** — `aaa5b65` (feat)
2. **Task 2: RTT 운영 기준선 기록** — `53d246a` (docs)
3. **Task 3: 태스크 원장 및 open question 갱신** — `6ff06e8` (docs)

## Files Created/Modified

- `apps/worker/src/worker/rtt.py` — 실패 허용 one-shot RTT 측정과 최근접 순위 백분위
- `apps/worker/src/worker/__main__.py` — 기동 프로브 실행과 구조화 이벤트
- `apps/worker/tests/test_rtt.py` — 실제 네트워크 없는 결정적 테스트 5건
- `docs/ops/rtt-baseline.md` — 배포 측정값, 방법, ×5 환산 및 Phase 4 포인터
- `checklists.json` — open question 해소와 여섯 태스크의 기계 판정 결과

## Decisions Made

- 실패한 요청은 `failures`에 포함하되 성공 표본만 p50/p95에 사용한다. 성공 표본이 0이면 두 백분위는 null이다.
- 특정 신규 deployment ID의 로그만 증거로 사용해 재배포 이전 로그의 위양성을 차단했다.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Railway CLI가 PATH에 없어 로그인 세션을 그대로 사용하는 `npx @railway/cli`로 호출했다.
- 첫 전체 검증 명령에서 zsh 예약 변수 `status`를 사용해 셸 오류가 났으며, 변수명을 바꾸어 `/health/ready` HTTP 200을 재검증했다.

## Authentication Gates

- 기존 Railway CLI 로그인 세션을 사용했다. 토큰과 서비스 변수 값은 출력하거나 저장하지 않았다.

## User Setup Required

None — required Railway and Supabase configuration was already present.

## Next Phase Readiness

- Phase 4 OPS-05는 p50 29.093 ms, p95 37.610 ms와 ×5 환산치를 네트워크 기준선으로 사용할 수 있다.
- 배포된 `/health/ready`가 클라우드 migration 적용 후 HTTP 200을 반환한다.

## Self-Check: PASSED

- 생성 파일 3개와 수정 파일 2개 존재
- Task 커밋 3건 존재
- RTT 테스트 5건, 전체 pytest 7건, Ruff check/format 통과
- worker 신규 배포 SUCCESS 및 해당 배포 로그에서 표본 50개, 오류 0건 확인
- RTT 문서 negative secret grep 4종과 원장 acceptance command 전부 통과
- 배포된 api `/health/ready` HTTP 200

---
*Phase: 01-bootstrap-and-ground-truth*
*Completed: 2026-08-05*
