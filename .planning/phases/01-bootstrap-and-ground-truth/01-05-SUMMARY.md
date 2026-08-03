---
phase: 01-bootstrap-and-ground-truth
plan: 05
subsystem: ui
tags: [nextjs, react, tailwindcss, typescript, vitest, testing-library]

requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: uv 워크스페이스와 공통 bootstrap 기반
provides:
  - 독립 pnpm 패키지인 Next.js 15.5.22 대시보드 셸
  - Tailwind 4 CSS-first 및 TypeScript strict 설정
  - 클라이언트 컴포넌트와 순수 함수에 대한 Vitest 2건
  - 로컬 dev 서버 기동 및 프로세스 그룹 정리 스모크 검사
affects: [phase-06-ui, pre-commit, dashboard]

actuals:
  tokens: 43891
  tasks: 3
  commits: 2

tech-stack:
  added: [next@15.5.22, react@19.2.8, tailwindcss@4.3.3, typescript@5.9.3, vitest@4.1.10, testing-library]
  patterns: [standalone-pnpm-package, css-first-tailwind, tests-only-vitest, telemetry-disabled-scripts]

key-files:
  created:
    - apps/dashboard/package.json
    - apps/dashboard/pnpm-lock.yaml
    - apps/dashboard/app/page.tsx
    - apps/dashboard/components/HealthBadge.tsx
    - apps/dashboard/lib/workspace-path.ts
    - apps/dashboard/vitest.config.ts
    - scripts/smoke_dashboard.sh
  modified: []

key-decisions:
  - "Next.js 15.5.22를 범위 없이 고정하고 package.json 및 lockfile 양쪽을 비교한다."
  - "Vitest 대상은 tests/ 아래 순수 함수와 클라이언트 컴포넌트로 한정한다."

patterns-established:
  - "Dashboard package: apps/dashboard는 루트 JS workspace 없이 자체 package.json과 lockfile을 소유한다."
  - "RSC testing boundary: async Server Component는 Phase 6 Playwright가 담당한다."

requirements-completed: [BOOT-07]

coverage:
  - id: D1
    description: "Next.js 15.5.22, Tailwind 4 CSS-first, TypeScript strict 대시보드가 빌드된다."
    requirement: BOOT-07
    verification:
      - kind: integration
        ref: "pnpm --dir apps/dashboard exec tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 pnpm --dir apps/dashboard build"
        status: pass
    human_judgment: false
  - id: D2
    description: "순수 함수와 클라이언트 컴포넌트 테스트가 정확히 2건 통과한다."
    requirement: BOOT-07
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/*.test.{ts,tsx} — pnpm --dir apps/dashboard exec vitest run"
        status: pass
    human_judgment: false
  - id: D3
    description: "로컬 dev 서버가 200을 반환한 뒤 자식 워커까지 종료된다."
    requirement: BOOT-07
    verification:
      - kind: integration
        ref: "bash scripts/smoke_dashboard.sh; subsequent curl to port 3000 fails"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-08-03
status: complete
---

# Phase 01 Plan 05: Dashboard Bootstrap Summary

**Next.js 15.5.22 대시보드가 Tailwind 4 CSS-first, strict TypeScript, 정확히 2건의 Vitest와 재현 가능한 dev 스모크 경로를 갖췄다.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-03T09:34:00Z
- **Completed:** 2026-08-03T09:47:41Z
- **Tasks:** 3
- **Files modified:** 16

## Accomplishments

- CVE 하한을 넘는 Next.js 15.5.22와 React 19.2.8을 정확한 버전으로 고정하고 독립 lockfile을 커밋했다.
- Tailwind 4 CSS-first, TypeScript strict, 텔레메트리 비활성화 스크립트를 갖춘 App Router 셸을 만들었다.
- `workspacePath`와 `HealthBadge`의 정상 및 엣지 동작을 정확히 2개 테스트로 검증했다.
- dev 서버가 200을 반환한 뒤 프로세스 그룹 전체가 종료됨을 자동 검증했다.

## Task Commits

1. **Task 1: npm 패키지 정당성 확인** — 사용자 승인 공급망 게이트, 코드 커밋 없음
2. **Task 2: Next.js 15.5.22 · Tailwind 4 · TS strict 스캐폴딩** — `2572461` (feat)
3. **Task 3: Vitest + Testing Library 테스트 2건** — `6c9f2ac` (test)

## Files Created/Modified

- `apps/dashboard/package.json` — 고정된 런타임/개발 의존성과 build/test 스크립트
- `apps/dashboard/pnpm-lock.yaml` — 독립 pnpm 해소 결과
- `apps/dashboard/app/` — 한국어 App Router 최소 셸과 Tailwind 진입점
- `apps/dashboard/components/HealthBadge.tsx` — 상태 라벨을 제공하는 클라이언트 컴포넌트
- `apps/dashboard/lib/workspace-path.ts` — `/w/{workspaceId}` 경로 계약
- `apps/dashboard/vitest.config.ts` — tests 전용 jsdom Vitest 구성
- `apps/dashboard/tests/` — 순수 함수 및 클라이언트 컴포넌트 테스트
- `scripts/smoke_dashboard.sh` — dev 서버 기동, HTTP 200 폴링, 프로세스 그룹 정리

## Decisions Made

- 루트 `package.json`이나 pnpm workspace 없이 `apps/dashboard`가 자체 패키지와 lockfile을 소유한다.
- 테스트 검색 범위를 `tests/**/*.test.{ts,tsx}`로 고정해 async RSC가 우연히 포함되지 않게 했다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] dev 서버 자식 프로세스 정리 보강**
- **Found during:** Task 2
- **Issue:** 일반 background job의 PID가 프로세스 그룹 ID와 달라 Next 자식 워커 종료 후 `wait`가 멈출 수 있었다.
- **Fix:** Bash job control로 background job을 독립 프로세스 그룹으로 만든 뒤 그룹 전체를 종료했다.
- **Files modified:** `scripts/smoke_dashboard.sh`
- **Verification:** 스모크 성공 직후 포트 3000 curl 실패
- **Committed in:** `2572461`

---

**Total deviations:** 1 auto-fixed (1 missing critical). **Impact:** 스모크 검사와 로컬 프로세스 정리의 결정성을 높였으며 범위 확장은 없다.

## Issues Encountered

- pnpm 11의 공급망 정책이 `sharp`와 `unrs-resolver` build script를 최초 설치에서 차단했다. 승인된 설치 구간에서 build를 허용해 로컬 store를 구성했으며 이후 `--frozen-lockfile` 검증은 통과했다.
- Vitest가 향후 native config loader와 `vite-tsconfig-paths` 중복 가능성 경고를 출력하지만 현재 테스트와 타입 검사는 정상이다.

## TDD Gate Compliance

- Task 3의 RED 커밋은 만들 수 없었다. Plan Task 2가 `workspacePath`와 `HealthBadge` 동작을 먼저 구현하도록 명시해 Task 3 테스트는 최초 실행부터 통과했다.
- 테스트는 공개 동작과 엣지를 검증하며 정확히 2건으로 유지했다. 이 계획 구조상의 예외 외에 테스트 실패나 누락은 없다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 UI가 `/w/{workspaceId}` 경로, `HealthBadge`, Tailwind 진입점 위에서 확장할 수 있다.
- 계획 01-07의 local prettier hook이 사용할 `apps/dashboard`의 Prettier 실행 파일이 준비됐다.

## Self-Check: PASSED

- key-files.created 전부 존재
- Task 커밋 2건 존재
- Next 하한 비교, frozen install, tsc, Vitest 2건, production build, dev smoke 및 종료 검증 통과

---
*Phase: 01-bootstrap-and-ground-truth*
*Completed: 2026-08-03*
