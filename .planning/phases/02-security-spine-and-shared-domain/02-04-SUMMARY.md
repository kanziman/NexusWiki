---
phase: 02-security-spine-and-shared-domain
plan: 04
subsystem: backend
tags: [rls, tenant-isolation, fastapi, pytest, fail-first, postgrest, sec-06]

# Dependency graph
requires:
  - phase: 02-security-spine-and-shared-domain
    provides: "02-03의 UserDb.update_one / delete_one, api.errors의 단일 403 핸들러와 create_app의 등록 한 줄"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-02의 create_app(settings) 주입 지점과 ApiSettings(secret 필드 없음)"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-06의 0007 섹션 8 최소권한 매트릭스 — 이것 없이는 모든 실제 질의가 42501로 떨어진다"
provides:
  - "PATCH/DELETE /workspaces/{workspace_id} — 격리 증명 표면. 상태 코드 리터럴 0개, except 0개"
  - "WorkspaceUpdateRequest — extra=forbid, name 한 필드. 소유권 이전 경로를 422로 닫는다"
  - "apps/api/tests/conftest.py — 저장소 최초의 공유 픽스처. 테스트별 고유 사용자 2명 × 워크스페이스 2개"
  - "CROSS_TENANT_CASES — 새 라우터가 늘면 행만 추가하는 파라미터화 표 (D-14)"
  - "supabase/tests/0004_loosened_rls_violation.sql — 느슨하게/되돌리기 2개 섹션의 fail-first 픽스처"
  - "docs/ops/tenant-isolation-proof.md — 3단계 종료 코드 0/1/0 실측 기록"
  - "실측 사실: workspaces의 교차 테넌트 쓰기는 SELECT·UPDATE 두 정책이 각각 독립적으로 막는다"
affects: [02-07, 02-08, 02-09, phase-03, phase-07]

# Actuals (#2632)
actuals:
  tokens: 21500
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "격리 증명 표면: 제품 기능이 아니라 증명을 위해 존재하는 최소 라우터를 명시적으로 그렇게 선언한다"
    - "픽스처가 스스로를 검사한다: 이미 발급한 식별자를 다시 내주면 픽스처가 AssertionError로 죽어 실행 순서 의존을 red로 바꾼다"
    - "접속 정보를 env가 아니라 상수로 못 박고 루프백 가드를 건다 — 파괴적 픽스처가 원격을 가리킬 수 없게 만든다"
    - "fail-first는 red의 분포까지 본다: 무엇을 풀었는지와 무엇이 빨개졌는지가 대응하지 않으면 테스트가 다른 것에 반응하고 있다는 신호다"

key-files:
  created:
    - apps/api/src/api/routers/workspaces.py
    - apps/api/tests/test_workspaces_router.py
    - apps/api/tests/conftest.py
    - apps/api/tests/test_workspaces_isolation.py
    - supabase/tests/0004_loosened_rls_violation.sql
    - docs/ops/tenant-isolation-proof.md
  modified:
    - apps/api/src/api/main.py
    - checklists.json

key-decisions:
  - "자격증명 없는 요청은 FastAPI의 HTTPBearer가 401로 낸다 — 라우터에 상태 코드를 두지 않으면서도 미인증과 격리 위반이 다른 응답을 갖는 유일한 방법이다"
  - "conftest의 로컬 스택 접속 정보를 환경변수에서 읽지 않는다 — 저장소의 .env.local이 클라우드 자격증명을 담고 있어 env를 읽는 파괴적 픽스처는 운영 프로젝트에 사용자를 만들고 지운다"
  - "테스트 픽스처는 워크스페이스를 소유자 JWT로 만든다 — 0007 매트릭스가 service_role에 workspaces SELECT만 주며, 그 좁음은 결함이 아니라 정상이다"
  - "위반 픽스처는 SELECT 정책까지 함께 푼다 — UPDATE·DELETE만 풀면 격리가 유지되어 fail-first가 red를 만들지 못한다는 것을 실측했다"
  - "라우트 존재 확인을 app.routes가 아니라 OpenAPI 문서로 한다 — FastAPI 0.141의 include_router가 개별 APIRoute를 노출하지 않는다"

patterns-established:
  - "정상 경로 성공을 격리 테스트와 같은 표에 넣는다: 전부 거절하는 서버도 교차 케이스만 보면 통과하므로 소유자 성공 케이스가 없으면 증명이 반쪽이다"
  - "미인증 케이스를 별도로 분리해 Forbidden이 아님을 단언한다: 인증 실패가 격리 성공으로 위장되는 위양성을 구조적으로 막는다"
  - "복원은 '되돌리기를 실행했다'가 아니라 pg_policies 문자열 대조로 증명한다"

requirements-completed: [SEC-06]

coverage:
  - id: D1
    description: "교차 테넌트 CRUD 시도 전부가 HTTP 403을 받는다 (SEC-06, T-02-19)"
    requirement: SEC-06
    verification:
      - kind: integration
        ref: "apps/api/tests/test_workspaces_isolation.py#test_cross_tenant_write_is_forbidden[PATCH|DELETE]"
        status: pass
      - kind: integration
        ref: "apps/api/tests/test_workspaces_isolation.py#test_cross_tenant_write_is_forbidden_in_the_other_direction[PATCH|DELETE]"
        status: pass
    human_judgment: false
  - id: D2
    description: "존재하지 않는 리소스도 404가 아니라 403을 받는다 (D-12, T-02-20)"
    requirement: SEC-06
    verification:
      - kind: integration
        ref: "apps/api/tests/test_workspaces_isolation.py#test_absent_resource_is_forbidden_not_not_found[PATCH|DELETE]"
        status: pass
    human_judgment: false
  - id: D3
    description: "자기 워크스페이스 DELETE 재호출도 403이며 그것이 D-12의 귀결임이 문서에 명시된다"
    requirement: SEC-06
    verification:
      - kind: integration
        ref: "apps/api/tests/test_workspaces_isolation.py#test_second_delete_of_own_workspace_is_forbidden"
        status: pass
      - kind: integration
        ref: "docs/ops/tenant-isolation-proof.md §배경 표 3행 · §한계 2번째 항목"
        status: pass
    human_judgment: false
  - id: D4
    description: "격리 테스트가 실행 순서·병렬성에 무관하다 — 테스트별 고유 워크스페이스/사용자를 생성·정리한다 (T-02-25)"
    requirement: SEC-06
    verification:
      - kind: integration
        ref: "연속 2회 `pytest apps/api/tests/test_workspaces_isolation.py -q` 모두 exit 0, `-p no:randomly` 포함 3회"
        status: pass
      - kind: integration
        ref: "실행 후 `workspaces where name like 'test-%'` = 0, `auth.users where email like 'test-%@example.test'` = 0"
        status: pass
      - kind: unit
        ref: "apps/api/tests/conftest.py#_register — 재발급 식별자를 AssertionError로 막는다"
        status: pass
    human_judgment: false
  - id: D5
    description: "라우터 모듈에 Forbidden 상태 코드 리터럴이 없다 (SEC-04의 한 곳 조건 유지)"
    requirement: SEC-06
    verification:
      - kind: integration
        ref: "grep -vE '^\\s*#' routers/workspaces.py | grep -cE '\\b403\\b' → 0 · grep -c 'status_code=' → 0 · grep -c 'except' → 0"
        status: pass
      - kind: unit
        ref: "apps/api/tests/test_workspaces_router.py#test_zero_affected_rows_are_rendered_by_the_single_handler"
        status: pass
    human_judgment: false
  - id: D6
    description: "정책을 느슨하게 만든 상태에서 격리 테스트가 반드시 red가 된다 (prohibitions, T-02-22)"
    requirement: SEC-06
    verification:
      - kind: integration
        ref: "3단계 실측 — 정상 exit 0 / 느슨 exit 1 (5 failed) / 복구 exit 0. docs/ops/tenant-isolation-proof.md §결과"
        status: pass
      - kind: integration
        ref: "느슨 단계에서 service_role 재조회로 대상 워크스페이스의 name이 실제로 변경됨을 확인"
        status: pass
    human_judgment: false
  - id: D7
    description: "느슨한 정책이 커밋되지 않으며 위반 픽스처가 마이그레이션 경로 밖에 있다 (T-02-23)"
    verification:
      - kind: integration
        ref: "`git diff --name-only supabase/migrations/` 빈 출력 (length=0)"
        status: pass
      - kind: integration
        ref: "`supabase db reset` 후 pg_policies 4행이 느슨하게 만들기 전과 문자열 일치"
        status: pass
    human_judgment: false
  - id: D8
    description: "갱신 요청 모델이 소유권 이전 필드를 받지 않는다 (T-02-21)"
    verification:
      - kind: unit
        ref: "apps/api/tests/test_workspaces_router.py#test_ownership_transfer_field_is_rejected_before_any_upstream_call"
        status: pass
      - kind: integration
        ref: "grep -cE 'owner_id|created_at' routers/workspaces.py → 0"
        status: pass
    human_judgment: false
  - id: D9
    description: "인증 없는 요청이 Forbidden 단언을 우연히 통과하지 않는다 (T-02-24)"
    verification:
      - kind: integration
        ref: "apps/api/tests/test_workspaces_isolation.py#test_unauthenticated_write_is_unauthorized_not_forbidden[PATCH|DELETE] — 401이며 403이 아님"
        status: pass
    human_judgment: false
  - id: D10
    description: "0007 섹션 8의 권한 매트릭스가 workspaces 경로에 대해 넓지도 좁지도 않다"
    verification:
      - kind: integration
        ref: "authenticated의 workspaces SELECT/INSERT/UPDATE/DELETE 4종이 실제 왕복에서 전부 필요했고 전부 충분했다 — 예상치 못한 42501은 한 건도 없었다"
        status: pass
    human_judgment: false
  - id: D11
    description: "나머지 8개 테이블과 Storage 경로의 격리도 애플리케이션 경로에서 차단된다"
    verification: []
    human_judgment: true
    rationale: "이 플랜이 만든 표면은 workspaces 테이블 하나뿐이다. 전수 스위트는 Phase 7의 OPS-04이며, CROSS_TENANT_CASES가 행 추가만으로 확장되도록 설계되어 있다."
  - id: D12
    description: "클라우드(ap-southeast-1)에서도 같은 왕복 결과가 나온다"
    verification: []
    human_judgment: true
    rationale: "0007까지 스키마와 권한 매트릭스가 동일함은 확인되었으나 실제 왕복은 로컬에서만 관측했다. 픽스처는 루프백 가드로 클라우드를 가리킬 수 없게 막혀 있으므로, 클라우드 확인은 별도 수단이 필요하다."

# Metrics
duration: 55min
completed: 2026-08-07
status: complete
---

# Phase 02 Plan 04: 교차 테넌트 격리의 실제 HTTP 왕복 증명 Summary

**02-03이 `MockTransport`로 가정했던 "RLS가 막은 쓰기는 0행으로 돌아온다"를 로컬 스택 상대의 실제 왕복으로 확인하고, 그 테스트가 공허하지 않음을 정책을 실제로 깨서 증명했다**

## Performance

- **Duration:** 약 55분
- **Completed:** 2026-08-07
- **Tasks:** 3 (TDD 2 + 검증 1)
- **Files:** 신규 6, 수정 2
- **Tests:** 88 → 110 (신규 22: 라우터 단위 9 + 격리 왕복 13)

## Accomplishments

- **SEC-06이 실측으로 충족됐다.** 사용자 2명 × 워크스페이스 2개를 실제로 만들고, 양방향 교차
  `PATCH`/`DELETE` 4건이 전부 403을 받는 것을 확인했다. 이 페이즈 이전까지 "격리는 RLS가
  강제한다"는 문장은 SQL 안에서만 참이었다.
- **02-03의 두 가정이 실제 왕복에서 확인됐다.** PostgREST는 RLS가 막은 `PATCH`/`DELETE`에
  대해 **HTTP 200과 빈 배열**을 돌려준다 — 예외가 아니다. `UserDb._exactly_one`이 영향 행 수
  0을 `WorkspaceForbidden`으로 바꾸고 단일 핸들러가 403으로 렌더한다는 02-03의 설계가 실제
  PostgREST 동작과 정확히 맞물린다.
- **fail-first가 실제로 red를 만들었고, 그 과정에서 첫 시도가 실패했다.** 처음 만든 위반
  픽스처(UPDATE·DELETE만 느슨하게)에서 격리 테스트는 **13건 전부 통과**했다. 원인을 추적한
  결과 Postgres에서 `update … where id = $1`이 대상 행을 먼저 읽어야 하므로 SELECT 정책이 그
  행을 가린 상태에서는 UPDATE 술어를 아무리 풀어도 0행이 돌아온다는 사실이 드러났다. SELECT
  정책까지 함께 푼 뒤에야 교차 테넌트 쓰기가 실제로 성공했고 5건이 `assert 200 == 403`으로
  실패했다. **이 첫 실패가 fail-first를 한 이유 그 자체다** — 안 했다면 "위반 픽스처를 만들고
  테스트가 통과하니 안전하다"는 정확히 거꾸로 된 결론에 도달했을 것이다.
- **red의 분포가 무엇을 풀었는지와 정확히 대응했다.** 느슨 단계에서도 green으로 남은 8건은
  전부 그래야 할 이유가 있다 — 부재 UUID와 재삭제는 어떤 테넌트에도 행이 없어 정책과 무관하고,
  미인증 2건은 `to authenticated`를 건드리지 않았으므로 그대로다. 전부 빨개졌다면 그것은
  테스트가 정책이 아니라 환경에 반응한다는 신호였을 것이다.
- **0007의 권한 매트릭스가 이 경로에서 처음 실전 검증됐다.** 02-06이 남긴 "넓지도 좁지도
  않은지는 02-04에서 처음 드러난다"에 대한 답: `workspaces` 경로에 대해 정확히 맞았다.
  예상치 못한 `42501`은 한 건도 없었다.

## Task Commits

1. **Task 1: workspaces 최소 라우터** — `459ed45` (test, RED) → `999fbd8` (feat, GREEN)
2. **Task 2: 테스트별 고유 픽스처와 파라미터화 교차 테넌트 표** — `c591c69` (test, RED) → `7aac6dd` (feat, GREEN)
3. **Task 3: fail-first 증명** — `81f10d1` (test)

## Files Created/Modified

### 신규

- `apps/api/src/api/routers/workspaces.py` — `PATCH`/`DELETE /workspaces/{workspace_id}`.
  상태 코드 리터럴 0개, `status_code=` 0개, `except` 0개. `WorkspaceUpdateRequest`는
  `extra="forbid"` + `name` 한 필드.
- `apps/api/tests/test_workspaces_router.py` (9 tests) — MockTransport 기반 단위 회귀.
- `apps/api/tests/conftest.py` — 저장소 최초의 공유 픽스처. `two_workspaces_two_users`,
  `authed_client`(팩토리), `user_db`(팩토리), `local_stack`.
- `apps/api/tests/test_workspaces_isolation.py` (13 tests) — SEC-06 증명.
- `supabase/tests/0004_loosened_rls_violation.sql` — `-- 1. 느슨하게` / `-- 2. 되돌리기`.
- `docs/ops/tenant-isolation-proof.md` — 배경 / 방법 / 결과 / 한계 4절.

### 수정

- `apps/api/src/api/main.py` — `include_router(workspaces_router)` 한 줄.
- `checklists.json` — `P2-BE-01`에 `deviations_from_plan` 3건.

## Decisions Made

- **미인증 요청의 401은 `HTTPBearer`가 낸다.** 플랜은 "라우터에 상태 코드 리터럴을 두지
  말라"와 "인증 없는 요청은 Unauthorized를 받는다"를 동시에 요구한다. FastAPI의 `HTTPBearer`
  의존성이 자격증명 부재를 401로 처리하므로 두 요구가 동시에 만족된다. 라우터가 직접
  `HTTPException(401)`을 던졌다면 상태 코드가 다시 라우터로 흩어졌을 것이다.
- **conftest는 로컬 스택 접속 정보를 환경변수에서 읽지 않는다.** 저장소 루트의 `.env.local`은
  **클라우드** 프로젝트의 URL과 secret key를 담고 있다. 환경을 읽는 픽스처는 그 값이 export 된
  셸에서 실제 운영 프로젝트에 사용자와 워크스페이스를 만들고 지운다. 상수로 못 박고 루프백
  가드(`_assert_loopback`)를 추가로 걸었다. 쓰인 값은 Supabase CLI가 모든 로컬 스택에 동일하게
  발급하는 공개 데모 JWT다 — `supabase status`가 매번 새로 생성하는 `sb_publishable_`/
  `sb_secret_` 값을 쓰면 스택 재시작마다 테스트가 깨진다.
- **픽스처가 워크스페이스를 소유자 JWT로 만든다.** `0007` 섹션 8은 `service_role`에
  `workspaces` SELECT만 준다. 처음에는 이것을 매트릭스가 좁게 틀린 것으로 의심했으나, 워커가
  워크스페이스를 만드는 경로는 설계에 없으므로 정상이다. 오히려 이 좁음 덕분에 픽스처가
  사용자 경로를 그대로 밟게 되어 증명이 더 실전에 가까워졌다.
- **정상 소유자 경로 성공을 같은 파라미터 표에 넣었다.** 전부 거절하는 서버도 교차 케이스만
  보면 통과한다. `test_owner_can_write_to_their_own_workspace` 2건이 없으면 이 스위트는 절반만
  증명한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 위반 픽스처가 SELECT 정책을 풀지 않아 fail-first가 green으로 통과**

- **Found during:** Task 3, 3단계
- **Issue:** 플랜은 "`workspaces`의 UPDATE·DELETE 정책을 느슨하게"라고 지시한다. 그대로 만들어
  적용했더니 격리 테스트가 **13건 전부 통과**했다. Postgres에서 `update … where id = $1`은 대상
  행을 먼저 읽어야 찾으므로, SELECT 정책이 그 행을 가리고 있으면 UPDATE 술어를 아무리 풀어도
  0행이 돌아온다. `service_role`로 재조회해 대상 행이 실제로 바뀌지 않았음도 확인했다.
- **Fix:** 위반 픽스처가 `workspaces_select_member`까지 함께 풀도록 확장했다. 되돌리기 섹션도
  `0004:163-178` 세 정책 전부를 복원한다. 세 조합(UPDATE·DELETE만 / SELECT만 / SELECT+UPDATE)을
  각각 실측해 어느 겹이 무엇을 막는지 표로 남겼다.
- **Files modified:** `supabase/tests/0004_loosened_rls_violation.sql`, `docs/ops/tenant-isolation-proof.md`
- **Verification:** 확장 후 3단계 exit 1 (5 failed), 대상 워크스페이스의 `name`이 실제로 `HIJACKED`로 변경됨
- **Committed in:** `81f10d1`

**2. [Rule 3 - Blocking] FastAPI 0.141의 `include_router`가 `app.routes`에 개별 라우트를 남기지 않음**

- **Found during:** Task 1 (GREEN 검증)
- **Issue:** 플랜 Task 1의 `<verify>` 명령은 `paths={r.path for r in a.routes}`로 경로 존재를
  확인한다. FastAPI 0.141은 `include_router` 결과를 불투명한 `_IncludedRouter` 객체 하나로 남겨
  `r.path`가 `None`이다. 명령을 그대로 쓰면 라우터가 정상 등록되어 있어도 실패한다.
- **Fix:** 실제 노출 표면을 묻는 안정적인 창구인 `app.openapi()["paths"]`로 바꿨다. 테스트에도
  같은 방식을 쓰고 ⚠️ 주석으로 이유를 남겼다.
- **Files modified:** `apps/api/tests/test_workspaces_router.py`
- **Verification:** `{'patch','delete'} <= set(paths['/workspaces/{workspace_id}'])`
- **Committed in:** `999fbd8`

**3. [Rule 2 - Missing Critical] 파괴적 픽스처가 클라우드를 가리킬 수 없게 하는 가드**

- **Found during:** Task 2
- **Issue:** 플랜은 접속 정보의 출처를 지정하지 않는다. 관례대로 `SUPABASE_URL` 환경변수를 읽게
  만들었다면, 저장소의 `.env.local`이 **클라우드** URL과 secret key를 담고 있으므로 그 값이
  export 된 셸에서 이 픽스처가 운영 프로젝트에 사용자와 워크스페이스를 만들고 지운다. 조용히
  성공하는 종류의 사고다.
- **Fix:** 접속 정보를 상수로 못 박고, 모든 진입점에서 `_assert_loopback()`이 호스트가
  루프백인지 확인한다. 아니면 이유를 밝히며 `RuntimeError`.
- **Files modified:** `apps/api/tests/conftest.py`
- **Verification:** 세 픽스처(`local_stack`, `authed_client`, `user_db`) 전부에서 호출됨
- **Committed in:** `7aac6dd`

### 계획과의 차이 (자동 수정 아님)

**4. `apps/api/tests/test_workspaces_router.py`는 플랜의 파일 목록에 없다**

- Task 1이 `tdd="true"`이고 `<behavior>` 4개 케이스를 지정하지만 `<files>`에 테스트 파일이 없다.
  RED 게이트를 만족하려면 테스트 파일이 필요하므로 추가했다. 격리 왕복 테스트(Task 2)와 역할이
  다르다 — 이쪽은 MockTransport 기반 단위 회귀이고, 저쪽이 실제 왕복이다.

**5. Task 2 `<behavior>` Test 6(워크스페이스 목록 조회)을 라우터가 아닌 `UserDb`로 확인했다**

- Task 1이 "경로 두 개만 만든다"고 못 박았으므로 `GET /workspaces` 라우트를 추가하지 않았다.
  대신 `test_read_that_rls_blocks_returns_empty_instead_of_forbidden`이 요청자 JWT를 실은
  `UserDb.select`로 실제 왕복을 돌려 "RLS가 막은 조회는 빈 결과이며 예외가 아니다"(D-11)를
  확인한다. 라우트를 하나 더 늘리는 것보다 D-11의 주장에 더 직접적이다.

**6. `checklists.json`의 `P2-BE-01`은 여전히 `pending`이다**

- 이 태스크의 원래 범위(인증 미들웨어, 워크스페이스 컨텍스트 해석, CORS)는 아직 없다. 이 플랜이
  만든 것은 그 범위의 일부인 라우터 표면과 예외 렌더 경로뿐이므로 `status`를 올리지 않고
  `deviations_from_plan`만 기록했다. CLAUDE.md의 "이탈은 in-file과 원장 양쪽에" 규약을 따른 것이다.

---

**Total deviations:** 3 auto-fixed (1 bug, 1 blocking, 1 missing critical) + 3 문서화된 차이
**Impact on plan:** 산출물 목록은 플랜 그대로이고 하나(`test_workspaces_router.py`)가 늘었다.
확대된 것은 위반 픽스처의 범위(정책 2개 → 3개)이며, 그것이 없으면 fail-first가 성립하지 않는다.

## Issues Encountered

- **`ruff format`이 커밋을 한 번 거부했다** (Task 2 RED). 파라미터화 데코레이터를 상수로 뽑는
  과정에서 줄바꿈이 달라졌다. 재-stage 후 재커밋으로 해소했고 `--no-verify`는 쓰지 않았다.
- **로컬 auth rate limit은 문제가 되지 않았다.** `sign_in_sign_ups = 30`(5분/IP)이 13개 테스트 ×
  사용자 2명 = 26회 로그인과 충돌할 수 있어 40회 연속 생성+로그인을 먼저 실측했다. 제한에 걸리지
  않았다 — admin 경로 생성은 이 카운터에 포함되지 않는 것으로 보인다.

## Known Stubs

없음. 이 플랜이 만든 모든 경로는 실제로 연결되어 있고 실제 왕복 테스트가 덮는다.

다만 아래는 스텁이 아니라 **의도적 범위 경계**다.

- **라우터가 두 개뿐이다.** 이것은 미완성이 아니라 증명 표면의 최소 크기다. 라우터 파일 헤더와
  `docs/ops/tenant-isolation-proof.md` §배경이 그 이유를 밝힌다. 실제 도메인 라우터는 Phase 3~5.
- **`docs/ops/tenant-isolation-proof.md` §한계**가 이 증명이 덮지 않는 것 5가지를 열거한다 —
  나머지 8개 테이블, Storage, 클라우드 왕복, 읽기 경로의 조용한 실패 양식, 동시성.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: defense-depth-observed | `supabase/migrations/0004_rls_policies.sql` | `workspaces`의 교차 테넌트 쓰기를 `workspaces_select_member`와 `workspaces_update_owner`가 **각각 독립적으로** 막는다. 좋은 소식이지만 함정도 있다 — 정책 하나가 실수로 넓어져도 증상이 나타나지 않으므로 회귀가 조용히 누적될 수 있다. 앞으로 이 종류의 fail-first는 반드시 관련 정책 전부를 함께 풀어야 유효하다 |
| threat_flag: destructive-fixture | `apps/api/tests/conftest.py` | 이 픽스처는 사용자와 워크스페이스를 실제로 생성·삭제한다. 접속 정보를 상수와 루프백 가드로 묶어 두었으나, 앞으로 누구든 이 상수를 환경변수 읽기로 "개선"하면 저장소의 `.env.local`(클라우드 자격증명)과 만나 운영 데이터를 건드린다. 상수 위 ⚠️ 주석이 유일한 경고다 |

## User Setup Required

`user_setup: []` — 신규 패키지 설치도 외부 서비스 설정도 없다. 로컬 Supabase 스택이 떠 있고
`0001`~`0007`이 적용되어 있으면 된다(`supabase status`).

## Next Phase Readiness

**준비된 것**

- **Phase 7의 OPS-04가 딛고 설 확장점이 있다.** `CROSS_TENANT_CASES`에 `(메서드, 경로 템플릿,
  본문, 설명)` 행만 추가하면 새 라우터가 같은 5종 검사를 자동으로 받는다.
- **Phase 3의 라우터가 그대로 따를 형태가 고정됐다.** 요청자 JWT를 `HTTPBearer`로 받아
  `UserDb`에 넘기고, 상태 코드도 예외 처리도 라우터에 두지 않는다.
- **02-03이 남긴 미확인 항목(D9)이 닫혔다.** PostgREST의 RLS 차단 응답 형태가 실제로 확인됐다.

**확인이 필요한 것**

- ⚠️ **이 증명은 `workspaces` 한 테이블에 한정된다.** 나머지 8개 테이블과 Storage 경로는 아직
  애플리케이션 경로에서 확인되지 않았다.
- ⚠️ **클라우드 왕복은 관측하지 않았다.** 스키마와 권한은 동일하지만, 루프백 가드 때문에 이
  픽스처로는 클라우드를 확인할 수 없다(의도된 제약이다). 별도 수단이 필요하다.
- ⚠️ **읽기 경로에서 격리가 풀리면 상태 코드가 변하지 않는다.** 결과 집합만 늘어나는 조용한
  실패다. Phase 4의 검색 경로가 이 성질을 그대로 물려받으므로 융합 계층 테스트는 상태 코드가
  아니라 내용을 단언해야 한다.

## Self-Check: PASSED

- 신규 6개 파일 전부 디스크에 존재
- 커밋 5개 전부 git 이력에 존재 (`459ed45`, `999fbd8`, `c591c69`, `7aac6dd`, `81f10d1`)
- 플랜 `<verification>` 5개 항목 전부 통과: `pytest apps/api/tests` exit 0 · 연속 2회 exit 0 ·
  느슨 단계 exit 1이 문서에 기록됨 · 403 리터럴 grep 0 · `git diff supabase/migrations/` 빈 출력
- 전체 스위트 `uv run pytest -q` 110 passed, `uv run ruff check apps packages` 통과
- 실행 후 잔여 행 0 (`workspaces` 0, `auth.users` 0)

---
*Phase: 02-security-spine-and-shared-domain*
*Completed: 2026-08-07*
