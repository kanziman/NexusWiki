---
phase: 01-bootstrap-and-ground-truth
plan: 04
subsystem: auth
tags: [supabase, gotrue, password-policy, email-confirmation, security-testing]
requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: linked Supabase Cloud project with migrations 0001 through 0006
provides:
  - Local and cloud Auth policy requiring passwords of at least 12 characters
  - Local and cloud email confirmation enforcement
  - Repeatable HTTP regression proof with guaranteed test-user cleanup
affects: [api-auth, dashboard-auth, deployment, phase-02]
actuals:
  tokens: 2400
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [production Auth policy parity, sanitized HTTP security probes, trap-based cloud fixture cleanup]
key-files:
  created: [docs/ops/auth-hardening-record.md, scripts/verify_auth_hardening.sh]
  modified: [supabase/config.toml]
key-decisions:
  - "Auth 하드닝은 로컬 config.toml과 Supabase Cloud에 각각 적용하고 실제 Cloud HTTP 동작으로 판정한다."
  - "검증 계정은 성공·실패 경로 모두에서 trap으로 삭제하며 Railway 런타임에서는 스크립트를 실행하지 않는다."
patterns-established:
  - "Auth policy evidence records only status/error codes and masked email addresses."
  - "Cloud security probes clean created principals before returning on every path."
requirements-completed: [BOOT-10]
coverage:
  - id: D1
    description: "정책 적용 직전 로컬·클라우드 auth.users가 모두 0행임을 기록했다."
    requirement: BOOT-10
    verification:
      - kind: integration
        ref: "supabase db query --linked and docker psql count(auth.users)"
        status: pass
    human_judgment: false
  - id: D2
    description: "로컬과 클라우드에 최소 12자 및 이메일 확인 필수 정책을 적용했다."
    requirement: BOOT-10
    verification:
      - kind: integration
        ref: "supabase config push; supabase start; cloud signup behavior"
        status: pass
    human_judgment: false
  - id: D3
    description: "실제 Cloud HTTP 호출로 약한 비밀번호와 미확인 이메일 로그인을 거부하고 테스트 계정을 정리한다."
    requirement: BOOT-10
    verification:
      - kind: e2e
        ref: "bash scripts/verify_auth_hardening.sh"
        status: pass
      - kind: integration
        ref: "supabase db query --linked: auth.users count = 0 after probe"
        status: pass
    human_judgment: false
duration: 3h 17m
completed: 2026-08-05
status: complete
---

# Phase 01 Plan 04: Supabase Auth 하드닝 Summary

**Supabase Auth가 로컬·클라우드 모두 최소 12자와 이메일 확인을 강제하며, 실제 HTTP 거부와 계정 정리를 재실행 가능한 스크립트로 증명한다.**

## Performance

- **Duration:** 3h 17m (호스팅 이메일 제한 대기 포함)
- **Started:** 2026-08-05T12:28:50+09:00
- **Completed:** 2026-08-05T15:45:22+09:00
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- 정책 적용 직전 클라우드와 로컬의 `auth.users`가 모두 0행임을 기록했다.
- 로컬 `config.toml`과 Supabase Cloud에 최소 12자·이메일 확인 필수를 함께 적용했다.
- 실제 HTTP 호출에서 6자 가입 `422 weak_password`, 미확인 로그인 `400 email_not_confirmed`를 확인하고 생성 계정 1개를 삭제했다.

## Task Commits

1. **Task 1: 적용 시점 `auth.users` 행 수 확인 및 기록** — `ad11243`
2. **Task 2: 최소 12자 · 이메일 확인 필수를 로컬과 클라우드에 적용** — `fb3ac91`
3. **Task 3: 실제 HTTP 호출로 두 거부 증명** — `3bafa7a`

## Files Created/Modified

- `docs/ops/auth-hardening-record.md` — 적용 전 계정 수, 정책 before/after, HTTP 관측값을 시크릿 없이 기록한다.
- `scripts/verify_auth_hardening.sh` — 클라우드 Auth 거부 세 단언과 실패 경로 계정 정리를 자동화한다.
- `supabase/config.toml` — 로컬 Auth 최소 길이와 이메일 확인 정책을 강화한다.

## Decisions Made

- 로컬 설정 파일은 프로덕션 정책의 증거가 아니므로 클라우드 설정과 실제 클라우드 HTTP 동작을 별도로 검증했다.
- Admin 권한을 쓰는 정리 경로는 개발자 머신 전용으로 제한하고 Railway `api` 서비스에는 secret key를 제공하지 않는다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CLI 전체 Auth 동기화가 범위 밖 원격 값을 변경**

- **Found during:** Task 2
- **Issue:** `supabase config push`가 목표 두 값 외에 site URL, redirect, MFA, OTP 값을 로컬 기본값으로 동기화했다.
- **Fix:** CLI diff에 표시된 적용 전 원격 값을 즉시 복원하고 목표인 `12`와 `true`만 유지했다.
- **Files modified:** `supabase/config.toml`, `docs/ops/auth-hardening-record.md`
- **Verification:** 복원 push diff와 이후 Cloud Auth HTTP 동작을 확인했다.
- **Committed in:** `fb3ac91`

**2. [Rule 3 - Blocking] Hosted Email rolling-hour 제한**

- **Found during:** Task 3
- **Issue:** 확인 메일 제한으로 12자 가입 요청이 일시적으로 `429 over_email_send_rate_limit`을 반환했다.
- **Fix:** 테스트 계정이 0행임을 확인하고 제한 창이 지난 뒤 한 번만 재시도했다.
- **Files modified:** 없음
- **Verification:** 재시도에서 `200` 확인 대기 상태, `400 email_not_confirmed`, 삭제 후 0행을 확인했다.
- **Committed in:** `3bafa7a`

**Total deviations:** 2 auto-fixed (1 bug, 1 blocker). **Impact:** 목표 정책 외 클라우드 설정은 원복됐고 최종 보안 동작과 정리 상태에는 영향이 없다.

## Issues Encountered

- Supabase Hosted Email 제한 때문에 Task 3 검증을 rolling-hour 창 이후 재개했다. 추가 반복 요청 없이 첫 재시도에서 통과했다.

## User Setup Required

완료됨. Supabase CLI 로그인, 로컬 `.env.local`의 세 키, 클라우드 Auth 정책이 준비돼 있다. 비밀값은 저장소에 기록하지 않았다.

## Next Phase Readiness

- API와 dashboard 인증 구현은 최소 12자·확인된 이메일이라는 전제 위에서 진행할 수 있다.
- `scripts/verify_auth_hardening.sh`는 개발자 머신 전용이며 연속 실행 시 Hosted Email 제한을 고려해야 한다.

## Self-Check: PASSED

세 task의 수용 기준과 plan-level 검증을 통과했으며, 최종 클라우드 `auth.users` 행 수는 `0`이다.

---
*Phase: 01-bootstrap-and-ground-truth*
*Completed: 2026-08-05*
