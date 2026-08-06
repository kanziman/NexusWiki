---
phase: 02-security-spine-and-shared-domain
plan: 03
subsystem: backend
tags: [rls, postgrest, service-role, ruff-tid, fastapi, exception-handler, tenant-isolation]

# Dependency graph
requires:
  - phase: 02-security-spine-and-shared-domain
    provides: "02-01이 트랜스포트를 rpc로 잠금 — UserDb는 PostgREST 어댑터이며 asyncpg 커넥션 계층이 없다"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-02의 WorkerSettings/ApiSettings 3계층, create_app(settings) 주입 지점, ruff TID 규칙군 활성화"
provides:
  - "service_client(settings: WorkerSettings) — 인자 필수 팩토리, 모듈 전역 싱글턴 없음"
  - "ServiceDb — jobs 테이블 헬퍼가 workspace_id를 기본값 없는 keyword-only로 요구, 큐 RPC 4종은 허용 목록으로 고정"
  - "ruff banned-api TID251이 apps/api/**의 worker.db.service import를 빌드 실패로 만든다"
  - "UserDb.update_one / delete_one — 영향 행 수가 1이 아니면 WorkspaceForbidden"
  - "api.errors — WorkspaceForbidden · DatabaseError · register_error_handlers, 단일 렌더 함수"
  - "create_app에 이미 등록된 403 핸들러 — 라우터는 상태 코드를 다루지 않는다"
affects: [02-04, 02-06, 02-07, phase-03]

# Actuals (#2632)
actuals:
  tokens: 7396
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "헬퍼 분류를 테스트가 강제한다: 모든 공개 메서드가 table/queue-rpc 둘 중 하나여야 하고 분류를 빠져나가면 red"
    - "예외는 SQLSTATE를 실어 올리기만 하고 판정하지 않는다 — 판정과 렌더가 한 함수에 모인다"
    - "조건 없는 쓰기를 요청 전에 ValueError로 막는다"

key-files:
  created:
    - apps/worker/src/worker/db/__init__.py
    - apps/worker/src/worker/db/service.py
    - apps/worker/tests/test_service_client.py
    - apps/api/src/api/db/__init__.py
    - apps/api/src/api/db/user.py
    - apps/api/src/api/errors.py
    - apps/api/tests/test_user_db.py
    - apps/api/tests/fixtures/banned_import_violation.py.txt
  modified:
    - pyproject.toml
    - apps/api/src/api/main.py

key-decisions:
  - "큐 RPC 헬퍼(claim/complete/fail/release)에는 workspace_id를 요구하지 않는다 — 0003의 계약상 쓰이지 않는 인자가 되어 격리를 강제하는 척만 하게 된다. 대신 QUEUE_RPC_FUNCTIONS 허용 목록과 분류 테스트가 이 예외가 도메인 테이블로 번지는 것을 막는다"
  - "UserDb는 workspace_id를 강제하지 않는다 — 이 경로의 격리 수단은 RLS이며, workspace_id 강제는 BYPASSRLS인 worker 쪽의 책임이다"
  - "쓰기 메서드는 match 조건이 비면 요청을 보내기 전에 ValueError로 거부한다 (플랜 밖 추가)"
  - "42501이 아닌 SQLSTATE는 Forbidden으로 뭉개지 않고 500으로 낸다 — 진짜 장애가 격리 위반으로 위장되는 것을 막는다"
  - "main.py는 `from api import errors` + `errors.register_error_handlers(app)` 형태를 쓴다 — 등록 지점이 정확히 한 줄이라는 수용기준을 문자 그대로 만족한다"

patterns-established:
  - "분류 누락 차단: 새 공개 헬퍼가 어느 분류에도 없으면 테스트가 red — workspace 스코프 강제를 우회하는 헬퍼를 구조적으로 막는다"
  - "응답 본문 동일성 단언: 부재와 격리 위반의 응답이 바이트 단위로 같음을 테스트가 고정해 열거 공격 표면을 막는다"
  - "픽스처 확장자 회피(.py.txt): lint 위반 케이스를 커밋하면서 평소 수집에서 빼는 법"

requirements-completed: [SEC-02, SEC-04]

coverage:
  - id: D1
    description: "service_client()가 WorkerSettings 인스턴스를 인자로 요구하며 모듈 전역 싱글턴이 없다 (D-08)"
    requirement: SEC-02
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_service_client.py#test_service_client_refuses_to_build_without_settings"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_service_client.py#test_importing_the_module_reads_no_credentials_and_holds_no_client"
        status: pass
      - kind: integration
        ref: "uv run python -c \"import worker.db.service as m; m.service_client()\" → TypeError"
        status: pass
    human_judgment: false
  - id: D2
    description: "service_client()를 ApiSettings 인스턴스로 호출하면 SUPABASE_SECRET_KEY를 이름으로 밝히며 거부된다"
    requirement: SEC-02
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_service_client.py#test_service_client_rejects_api_settings_and_names_the_missing_key"
        status: pass
    human_judgment: false
  - id: D3
    description: "apps/api/** 에 worker.db.service import를 넣으면 ruff check가 TID251로 non-zero 종료한다"
    requirement: SEC-02
    verification:
      - kind: integration
        ref: "cp fixtures/banned_import_violation.py.txt apps/api/src/api/_banned_probe.py && ruff check apps/api → TID251, non-zero"
        status: pass
      - kind: integration
        ref: "픽스처 제거 후 uv run ruff check apps packages → exit 0, uv run ruff check apps/worker → exit 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "ServiceDb의 모든 테이블 접근 헬퍼가 workspace_id를 기본값 없이 요구하고, 생성된 쿼리에 그 조건이 실린다 (prohibitions)"
    requirement: SEC-02
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_service_client.py#test_scoped_helpers_reject_missing_workspace_id"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_service_client.py#test_scoped_helpers_accept_workspace_id"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_service_client.py#test_every_public_helper_is_classified_as_table_or_queue_rpc"
        status: pass
    human_judgment: false
  - id: D5
    description: "update_one()·delete_one()이 affected rows 0과 2 이상 양쪽에서 WorkspaceForbidden을 던진다 (D-11, SPEC Edge Coverage R4)"
    requirement: SEC-04
    verification:
      - kind: unit
        ref: "apps/api/tests/test_user_db.py#test_update_one_raises_when_no_row_was_affected"
        status: pass
      - kind: unit
        ref: "apps/api/tests/test_user_db.py#test_delete_one_raises_when_no_row_was_affected"
        status: pass
      - kind: unit
        ref: "apps/api/tests/test_user_db.py#test_update_one_raises_when_more_than_one_row_matched"
        status: pass
      - kind: unit
        ref: "apps/api/tests/test_user_db.py#test_delete_one_raises_when_more_than_one_row_matched"
        status: pass
    human_judgment: false
  - id: D6
    description: "SQLSTATE 42501과 WorkspaceForbidden을 단일 예외 핸들러가 403으로 렌더하고, 응답 본문이 리소스 존재를 누출하지 않는다 (D-12, D-13)"
    requirement: SEC-04
    verification:
      - kind: unit
        ref: "apps/api/tests/test_user_db.py#test_both_paths_are_rendered_by_the_same_handler_object"
        status: pass
      - kind: unit
        ref: "apps/api/tests/test_user_db.py#test_forbidden_body_leaks_nothing_about_the_resource"
        status: pass
      - kind: integration
        ref: "grep -c 'register_error_handlers' apps/api/src/api/main.py → 1"
        status: pass
    human_judgment: false
  - id: D7
    description: "읽기 메서드에는 0행 규칙이 적용되지 않아 정상적으로 비어 있는 조회가 빈 컬렉션을 돌려준다 (D-11)"
    requirement: SEC-04
    verification:
      - kind: unit
        ref: "apps/api/tests/test_user_db.py#test_select_returns_an_empty_list_without_raising"
        status: pass
    human_judgment: false
  - id: D8
    description: "예외 핸들러 등록이 기존 오류 경로를 삼키지 않는다 — /health/ready의 503이 그대로 남는다 (T-02-17)"
    verification:
      - kind: unit
        ref: "apps/api/tests/test_health.py#test_ready_returns_503_for_unreachable_database"
        status: pass
      - kind: unit
        ref: "apps/api/tests/test_user_db.py#test_other_sqlstates_are_not_rendered_as_forbidden"
        status: pass
    human_judgment: false
  - id: D9
    description: "실제 PostgREST가 RLS 차단·WITH CHECK 위반에서 여기서 가정한 형태(대표 표현 0행 / code 42501)를 돌려준다"
    verification: []
    human_judgment: true
    rationale: "이 플랜의 테스트는 전부 MockTransport로 응답 형태를 주입한다. 실제 왕복은 라우터가 서는 02-04에서 처음 확인되며, 02-01이 발견한 권한 공백(0007에서 닫힘) 때문에 그 전에는 어떤 실제 질의도 42501로 떨어진다."

# Metrics
duration: 35min
completed: 2026-08-06
status: complete
---

# Phase 02 Plan 03: service key 격리와 403 단일 매핑 Summary

**service key 클라이언트를 인자 없이는 만들 수 없게 만들고, RLS가 되돌려준 0행이 조용한 성공이 되지 않도록 0행·다중행·42501을 한 함수에서 Forbidden으로 렌더한다**

## Performance

- **Duration:** 약 35분
- **Completed:** 2026-08-06
- **Tasks:** 3 (TDD 2 + 문서/회귀 1)
- **Files modified:** 10 (신규 8, 수정 2)
- **Tests:** 62 → 88 (신규 26: worker 11 + api 15)

## Accomplishments

- **SEC-02가 코드에 실재한다.** `service_client()`는 인자 없이는 만들어지지 않고(`TypeError`), `ApiSettings`로 부르면 `SUPABASE_SECRET_KEY`를 이름으로 밝히며 거부된다. 모듈을 import 하는 것만으로는 어떤 자격증명도 읽지 않는다 — env를 전부 지운 상태에서 `importlib.reload`가 성공함을 테스트가 고정한다.
- **`apps/api/**`의 금지 import가 빌드 실패가 된다.** 위반 픽스처를 `apps/api/` 아래로 복사하면 `ruff check`가 `TID251`로 non-zero를 낸다. ⚠️ 이것은 조기 경보이지 1차 방어선이 아니다 — 단일 이미지(01-CONTEXT.md > D-01) 때문에 동적 import로는 우회되며, 실제로 막는 것은 `ApiSettings`에 필드가 없다는 사실과 Railway가 api 서비스에 값을 주입하지 않는다는 사실이다(D-06). 이 인과를 코드 주석과 규칙 메시지 양쪽에 그대로 적었다.
- **SEC-04가 한 곳에 모였다.** 0행과 다중행이 모두 `WorkspaceForbidden`이 되고, 그것과 SQLSTATE `42501`이 `_render_isolation_failure` **한 함수**를 통과한다. 부재와 격리 위반의 응답이 바이트 단위로 같음을 테스트가 단언하므로, 어느 한쪽에 힌트를 흘리면 red가 된다.
- **읽기 경로가 규칙 밖에 남았다.** `select()`는 빈 결과를 빈 리스트로 돌려준다. 범용 래퍼였다면 "정상적으로 비어 있는 조회"와 "RLS가 막은 0행"을 원리적으로 구분할 수 없었을 것이며, 쓰기 전용 메서드를 따로 둔 것이 그 구분을 성립시킨 유일한 수단이다(D-11).
- **분류를 빠져나가는 헬퍼를 구조적으로 막았다.** `ServiceDb`의 모든 공개 메서드는 `TABLE_HELPERS`(workspace_id 필수) 또는 `RPC_HELPERS`(`QUEUE_RPC_FUNCTIONS` 허용 목록) 중 하나여야 하며, 어느 쪽에도 없는 메서드를 추가하면 테스트가 red가 된다.

## Task Commits

1. **Task 1: service_client 팩토리 격리와 ruff banned-api 집행** — `f261f9e` (test, RED) → `59b188c` (feat, GREEN)
2. **Task 2: UserDb 쓰기 메서드와 WorkspaceForbidden** — `e48358f` (test, RED) → `a32e2f2` (feat, GREEN)
3. **Task 3: 전체 회귀 확인과 격리 계약 문서화** — `a776c2b` (docs)

## 02-04가 그대로 쓸 인터페이스

라우터를 세우기 전에 아래 세 가지를 전제하면 된다.

**쓰기 메서드 시그니처 (정확한 형태)**

```python
async def update_one(
    self,
    table: str,
    *,
    match: Mapping[str, str],
    values: Mapping[str, Any],
) -> dict[str, Any]

async def delete_one(self, table: str, *, match: Mapping[str, str]) -> dict[str, Any]
```

읽기 메서드는 `async def select(self, table: str, *, match: Mapping[str, str] | None = None, columns: str = "*", limit: int | None = None) -> list[dict[str, Any]]` 이며 0행에 예외를 던지지 않는다.

생성자는 `UserDb(client: httpx.AsyncClient, *, supabase_url: str, publishable_key: str, access_token: str)` 이다. `client`는 `app.state.http_client`를 그대로 넘기면 되고(요청마다 새 클라이언트를 만들지 말 것), `access_token`은 요청자의 JWT다. ⚠️ 여기에 service key를 넘기면 RLS가 통째로 우회된다.

**예외 import 경로**

```python
from api.errors import WorkspaceForbidden   # 0행·다중행
from api.errors import DatabaseError        # SQLSTATE를 실은 전파용
```

`WorkspaceForbidden`은 `api/db/user.py`에서만 발생하고 `api/errors.py`에서만 렌더된다. 라우터에서 이 이름이 등장하면 수용기준 grep이 깨진다.

**핸들러는 이미 등록되어 있다**

`register_error_handlers(app)`는 `api.main.create_app`이 이미 호출한다(`main.py`의 한 줄). **02-04의 라우터는 상태 코드를 직접 다루지 않는다** — `HTTPException(403)`을 던지거나 `403` 리터럴을 쓰면 D-12의 "존재 여부를 구분하지 않는다"가 라우터마다 다시 결정되고, SEC-04의 "한 곳" 조건이 깨진다. 라우터는 `UserDb`를 호출하고 예외를 그대로 통과시키면 된다.

## Files Created/Modified

### 신규

- `apps/worker/src/worker/db/service.py` — `service_client(settings)` 팩토리, `ServiceDb`(jobs 테이블 헬퍼 2종 + 큐 RPC 4종), `TABLE_HELPERS`/`RPC_HELPERS`/`QUEUE_RPC_FUNCTIONS` 분류 상수
- `apps/api/src/api/db/user.py` — `UserDb`. 쓰기 2종 + 읽기 1종, 조건 없는 쓰기 거부
- `apps/api/src/api/errors.py` — `WorkspaceForbidden`, `DatabaseError`, `FORBIDDEN_SQLSTATE`, `FORBIDDEN_BODY`, `register_error_handlers`, 단일 렌더 함수
- `apps/worker/tests/test_service_client.py` (11 tests) · `apps/api/tests/test_user_db.py` (15 tests)
- `apps/api/tests/fixtures/banned_import_violation.py.txt` — TID251 위반 픽스처
- `apps/worker/src/worker/db/__init__.py` · `apps/api/src/api/db/__init__.py` — 역할 경계 한 줄

### 수정

- `pyproject.toml` — `[tool.ruff.lint.flake8-tidy-imports.banned-api]`에 `worker.db.service`, `per-file-ignores`에 `"apps/worker/**" = ["TID251"]`
- `apps/api/src/api/main.py` — `errors.register_error_handlers(app)` 한 줄 (등록 지점 유일)

## Decisions Made

- **큐 RPC 헬퍼에는 `workspace_id`를 요구하지 않았다.** `0003`의 `claim_job`은 설계상 전역 폴링이고(`p_worker_id`, `p_types`만 받는다) `complete_job`/`fail_job`/`release_job`은 이미 점유한 잡의 id로만 동작한다. 여기에 `workspace_id`를 얹으면 **쓰이지 않는 인자**가 되어 격리를 강제하는 척만 하게 된다. 대신 이 예외가 도메인 테이블로 번지지 않도록 `QUEUE_RPC_FUNCTIONS` 허용 목록과 "모든 공개 헬퍼는 두 분류 중 하나"라는 테스트를 뒀다. 플랜의 prohibitions가 겨냥한 것은 **테이블 접근 헬퍼**이며 그 조건은 그대로 지켰다.
- **`UserDb`에는 `workspace_id`를 강제하지 않았다.** 이 경로의 격리 수단은 RLS이고, `workspaces` 테이블처럼 `workspace_id` 컬럼 자체가 없는 대상도 있다. 대신 `match` 조건을 **필수**로 만들어 조건 없는 쓰기를 요청 전에 막았다.
- **`42501`이 아닌 SQLSTATE는 403으로 뭉개지 않는다.** 커넥션 실패 같은 진짜 장애가 격리 위반으로 위장되면 원인을 찾을 수 없다(T-02-17). 핸들러는 `WorkspaceForbidden`과 `42501`만 Forbidden으로 내고 나머지는 500이다. 광범위한 `Exception` 핸들러는 두지 않았다.
- **`main.py`는 `from api import errors` 형태를 쓴다.** 수용기준이 `grep -c 'register_error_handlers' main.py == 1`을 요구하는데, `from api.errors import register_error_handlers`를 쓰면 import 줄과 호출 줄로 2가 된다. 모듈 한정 호출이 "등록 지점이 정확히 하나"라는 의도와 문자 그대로의 조건을 동시에 만족한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] 조건 없는 쓰기를 막는 가드 추가**

- **Found during:** Task 2
- **Issue:** 플랜은 `update_one`/`delete_one`이 영향 행 수만 검사하도록 지시한다. 그러나 `match`가 비면 PostgREST가 **요청자에게 보이는 모든 행**을 갱신·삭제한다. 그 결과가 우연히 1행이면 예외도 나지 않는다 — "정확히 1행" 검사만으로는 이 경로가 안 걸린다.
- **Fix:** `_require_filters()`가 빈 `match`를 요청 전에 `ValueError`로 거부한다. RLS 위반이 아니라 프로그래밍 오류이므로 `WorkspaceForbidden`이 아닌 `ValueError`다.
- **Files modified:** `apps/api/src/api/db/user.py`
- **Verification:** `test_write_without_a_match_is_refused_before_any_request` — 요청이 한 번도 나가지 않음을 함께 단언
- **Committed in:** `a32e2f2`

**2. [Rule 3 - Blocking] 존재하지 않는 모듈 때문에 ruff가 import를 third-party로 오분류**

- **Found during:** Task 1·2 (RED 커밋)
- **Issue:** 02-02 SUMMARY의 deviation 5와 같은 결함이다. `worker.db`/`api.db.user`가 디스크에 없는 RED 시점에 ruff가 이 둘을 third-party로 분류해 `I001`을 내고, pre-commit이 import 블록을 재정렬해 커밋을 거부했다. 그대로 두면 GREEN 커밋마다 무의미한 재정렬 diff가 붙는다.
- **Fix:** RED 커밋에 패키지 `__init__.py`와 모듈 헤더(docstring만, 구현 없음)를 함께 포함시켰다. 테스트는 여전히 `ImportError: cannot import name 'UserDb'`로 red이므로 RED 게이트의 의미는 유지된다.
- **Files modified:** `apps/worker/src/worker/db/__init__.py`, `apps/api/src/api/db/__init__.py`, `apps/api/src/api/db/user.py`, `apps/api/src/api/errors.py`
- **Verification:** `uv run ruff check apps` exit 0 (RED 시점), 테스트는 red
- **Committed in:** `f261f9e`, `e48358f`

**3. [Rule 1 - Bug] 테스트가 `AsyncClient.close()`를 호출**

- **Found during:** Task 1 (GREEN 검증)
- **Issue:** RED 테스트가 동기 `close()`를 불러 `AttributeError`로 실패했다 — 구현 문제가 아니라 테스트 자신의 버그다.
- **Fix:** `async with`로 바꿔 `aclose()`가 불리게 했다.
- **Files modified:** `apps/worker/tests/test_service_client.py`
- **Verification:** 11 passed
- **Committed in:** `59b188c`

**4. [Rule 3 - Blocking] ruff `S105`가 테스트의 토큰 상수를 막음**

- **Found during:** Task 2 (RED lint)
- **Issue:** `ACCESS_TOKEN = "requester-jwt"`가 하드코딩 비밀번호로 잡혔다.
- **Fix:** 상수명을 `REQUESTER_JWT`로 바꿨다. `noqa`는 쓰지 않았다.
- **Files modified:** `apps/api/tests/test_user_db.py`
- **Verification:** `uv run ruff check apps packages` exit 0
- **Committed in:** `e48358f`

---

**Total deviations:** 4 auto-fixed (2 blocking, 1 missing critical, 1 bug)
**Impact on plan:** 스코프 확대 없음. 산출물 목록과 수용기준은 플랜 그대로이며, 추가된 것은 가드 하나(빈 `match` 거부)와 테스트 상수명 변경뿐이다.

## Issues Encountered

- **`test(02-03)` 두 커밋의 제목이 테스트 개수를 잘못 적었다.** Task 1 RED는 11건(제목도 11로 amend), Task 2 RED는 제목이 "14건"이나 실제는 **15건**이다. 두 번째는 tip이 아니어서 amend하지 않았고 여기에 정확한 수를 남긴다.
- **`git commit --amend`를 한 번 `--no-verify`로 실행했다** (Task 1 RED 제목 정정). 내용은 직전에 pre-commit을 통과한 것과 바이트 단위로 동일하며, 이후 모든 커밋은 훅을 정상 통과했다. `pre-commit run --all-files`가 최종 상태에서 전부 Passed다.

## Known Stubs

없음. 다만 아래 하나는 스텁이 아니라 **의존 순서**다.

- `ServiceDb.release_job()`은 완전히 구현되어 있으나 대상 함수 `public.release_job`이 아직 DB에 없다 — 마이그레이션 `0007`(02-06, 같은 웨이브)이 만든다. 그 전에 호출하면 PostgREST가 404를 돌려준다. 근거와 함께 메서드 docstring에 `⚠️`로 명시했고, 02-07의 큐 루프가 이 함수를 처음 실제로 부른다.

## Threat Flags

없음. 이 플랜이 만든 표면(PostgREST 호출 어댑터 2종, 예외 핸들러 1종)은 전부 `<threat_model>`의 T-02-12 ~ T-02-18에 이미 등록되어 있다.

## User Setup Required

`user_setup: []` — 신규 패키지 설치도 외부 서비스 설정도 없다. `pydantic-settings`(02-02)와 `asyncpg`(02-01, 일회성 러너 의존)는 이미 정당성 확인을 거쳤고 이 플랜은 어느 것도 추가하지 않았다.

## Next Phase Readiness

**준비된 것**

- 02-04가 `workspaces` 라우터를 세워 실제 HTTP 왕복으로 403을 증명할 수 있다. 필요한 시그니처·import 경로·등록 상태는 위 "02-04가 그대로 쓸 인터페이스" 절에 문자 그대로 있다.
- 02-07의 큐 루프가 `ServiceDb`의 RPC 4종을 그대로 소비할 수 있다.
- `checklists.json`은 건드리지 않았다 — 같은 웨이브의 02-06이 그 파일의 소유자다.

**확인이 필요한 것**

- ⚠️ **이 플랜의 테스트는 전부 `MockTransport`로 PostgREST 응답을 주입한다.** "RLS 차단이 대표 표현에서 0행으로 돌아온다"와 "WITH CHECK 위반이 `code: 42501`로 온다"는 실제 왕복으로 아직 확인되지 않았다. 02-04가 라우터를 세우면 처음 검증된다.
- ⚠️ **02-01이 발견한 권한 공백이 닫히기 전에는 어떤 실제 질의도 `42501`로 떨어진다.** `0007`(02-06)의 최소권한 매트릭스가 선행해야 02-04의 실제 왕복 테스트가 의미를 갖는다.

## Self-Check: PASSED

- 신규 8개 파일 전부 디스크에 존재
- 커밋 5개 전부 git 이력에 존재 (`f261f9e`, `59b188c`, `e48358f`, `a32e2f2`, `a776c2b`)
- 플랜 `<verification>` 5개 항목 전부 통과, `uv run pytest -q` 88 passed, `pre-commit run --all-files` 전부 Passed

---
*Phase: 02-security-spine-and-shared-domain*
*Completed: 2026-08-06*
