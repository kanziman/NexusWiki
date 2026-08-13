# Phase 2: Security Spine and Shared Domain - Pattern Map

**Mapped:** 2026-08-06
**Files analyzed:** 22 new/modified files
**Analogs found:** 18 / 22

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/core/src/nexuswiki_core/settings.py` | config | transform | `packages/core/src/nexuswiki_core/logging.py` | role-match (same package, same header/doc style) |
| `packages/core/src/nexuswiki_core/tokenizer.py` | utility | transform | `packages/core/src/nexuswiki_core/logging.py` | role-match |
| `packages/core/src/nexuswiki_core/slug.py` | utility | transform | `packages/core/src/nexuswiki_core/logging.py` | role-match |
| `packages/core/pyproject.toml` (modify: add `pydantic-settings`) | config | — | itself (existing pinned-dep style) | exact |
| `apps/api/src/api/settings.py` (`ApiSettings`) | config | transform | `packages/core/.../logging.py` + `apps/api/src/api/health_check.py` | role-match |
| `apps/api/src/api/main.py` (modify) | config/entrypoint | request-response | itself (`create_app`/`lifespan` already exist) | exact |
| `apps/api/src/api/routers/health.py` (modify: drop `os.environ`) | route | request-response | itself | exact |
| `apps/api/src/api/routers/workspaces.py` | route | CRUD | `apps/api/src/api/routers/health.py` | role-match (only router in repo) |
| `apps/api/src/api/db/user.py` (`UserDb`) | service | CRUD | `apps/api/src/api/health_check.py` | role-match (adapter + frozen dataclass result) |
| `apps/api/src/api/errors.py` (`WorkspaceForbidden` + handler) | middleware | request-response | **none** | no analog |
| `apps/worker/src/worker/settings.py` (`WorkerSettings`) | config | transform | `packages/core/.../logging.py` | role-match |
| `apps/worker/src/worker/db/service.py` | service | CRUD | `apps/worker/src/worker/rtt.py` (explicit-kwargs factory style) | partial |
| `apps/worker/src/worker/queue.py` (claim→complete loop) | service | event-driven | `apps/worker/src/worker/__main__.py` (SIGTERM loop) + `rtt.py` | role-match |
| `apps/worker/src/worker/handlers/noop.py` | service | event-driven | **none** | no analog |
| `apps/worker/src/worker/__main__.py` (modify) | entrypoint | event-driven | itself | exact |
| `apps/worker/src/worker/queue_baseline.py` (noop RTT percentiles) | utility | batch | `apps/worker/src/worker/rtt.py` | **exact** |
| `supabase/migrations/0007_*.sql` | migration | — | `supabase/migrations/0003_jobs.sql` (functions) + `0005_storage.sql` (recent style) | **exact** |
| `.github/workflows/ci.yml` | config/CI | — | **none** (`.github/` does not exist) | no analog |
| `pyproject.toml` (modify: `TID`, `testpaths`) | config | — | itself | exact |
| `apps/api/tests/test_workspaces_isolation.py` (+ fixtures) | test | request-response | `apps/api/tests/test_health.py` | role-match |
| `packages/core/tests/test_tokenizer.py`, `test_slug.py`, `test_settings.py` | test | — | `packages/core/tests/test_logging_redaction.py` | **exact** |
| `apps/worker/tests/test_queue.py` | test | event-driven | `apps/worker/tests/test_rtt.py` | **exact** |
| `docs/ops/db-transport-spike.md`, `docs/ops/reap-timeout-baseline.md` | doc | — | `docs/ops/rtt-baseline.md` | **exact** |

---

## Pattern Assignments

### `packages/core/src/nexuswiki_core/{settings,tokenizer,slug}.py` (utility/config, transform)

**Analog:** `packages/core/src/nexuswiki_core/logging.py`

**Module header + import pattern** (lines 1-14) — Korean docstring, task ID, decision-key citation, `from __future__ import annotations`:
```python
"""공용 구조화 로깅 설정.

관련 태스크: P0-INIT-02
설계 근거: 01-CONTEXT.md > D-13
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import orjson
import structlog
```
Phase 2 modules cite `02-CONTEXT.md > D-07` (settings), `> D-19` (tokenizer), `> D-20` (slug); the transport decision cites `checklists.json > decisions.db_transport` (D-05 puts it in the ledger, not the phase file).

**Module-level constant pattern** (lines 16-34) — versioned/frozen constants live at module top, uppercase, typed:
```python
REDACTED_KEYS: frozenset[str] = frozenset({...})
REDACTION_PLACEHOLDER = "[REDACTED]"
```
→ `TSV_TOKENIZER_VERSION = "bigram-nfkc-cf-v1"` and `SLUG_VERSION = "slug_v1"` follow this exact shape (compare `RTT_WARMUP_COUNT: int = 5` in `rtt.py:15-17`).

**Private helper + public API split** (lines 37-64) — `_redact_mapping`/`_redact_value` private, `redact_sensitive` public with one-line Korean docstring:
```python
def _redact_value(value: Any) -> Any: ...

def redact_sensitive(...) -> MutableMapping[str, Any]:
    """민감 키의 값을 로그 렌더링 전에 마스킹한다."""
    # ⚠️ denylist에서 키를 빠뜨리면 로그에 값이 조용히 새어 나간다.
    # 키 목록 자체를 단위 테스트로 고정한다. 근거: 01-CONTEXT.md > D-13.
```
→ `normalize()`/`bigram()` mirror this: `bigram()` carries the `⚠️` comment for the "정규화되지 않은 입력 = 조용한 색인/질의 불일치" footgun (SPEC R8, D-19).

**Keyword-only public signature** (line 67) — every public core function uses `*` to force named args:
```python
def configure_logging(*, environment: str, log_level: str) -> None:
```
→ `slugify(*, title: str, taken: Collection[str]) -> str`.

**Dependency pinning** — `packages/core/pyproject.toml:9-12` pins exact versions (`orjson==3.11.9`, `structlog==26.1.0`). Add `pydantic-settings==<exact>` the same way, and register it in `apps/api`/`apps/worker` only if they import it directly.

---

### `apps/api/src/api/db/user.py` (`UserDb`) (service, CRUD)

**Analog:** `apps/api/src/api/health_check.py`

**Adapter header naming the swap point** (lines 1-13):
```python
"""Supabase REST를 통한 얇은 DB readiness 어댑터.

관련 태스크: P0-INIT-02
설계 근거: 01-CONTEXT.md > D-11
(Phase 1은 DB 트랜스포트를 결정하지 않는다 — 교체 지점은 이 파일 한 곳)
"""

from dataclasses import dataclass
from time import monotonic

import httpx

READINESS_TIMEOUT_SECONDS: float = 2.0
```
→ `UserDb` is the Phase 2 continuation of this exact file's role: the transport chosen by R6 lands here and in `health_check.py`, and nowhere else.

**Frozen dataclass result + injected client** (lines 16-29) — the client is a parameter, never a module global; keyword-only config:
```python
@dataclass(frozen=True)
class ReadinessResult:
    ok: bool
    reason: str | None
    elapsed_ms: float


async def check_db_roundtrip(
    client: httpx.AsyncClient,
    *,
    supabase_url: str,
    publishable_key: str,
    timeout_seconds: float = READINESS_TIMEOUT_SECONDS,
) -> ReadinessResult:
```
→ Same shape for `service_client(settings: WorkerSettings)` (D-08: argument-required factory, no module singleton) and for `UserDb(conn_or_client, *, ...)`.

**Classify-then-return error pattern** (lines 32-47) — every failure mode gets a *named string reason*, not a raw exception leak:
```python
    try:
        response = await client.get(...)
    except httpx.TimeoutException:
        return _result(started, ok=False, reason="db_roundtrip_timeout")
    except httpx.HTTPError:
        return _result(started, ok=False, reason="db_unreachable")
    if not response.is_success:
        return _result(started, ok=False, reason=f"db_status_{response.status_code}")
```
→ `update_one()`/`delete_one()` invert this: they *raise* `WorkspaceForbidden` on `affected == 0` **and** on `affected > 1` (SPEC AC), because a return-value contract would let a caller ignore it. Read methods keep the plain-return contract (D-11).

**⚠️ comment placement** (lines 33-34) — the footgun comment sits immediately above the line it protects and cites its decision:
```python
        # ⚠️ 호출별 타임아웃이 없으면 readiness가 매달려 Railway가 프로세스를
        # 교체하지 못한 채 무한 대기한다. 근거: 01-CONTEXT.md > D-11.
```

---

### `apps/api/src/api/routers/workspaces.py` (route, CRUD)

**Analog:** `apps/api/src/api/routers/health.py` (the only router in the repo)

**Router module shape** (lines 1-15):
```python
"""프로세스 생존 여부만 노출하는 liveness 라우터.

관련 태스크: P0-INIT-02
설계 근거: 01-SPEC.md > R6
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.health_check import check_db_roundtrip

router = APIRouter()
```
Router is a module-level `router = APIRouter()` object, registered in `main.py:35` via `app.include_router(health_router)`.

**Status-code pattern to deliberately BREAK** (lines 31-34, 43-49) — `health.py` builds `JSONResponse(status_code=503, ...)` inline:
```python
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": f"missing_env:{key}"},
            )
```
→ ⚠️ `workspaces.py` must **not** copy this. SPEC AC "라우터 모듈에 403 상태 코드 리터럴이 없다" requires the router to raise `WorkspaceForbidden` (raised inside `UserDb`) and let a single `app.add_exception_handler` render 403. Copy the *module shape* from `health.py`, not its inline-status-code habit.

**`os.environ` reads to remove** — `health.py:7,22,28-39` and `main.py:9,22-25` read `os.environ` directly. R1 replaces all of these with `request.app.state.settings` / injected `ApiSettings`.

**Settings injection point** — `apps/api/src/api/main.py:20-36`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(
        environment=os.environ.get("ENVIRONMENT", "development"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(2.0))
    try:
        yield
    finally:
        await app.state.http_client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(health_router)
    return app
```
→ `create_app(settings: ApiSettings)` stores `app.state.settings`, feeds `configure_logging(environment=settings.ENVIRONMENT, log_level=settings.LOG_LEVEL)`, and registers the 403 exception handler here (single registration point, D-13). ⚠️ Module-level `app = create_app()` at line 39 is imported by `apps/api/tests/test_health.py:10` — changing the signature requires a default or a test-side update.

---

### `apps/worker/src/worker/queue.py` + `handlers/noop.py` (service, event-driven)

**Analog:** `apps/worker/src/worker/__main__.py`

**SIGTERM / graceful-shutdown skeleton to extend** (lines 22-33, 69-72):
```python
async def main() -> None:
    configure_logging(
        environment=os.environ.get("ENVIRONMENT", "development"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop.set)
    loop.add_signal_handler(signal.SIGINT, stop.set)

    bind_job_context(job_id="bootstrap", workspace_id="bootstrap")
    logger = get_logger(__name__)
    ...
        await stop.wait()
        logger.info("worker.stopped")
    finally:
        clear_job_context()
```
→ D-18: `await stop.wait()` becomes the claim loop's exit condition; on `stop` set, stop claiming, `asyncio.wait_for(current_job, timeout=GRACE)` and on timeout call `release_job(p_job_id)`. `bind_job_context(job_id=..., workspace_id=...)` per claimed job, `clear_job_context()` in the `finally` — that contextvar pairing is already established here.

**Structured event naming** (lines 36, 44, 58, 68) — dotted `worker.<event>` names with kwargs, `logger.exception` for failures:
```python
    logger.info("worker.rtt_measured", p50_ms=result.p50_ms, sample_count=..., git_sha=git_sha)
    ...
    except Exception:
        logger.exception("worker.rtt_failed", git_sha=git_sha)
```
→ `worker.job_claimed` / `worker.job_completed` / `worker.job_released` / `worker.job_dead_lettered`.

**Config-missing guard style** (lines 40-46) — worker logs a skip reason rather than crashing on optional config; R1/D-10 changes this for *required* keys to a fail-fast that names the key.

---

### `apps/worker/src/worker/queue_baseline.py` (utility, batch) — R11 reap baseline

**Analog:** `apps/worker/src/worker/rtt.py` — copy this file almost verbatim, swapping the HTTP roundtrip for a `claim_job`→`complete_job` roundtrip.

**Warmup/sample separation + injectable clock** (lines 13-17, 43-67):
```python
_perf_counter = time.perf_counter

RTT_WARMUP_COUNT: int = 5
RTT_SAMPLE_COUNT: int = 50
RTT_REQUEST_TIMEOUT_SECONDS: float = 5.0

    cold_first_ms = await request_once()
    for _ in range(warmup_count):
        await request_once()

    samples: list[float] = []
    for _ in range(sample_count):
        if (elapsed := await request_once()) is not None:
            samples.append(elapsed)
    samples.sort()

    # Nearest-rank percentile: rank=ceil(p*N), converted to a zero-based index.
    def percentile(percent: float) -> float | None:
        if not samples:
            return None
        return samples[max(0, math.ceil(percent * len(samples)) - 1)]
```
⚠️ `_perf_counter` as a module-level alias exists solely so tests can `monkeypatch.setattr(rtt, "_perf_counter", ...)` (`apps/worker/tests/test_rtt.py:57`). Keep that alias. SPEC R11 needs ≥200 samples for p99 → set `SAMPLE_COUNT` accordingly and add a `p99_ms` field to the frozen result dataclass (lines 20-27).

---

### `supabase/migrations/0007_*.sql` (migration)

**Analogs:** `supabase/migrations/0003_jobs.sql` (queue functions), `0005_storage.sql` (most recent, Phase 1 header style)

**File header** (`0003_jobs.sql:1-21`) — banner rule, task ID, decision key, ASCII state diagram when a state machine is encoded:
```sql
-- =============================================================================
-- NexusWiki 0003: 잡 큐
--
-- 관련 태스크: P1-DB-03 (소비자는 P2-JOB-01 워커, 생산자는 P2-ING-01 수집 API)
-- 설계 근거:  checklists.json > decisions.job_queue
--
-- 상태 전이
--
--   queued ──claim──> running ──complete──> succeeded
--     ^                  │
--     └────────────────────────── reap (락 타임아웃) ───────────────────────────┘
-- =============================================================================
```
→ `0007` header cites `checklists.json > decisions.db_transport` (D-05) for section 1 and `02-CONTEXT.md > D-18/D-21` for sections 2-6, and redraws the state diagram with the `release_job` arrow (`running ──release──> queued`, attempts−1).

**Numbered section rule lines** (`0003:24-26`, `91-98`, `213-220`) — D-21's six sections use exactly this:
```sql
-- -----------------------------------------------------------------------------
-- 1. jobs
-- -----------------------------------------------------------------------------
```

**Queue function pattern** — `release_job()` copies `complete_job()` (`0003:135-148`) verbatim except for the `attempts` decrement and target status:
```sql
create or replace function public.complete_job(p_job_id uuid)
returns public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs
  set status     = 'succeeded',
      last_error = null,
      locked_at  = null,
      locked_by  = null
  where id = p_job_id and status = 'running'
  returning *;
$$;
```
⚠️ Three invariants this excerpt encodes and `release_job`/`complete_job_and_chain` must preserve:
1. `where ... and status = 'running'` — makes re-calling on an already-`succeeded` job a **0-row no-op, not an exception** (SPEC R10 AC "이미 done인 잡에 complete_job을 불러도 예외가 나지 않는다" is already satisfied by this clause; keep it).
2. Clearing both `locked_at` and `locked_by` is mandatory — `jobs_lock_consistency` CHECK (`0003:65-68`) rejects the row otherwise.
3. `language sql volatile set search_path = public`, param prefix `p_`.

For `release_job`: `set status='queued', attempts = attempts - 1, locked_at=null, locked_by=null where id=p_job_id and status='running' and locked_by = p_worker_id` — the `locked_by` predicate is what makes the R10 AC "다른 워커의 진행을 덮어쓰지 않는다" true. `attempts >= 0` CHECK (`0003:47`) guards the decrement.

**Permission block** (`0003:213-229`) — every new function repeats this pair; Supabase grants EXECUTE to `anon`/`authenticated` by default:
```sql
revoke all on function public.claim_job(text, text[]) from public, anon, authenticated;
grant execute on function public.claim_job(text, text[]) to service_role;
```
→ `release_job` / `complete_job_and_chain` are `service_role`-only. The R6 search function is the opposite: if RPC wins, it is `security invoker` + `grant execute ... to authenticated` (see below).

**`SECURITY INVOKER` search function with GUCs** — the R6 winner-path function combines `0004`'s helper form with per-function `set`:
```sql
create or replace function public.is_workspace_member(ws_id uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$ ... $$;

comment on function public.is_workspace_member(uuid) is
  '호출자가 해당 워크스페이스 멤버인지. RLS 정책 전용 — 재귀 차단용 SECURITY DEFINER.';

grant execute on function public.is_workspace_member(uuid) to authenticated;
```
⚠️ `0004:36-38` states *why* each modifier exists (`stable` → per-row re-eval; `set search_path` → privilege escalation). The R6 function needs `set hnsw.iterative_scan`, `set hnsw.ef_search`, `set hnsw.max_scan_tuples` in the same modifier block, and — per `0002:30` — every pgvector reference schema-qualified (`extensions.vector(1536)`, `extensions.vector_cosine_ops`).

**`comment on function`** is mandatory for every public function (`0003:130`, `0004:88-91`, `0005:35`): contract + caller restriction, one Korean sentence.

**Single-transaction wrapping** (SPEC R7 AC) — no existing migration wraps itself in `begin`/`commit`; `0007` is the first. Note this as a deliberate deviation in `checklists.json > <task>.deviations_from_plan` per the ledger convention.

---

### Tests

**Analog for core module tests:** `packages/core/tests/test_logging_redaction.py`

```python
"""공용 로깅의 민감정보 마스킹 회귀 테스트."""

from nexuswiki_core.logging import (
    REDACTED_KEYS,
    REDACTION_PLACEHOLDER,
    ...
)


def test_redacted_keys_include_required_sensitive_fields() -> None:
    required = {"password", "authorization", ...}
    assert required <= REDACTED_KEYS
```
Korean one-line module docstring; long descriptive `test_<behavior>` names; `-> None` on every test; no classes; plain `assert`. The "pin the constant itself with a test" idea maps directly onto SPEC R1's `ApiSettings.model_fields` assertion:
```python
def test_api_settings_cannot_hold_secret_keys() -> None:
    forbidden = {"SUPABASE_SECRET_KEY", "DATABASE_URL", "OPENROUTER_API_KEY", "OPENAI_API_KEY"}
    assert forbidden.isdisjoint(ApiSettings.model_fields)
```

**Analog for HTTP-roundtrip tests:** `apps/api/tests/test_health.py:13-30`
```python
@asynccontextmanager
async def app_client():
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_health_does_not_require_supabase_env(monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
```
→ the SEC-06 cross-tenant table drives off this `app_client()` helper. ⚠️ There is **no `conftest.py` anywhere in the repo** — the 2-workspace × 2-user fixtures (D-14) are the first shared fixtures; put them in `apps/api/tests/conftest.py` and make each fixture create + tear down unique rows (SPEC AC "실행 순서·병렬성에 무관").

Parametrization table shape (new — no existing analog for `@pytest.mark.parametrize` in this repo; D-14 requires "행만 추가"):
```python
CROSS_TENANT_CASES = [("PATCH", "/workspaces/{other_id}"), ("DELETE", "/workspaces/{other_id}")]
```

**Analog for worker tests:** `apps/worker/tests/test_rtt.py` — monkeypatched clock (`monkeypatch.setattr(rtt, "_perf_counter", lambda: next(clock))`, line 57), `fields(result)` set assertions (lines 42-49), `pytest.approx` for percentiles. ⚠️ These tests are currently **not collected** — root `pyproject.toml:22` `testpaths` omits `apps/worker/tests` (SPEC R12).

---

### `docs/ops/db-transport-spike.md` and the reap baseline doc

**Analog:** `docs/ops/rtt-baseline.md` — copy its section skeleton exactly:

```markdown
# Railway–Supabase RTT 기준선

## 측정 일시
- 2026-08-05 15:50:30 KST
- 배포 커밋 `aaa5b65691b7b21a5b88c40dfd1c07f696fdb755`

## 방법
측정 주체는 개발자 머신이 아닌, `asia-southeast1` 리전에서 실행 중인 배포된 Railway
`worker` 서비스다. ...
SPEC R9는 배포된 `api`에서 측정하도록 요구하지만, 같은 SPEC 경계는 ... 이 편차의 근거는
`01-CONTEXT.md > D-14`다.

## 결과
| 콜드 첫 요청(ms) | p50(ms) | p95(ms) | N(표본 수) | 워밍업 횟수 | 실패 수 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 851.138 | 29.093 | 37.610 | 50 | 5 | 0 |
```
Sections: `## 측정 일시` (timestamp + commit SHA) → `## 방법` (who measured, from where, and any SPEC deviation with its decision citation) → `## 결과` (right-aligned numeric table) → limits/downstream consumer paragraph. The last paragraph of the analog ("이 프로브는 worker 기동 시 한 번만 실행된다") is exactly where R11's mandated limitation sentence ("이 값은 noop 기준이며 LLM 잡 p99는 Phase 3에서 재측정한다") and R6's per-condition measured values go — the prohibitions table forbids omitting them.

---

## Shared Patterns

### File header (every new file, SQL and Python)
**Source:** `packages/core/src/nexuswiki_core/logging.py:1-5`, `supabase/migrations/0003_jobs.sql:1-7`
**Apply to:** all new files
```python
"""<한 줄 한국어 요약>.

관련 태스크: <TASK-ID>
설계 근거: 02-CONTEXT.md > D-XX      # 페이즈 한정 결정
설계 근거: checklists.json > decisions.db_transport   # 프로젝트 수명 결정
"""
```
Never restate the rationale — point at the ledger. Lifetime picks the layer.

### `⚠️` footgun comment
**Source:** `apps/api/src/api/health_check.py:33-34`, `0004_rls_policies.sql:17`, `0003_jobs.sql:186-188`
**Apply to:** every place where an omission fails **silently**
Sits directly above the guarded line, states what breaks, cites the decision. Phase 2's mandatory ones: asyncpg GUC omission → silent isolation loss (D-04); unnormalized `bigram()` input → silent index/query mismatch (D-19); `service_client` without `workspace_id` filter → BYPASSRLS cross-tenant read.

### Secret handling
**Source:** `packages/core/src/nexuswiki_core/logging.py:16-33`
**Apply to:** `WorkerSettings`, `service_client`, CI grep
`REDACTED_KEYS` already contains `supabase_secret_key`, `openrouter_api_key`, `openai_api_key`, `database_url` (lines 28-31) — the `WorkerSettings` field names must casefold to these exact strings or the redaction silently stops covering them. Add the assertion to `test_logging_redaction.py`.

### Config fail-fast
**Source:** `apps/api/src/api/routers/health.py:28-34` (current, env-loop form)
**Apply to:** `BaseAppSettings` validation
The existing loop names the missing key (`f"missing_env:{key}"`). R1 moves this to boot time; the message must still name the key, and empty string counts as missing (`if not os.environ.get(key)` already has that semantic — preserve it in the pydantic validator).

### Ruff / tooling
**Source:** root `pyproject.toml:30-35`
```toml
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "ASYNC", "S"]

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["S101"]
"**/__main__.py" = ["S104"]
```
→ append `"TID"` to `select`; add `[tool.ruff.lint.flake8-tidy-imports.banned-api]` for `worker.db.service`; add `"apps/worker/**" = ["TID251"]` to `per-file-ignores`; add `"apps/worker/tests"` to `testpaths` (line 22).

### Pre-commit scoping
**Source:** `.pre-commit-config.yaml:1`
```yaml
# 훅 범위를 비우면 SQL·문서·원장까지 대규모로 재포맷되므로 각 언어 소스로 한정한다.
```
Hooks are path-scoped by `files:` regex. The CI workflow runs `pre-commit run --all-files` unchanged (SPEC R3 job a).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.github/workflows/ci.yml` | config/CI | — | `.github/` does not exist; no workflow, action, or CI script anywhere in the repo. Use SPEC R3's four-job list as the spec and the prohibition "no `continue-on-error` / `\|\| true` / `set +e` / empty-result-passes" as the constraint. Dashboard build/grep target is `apps/dashboard/.next` — verify the path exists before grep, and treat absence as fail. |
| `apps/api/src/api/errors.py` (`WorkspaceForbidden` + `add_exception_handler`) | middleware | request-response | No custom exception class or FastAPI exception handler exists. `health.py` returns `JSONResponse` inline instead. Register the handler in `create_app()` (`main.py:33-36`) so there is exactly one registration site (D-13). |
| `apps/worker/src/worker/handlers/noop.py` + handler registry | service | event-driven | No handler registry exists. Contract is given by `0003_jobs.sql:31-36`: unknown `type` → straight to `dead` with `last_error`. |
| Spike harness (`scripts/` or `supabase/spike/`) — synthetic corpus SQL + EXPLAIN assertions | test/migration | batch | No SQL script directory and no automated SQL test exist (`0001`~`0006` were verified ad hoc via `psql` per STACK.md). Follow migration SQL style anyway; the EXPLAIN assertion becomes the RTV-08 regression prototype (do not write it as throwaway). |

## Metadata

**Analog search scope:** `apps/api/`, `apps/worker/`, `packages/core/`, `supabase/migrations/`, `docs/ops/`, repo-root config
**Files scanned:** 21 (all Python source + tests, 3 migrations, 5 config files, 1 ops doc)
**Pattern extraction date:** 2026-08-06
