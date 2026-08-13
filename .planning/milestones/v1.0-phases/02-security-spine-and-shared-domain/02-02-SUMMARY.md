---
phase: 02-security-spine-and-shared-domain
plan: 02
subsystem: infra
tags: [pydantic-settings, fastapi, uv-workspace, ruff, pytest, secrets, rls]

# Dependency graph
requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: 단일 Dockerfile·단일 이미지(D-01), Railway 서비스별 env 스코프(D-12), packages/core 공용 패키지와 structlog REDACTED_KEYS
  - phase: 02-security-spine-and-shared-domain
    provides: 02-01이 트랜스포트를 rpc로 잠금 — 이 플랜은 그와 독립적으로 설정 계층만 다룬다
provides:
  - BaseAppSettings / ApiSettings / WorkerSettings 3계층 — api 프로세스는 secret을 담을 필드가 없다
  - MissingSettingError — 누락·빈 문자열·공백 값을 키 이름과 함께 기동 시점에 실패시킨다
  - create_app(settings, git_sha=...) 주입과 app.state.settings / app.state.git_sha
  - nexuswiki_core.deployment — git SHA·PORT를 설정 계층 밖에서 읽는 단일 지점
  - 루트 pyproject의 TID 규칙군 활성화와 apps/worker/tests 수집
affects: [02-03, 02-04, 02-07, 02-08, phase-03]

# Actuals (#2632)
actuals:
  tokens: 8900
  tasks: 4
  commits: 5

# Tech tracking
tech-stack:
  added: [pydantic-settings==2.14.2, python-dotenv==1.2.2 (전이 의존, 미사용)]
  patterns:
    - "역량 부재로 격리: 금지가 아니라 필드의 부재로 SEC-01을 집행"
    - "설정과 배포 메타데이터 분리: 없으면 못 뜨는 값과 없어도 되는 값을 다른 계층에 둔다"
    - "uvicorn factory 모드: 모듈 import가 프로덕션 환경을 요구하지 않는다"

key-files:
  created:
    - packages/core/src/nexuswiki_core/settings.py
    - packages/core/src/nexuswiki_core/deployment.py
    - apps/api/src/api/settings.py
    - apps/worker/src/worker/settings.py
    - packages/core/tests/test_settings.py
    - apps/worker/tests/test_settings.py
  modified:
    - apps/api/src/api/main.py
    - apps/api/src/api/routers/health.py
    - apps/api/src/api/__main__.py
    - apps/worker/src/worker/__main__.py
    - apps/api/tests/test_health.py
    - packages/core/tests/test_logging_redaction.py
    - pyproject.toml

key-decisions:
  - "git SHA와 PORT는 BaseAppSettings가 아니라 nexuswiki_core.deployment가 읽는다 — 배포 메타데이터에까지 D-10의 기동 실패 규칙이 번지지 않게 한다"
  - "uvicorn을 factory 모드로 바꾸고 모듈 레벨 app 객체를 제거했다 — 즉시 생성 app을 유지하면 api.main을 import하는 모든 테스트가 프로덕션 환경 전체를 요구한다"
  - "pytest import-mode를 importlib으로 고정 — 워크스페이스 멤버마다 같은 이름의 test 모듈이 생기므로 기본 prepend 모드는 basename 충돌로 수집 자체가 깨진다"
  - "WorkerSettings의 secret 4종과 LLM_MODEL을 모두 필수로 선언 — Railway worker 서비스 env에 다섯 키가 전부 있어야 기동한다"

patterns-established:
  - "필드명 ↔ REDACTED_KEYS casefold 일치를 테스트로 고정: 로그 마스킹이 조용히 멈추는 것을 red로 바꾼다"
  - "부팅 시점 검증이 런타임 검사를 대체한다: readiness는 DB 왕복만 보고 설정 유효성을 다시 묻지 않는다"
  - "설정 주입은 create_app 한 곳: 02-04의 라우터와 403 예외 핸들러가 같은 지점에 붙는다"

requirements-completed: [SEC-01]

coverage:
  - id: D1
    description: "ApiSettings가 SUPABASE_SECRET_KEY·DATABASE_URL·OPENROUTER_API_KEY·OPENAI_API_KEY 네 필드를 갖지 않는다 (SEC-01의 역량 부재)"
    requirement: SEC-01
    verification:
      - kind: unit
        ref: "packages/core/tests/test_settings.py#test_api_settings_has_no_field_that_could_hold_a_secret"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_settings.py#test_api_settings_adds_no_field_beyond_the_shared_ancestor"
        status: pass
    human_judgment: false
  - id: D2
    description: "WorkerSettings만 secret 4종 + LLM_MODEL을 선언하고 LLM_MODEL에 코드 기본값이 없다 (D-22)"
    requirement: SEC-01
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_settings.py#test_worker_settings_declare_every_secret_field"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_settings.py#test_llm_model_has_no_default_baked_into_the_code"
        status: pass
    human_judgment: false
  - id: D3
    description: "필수 설정이 누락·빈 문자열·공백일 때 해당 키 이름을 포함한 MissingSettingError로 기동이 실패한다 (D-10, SPEC R1)"
    requirement: SEC-01
    verification:
      - kind: unit
        ref: "packages/core/tests/test_settings.py#test_absent_required_setting_fails_and_names_the_key"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_settings.py#test_empty_string_setting_fails_exactly_like_an_absent_one"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_settings.py#test_worker_refuses_to_boot_without_a_secret_and_names_it"
        status: pass
    human_judgment: false
  - id: D4
    description: "WorkerSettings의 secret 필드명 casefold 집합이 REDACTED_KEYS에 덮여 로그 마스킹이 유지된다"
    requirement: SEC-01
    verification:
      - kind: unit
        ref: "packages/core/tests/test_logging_redaction.py#test_worker_settings_secret_fields_stay_inside_the_denylist"
        status: pass
    human_judgment: false
  - id: D5
    description: "create_app(settings)가 설정을 app.state에 싣고, api·worker 진입 경로가 환경을 직접 읽지 않는다"
    verification:
      - kind: unit
        ref: "apps/api/tests/test_health.py#test_create_app_stores_the_injected_settings_on_app_state"
        status: pass
      - kind: integration
        ref: "grep -rn 'os\\.environ' apps/api/src/api/ apps/worker/src/worker/__main__.py (출력 없음)"
        status: pass
    human_judgment: false
  - id: D6
    description: "ruff가 TID 규칙군을 적용하고 pytest가 저장소 루트에서 apps/worker/tests를 수집한다 (R12)"
    verification:
      - kind: integration
        ref: "uv run ruff check --select TID apps packages (exit 0)"
        status: pass
      - kind: integration
        ref: "uv run pytest --collect-only -q | grep apps/worker/tests/test_rtt.py"
        status: pass
    human_judgment: false
  - id: D7
    description: "Railway worker 서비스 env가 secret 4종 + LLM_MODEL을 실제로 담고 있어 배포된 worker가 기동한다"
    verification: []
    human_judgment: true
    rationale: "필수 필드화로 worker의 기동 조건이 강해졌다. 실제 Railway env 상태는 저장소에서 확인할 수 없고, 미충족 시 재배포 때 crash-loop으로만 드러난다."

# Metrics
duration: 45min
completed: 2026-08-06
status: complete
---

# Phase 02 Plan 02: Settings 계층 분리와 툴링 정합 Summary

**api 프로세스가 service key를 담을 필드 자체를 갖지 않도록 pydantic-settings 3계층을 세우고, 그 규칙을 집행할 ruff TID와 worker 테스트 수집을 켰다**

## Performance

- **Duration:** 약 45분 (blocking-human 게이트 대기 포함, 커밋 구간은 8분)
- **Started:** 2026-08-06T09:15Z (게이트 반환 시점 기준)
- **Completed:** 2026-08-06T09:29Z
- **Tasks:** 4 (게이트 1 + 실행 3)
- **Files modified:** 17 (신규 6, 수정 10, uv.lock 1)

## Accomplishments

- **SEC-01이 코드에 실재하게 되었다.** 이전에는 "api는 키를 담을 그릇이 없다"가 주장일 뿐이었고 `apps/api/src/api/main.py:24`가 환경을 직접 읽었다. 이제 `ApiSettings`는 `BaseAppSettings`의 네 필드를 그대로 상속할 뿐이며, secret 4종의 부재를 테스트가 고정한다.
- **부팅 시점 실패가 런타임 검사를 대체했다.** `MissingSettingError`가 누락·빈 문자열·공백 값을 모두 같은 방식으로 키 이름과 함께 보고한다. `/health/ready`의 필수 env 루프는 제거했다 — 기동 시점 검증이 그 역할을 이미 한 이상 런타임 반복은 절대 참이 되지 않는 죽은 분기다.
- **로그 마스킹 커플링이 테스트로 고정되었다.** `WorkerSettings`의 secret 필드명 casefold 집합이 `REDACTED_KEYS`의 부분집합임을 두 테스트가 단언하므로, 필드명을 바꾸면서 denylist를 갱신하지 않으면 red가 된다.
- **집행 수단 두 개가 무력 상태에서 벗어났다.** `TID`가 `select`에 없어 02-03의 banned-api 설정이 무시될 예정이었고, `testpaths`에 worker가 빠져 `test_rtt.py` 5개가 조용히 수집되지 않고 있었다. 수집 대상이 24개 → 39개로 늘었고 전부 통과한다.

## Task Commits

1. **Gate: pydantic-settings 패키지 정당성 확인** — 커밋 없음 (사용자 승인: `pydantic-settings==2.14.2`)
2. **Task 1: BaseAppSettings / ApiSettings / WorkerSettings 3계층** — `a1eb977` (test, RED) → `e76c4ed` (feat, GREEN)
3. **Task 2: create_app(settings) 주입과 진입 경로의 환경 직접 읽기 제거** — `4d3345f` (test, RED) → `3922483` (feat, GREEN)
4. **Task 3: 루트 pyproject.toml 툴링 정합** — `933b58d` (chore)

## Files Created/Modified

### 신규

- `packages/core/src/nexuswiki_core/settings.py` — `BaseAppSettings`(비밀 아닌 4개 필드) + `MissingSettingError`. 빈 문자열·공백을 누락과 동일하게 취급하는 `"*"` 검증기가 여기 있다.
- `packages/core/src/nexuswiki_core/deployment.py` — `resolve_git_sha()` / `resolve_port()`. api·worker 두 진입 경로에서 `os.environ`을 없애는 단일 지점.
- `apps/api/src/api/settings.py` — `ApiSettings`. 본문에 필드가 하나도 없고 `⚠️` 주석이 D-06을 가리킨다.
- `apps/worker/src/worker/settings.py` — `WorkerSettings`. secret 4종 + `LLM_MODEL` + `RTT_PROBE_ENABLED`.
- `packages/core/tests/test_settings.py` (10 tests) · `apps/worker/tests/test_settings.py` (10 tests)

### 수정

- `apps/api/src/api/main.py` — `create_app(settings, *, git_sha=None)`, `app.state.settings`/`app.state.git_sha`, uvicorn용 `build_app()`
- `apps/api/src/api/routers/health.py` — `os.environ` 접근과 필수 env 루프 제거, `request.app.state`만 읽음
- `apps/api/src/api/__main__.py` — factory 모드 + `resolve_port()`
- `apps/worker/src/worker/__main__.py` — 진입 즉시 `WorkerSettings` 생성, "설정 없으면 프로브 건너뜀" 분기 제거
- `apps/api/tests/test_health.py` — 팩토리 기반 `app_client()` 헬퍼 (02-04가 이 형태를 그대로 쓴다)
- `packages/core/tests/test_logging_redaction.py` — 마스킹 커플링 단언 추가
- `pyproject.toml` — `TID` 활성화, `apps/worker/tests` 수집, `--import-mode=importlib`
- `packages/core|apps/api|apps/worker/pyproject.toml` + `uv.lock` — `pydantic-settings==2.14.2` 고정

## Decisions Made

- **`GIT_SHA`·`PORT`를 설정 계층에서 뺐다.** 플랜은 "git SHA는 배포 메타데이터이므로 `BaseAppSettings`에 넣지 말라"고 지시하면서 동시에 `apps/api/src/api/`에서 `os.environ`을 전부 없애라고 요구한다. 두 요구를 동시에 만족하는 지점은 `apps/api` 바깥이므로 `packages/core`에 `deployment.py`를 두었다. worker도 같은 함수를 쓰므로 두 진입 경로의 `os.environ`이 한 번에 해소된다.
- **모듈 레벨 `app` 객체를 없애고 uvicorn factory 모드로 갔다.** 플랜은 `app = create_app(...)`을 유지하라고 했으나, `ApiSettings()`를 모듈 로드 시점에 만들면 `api.main`을 import하는 것만으로 프로덕션 환경 전체가 필요해진다. 02-04가 이 모듈을 import하는 격리 테스트를 추가하므로 그 비용이 계속 번진다. `build_app()` + `factory=True`로 기동 시점 실패는 그대로 유지하면서 import를 부작용 없게 만들었다.
- **`WorkerSettings`의 다섯 키를 전부 필수로 두었다.** D-10의 "반쯤 설정된 프로세스보다 안 뜨는 편이 안전하다"를 `LLM_MODEL`에도 일관되게 적용했다. Phase 2에는 LLM 호출이 없으므로 이 키는 당장 쓰이지 않지만, 기본값을 박지 말라는 D-22와 필수화는 양립한다. **배포 영향은 아래 Next Phase Readiness에 적었다.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `uv sync`가 워크스페이스 멤버를 제거해 테스트 환경이 깨졌다**

- **Found during:** Task 1 (GREEN 검증)
- **Issue:** 플랜의 `<verify>`가 지시한 `uv sync`는 루트가 `package = false`이고 의존성이 없어 `api`·`worker`·`nexuswiki-core`를 **언인스톨**한다. 실행 직후 `ModuleNotFoundError: No module named 'nexuswiki_core'`가 났다.
- **Fix:** `uv sync --all-packages`로 복구. 이것이 `Dockerfile:18`이 이미 쓰고 있는 정규 형태다.
- **Files modified:** 없음 (환경 조작)
- **Verification:** `uv run pytest -q` 39 passed
- **Note:** `README.md:16`의 `uv sync --frozen`도 같은 결함을 갖는다 — 새로 클론한 개발자에게 동작하지 않는 명령을 안내한다. ROADMAP 성공기준 3("`uv sync` 한 번으로 세 패키지가 빌드된다")과도 어긋나므로 아래 deferred-items에 남겼다. 이 플랜의 범위 밖이라 고치지 않았다.

**2. [Rule 3 - Blocking] 워크스페이스 간 test 모듈 basename 충돌로 수집이 깨졌다**

- **Found during:** Task 1 (GREEN 검증)
- **Issue:** `packages/core/tests/test_settings.py`와 `apps/worker/tests/test_settings.py` 두 이름이 같고 `__init__.py`가 없어 pytest 기본 prepend 모드가 `import file mismatch`로 수집을 중단했다. 플랜이 두 파일을 같은 이름으로 지정했다.
- **Fix:** 루트 `pyproject.toml`에 `addopts = ["--import-mode=importlib"]` 추가. 플랜이 이름 붙인 산출물 경로를 그대로 지키면서, 02-07·02-08이 worker 테스트를 더 추가할 때 같은 충돌이 재발하지 않게 하는 쪽을 골랐다 (파일명 변경은 증상만 미룬다).
- **Files modified:** `pyproject.toml`
- **Verification:** `uv run pytest -q` 39 passed, 두 `test_settings.py` 모두 수집됨
- **Committed in:** `e76c4ed`

**3. [Rule 3 - Blocking] ruff `S105`가 테스트의 secret 리터럴 비교를 막았다**

- **Found during:** Task 1 (RED 커밋 시 pre-commit)
- **Issue:** `assert settings.SUPABASE_SECRET_KEY == "sb_secret_test"`가 하드코딩된 비밀번호로 잡혀 커밋이 거부되었다.
- **Fix:** 픽스처 딕셔너리 `COMPLETE_WORKER_ENV`를 단일 출처로 삼아 `getattr` 루프로 비교. 오탐과 값 중복을 함께 없앴다. `noqa`는 쓰지 않았다.
- **Files modified:** `apps/worker/tests/test_settings.py`
- **Verification:** `uv run ruff check apps packages` exit 0
- **Committed in:** `a1eb977`

**4. [Rule 2 - Missing Critical] `apps/api/src/api/__main__.py`의 `os.environ` 누락**

- **Found during:** Task 2
- **Issue:** 플랜의 Task 2 `<files>`에 이 파일이 없으나, 수용기준의 `grep -rn 'os\.environ' apps/api/src/api/`는 이 디렉터리 전체를 훑고 `port=int(os.environ.get("PORT", "8000"))`이 걸린다. 파일을 빼둔 채로는 수용기준을 만족할 수 없다.
- **Fix:** `resolve_port()`로 교체. `os.getenv`로 바꿔 grep만 피하는 방식은 의도에 어긋나므로 쓰지 않았다.
- **Files modified:** `apps/api/src/api/__main__.py`
- **Verification:** grep exit 1 (출력 없음)
- **Committed in:** `3922483`

**5. [Rule 1 - Bug] ruff 캐시가 가리고 있던 `I001` 2건**

- **Found during:** Task 3
- **Issue:** `nexuswiki_core.settings`·`worker.settings`가 디스크에 없던 RED 시점에 ruff가 이 둘을 third-party로 분류해 import 블록을 정렬했고, 그 결과가 캐시되어 GREEN 이후에도 "clean"으로 보였다. `pyproject.toml` 변경으로 캐시가 무효화되자 두 파일에서 `I001`이 드러났다.
- **Fix:** `ruff check --fix`로 정렬 재적용. 두 모듈이 이제 first-party로 올바르게 분류된다.
- **Files modified:** `packages/core/tests/test_settings.py`, `apps/worker/tests/test_settings.py`
- **Verification:** `uv run ruff check apps packages` exit 0, `pre-commit run --all-files` 전부 Passed
- **Committed in:** `933b58d`

---

**Total deviations:** 5 auto-fixed (3 blocking, 1 missing critical, 1 bug)
**Impact on plan:** 범위 확대 없음. 4건은 플랜 자신의 수용기준·검증 명령을 만족하기 위해 필요했고, 1건은 캐시가 숨긴 기존 결함이다. 신규 파일 `deployment.py` 하나가 플랜에 없던 산출물이지만, 이는 "git SHA를 설정에 넣지 말라 + `os.environ`을 없애라"는 두 지시를 동시에 만족시키는 유일한 위치다.

## Issues Encountered

- **pre-commit이 두 차례 커밋을 거부했다** — ruff가 파일을 수정하면 pre-commit이 커밋을 중단한다. 재-stage 후 재커밋으로 해소했다. 정상 동작이며 우회하지 않았다 (`--no-verify` 미사용).
- **`uv run pytest`가 24개만 수집하던 구간이 있었다** — Task 3에서 `testpaths`를 고치기 전까지 worker 테스트 15개가 보이지 않았다. 이것이 이 태스크가 존재하는 이유 자체이므로 예상된 상태다.

## Known Stubs

없음. 이 플랜이 만든 모든 코드 경로는 실제로 연결되어 있고 테스트가 덮는다.

## User Setup Required

`user_setup: []` — 신규 외부 서비스 설정은 없다. 다만 아래 배포 영향을 확인할 것.

## Next Phase Readiness

**준비된 것**

- 02-03이 `service_client(settings: WorkerSettings)` 팩토리의 인자 타입으로 `WorkerSettings`를 그대로 쓸 수 있다. `ApiSettings`로는 타입이 맞지 않는다 (D-08).
- 02-03이 `[tool.ruff.lint.flake8-tidy-imports.banned-api]` 블록과 `per-file-ignores`의 `"apps/worker/**" = ["TID251"]`을 같은 파일에 이어 붙이면 즉시 동작한다. 규칙군은 이미 켜져 있다.
- 02-04가 `create_app(settings)`가 만든 앱 위에 라우터와 단일 403 예외 핸들러를 올릴 수 있다. `apps/api/tests/test_health.py`의 `app_client()` 헬퍼가 팩토리 형태로 준비되어 있다.
- 02-07·02-08의 worker 테스트가 저장소 루트 `pytest`에서 실제로 수집된다.

**확인이 필요한 것**

- ⚠️ **Railway worker 서비스 env에 `SUPABASE_SECRET_KEY`·`DATABASE_URL`·`OPENROUTER_API_KEY`·`OPENAI_API_KEY`·`LLM_MODEL` 다섯 개가 모두 있어야 worker가 기동한다.** 이전 코드는 설정이 없으면 RTT 프로브만 건너뛰고 계속 떴지만, 이제는 `main()` 진입 즉시 `MissingSettingError`로 죽는다. 이는 D-10이 의도한 동작이지만 다음 배포에서 crash-loop으로 처음 드러날 수 있다. api 서비스 env에는 secret 4종이 **없어야** 정상이다 (SEC-01).
- `README.md:16`의 `uv sync --frozen`은 워크스페이스 멤버를 설치하지 않는다 — `--all-packages`가 필요하다. ROADMAP 성공기준 3과 어긋나므로 `deferred-items.md`에 기록했다.

## Self-Check: PASSED

- 산출물 7개 파일 전부 디스크에 존재
- 커밋 5개 전부 git 이력에 존재 (`a1eb977`, `e76c4ed`, `4d3345f`, `3922483`, `933b58d`)
- 플랜 `<verification>` 5개 항목 전부 통과, `pre-commit run --all-files` 통과

---
*Phase: 02-security-spine-and-shared-domain*
*Completed: 2026-08-06*
