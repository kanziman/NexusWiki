# Phase 7: Integration and Ops Baseline - Pattern Map

**Mapped:** 2026-08-13  
**Files analyzed:** 12 expected create/modify paths  
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `apps/api/tests/fixtures/pipeline.py` | test fixture / utility | batch, request-response | `apps/api/tests/conftest.py` | role-match |
| `apps/api/tests/test_pipeline_e2e.py` | integration test | request-response, event-driven | `apps/api/tests/test_jobs_router.py` + `apps/worker/tests/test_handlers.py` | composite exact |
| `apps/api/tests/test_reingestion_idempotency.py` | integration test | request-response, batch | `apps/api/tests/test_sources_router.py` + parse handler tests | composite exact |
| `apps/api/tests/test_tenant_isolation_full_path.py` | integration test | CRUD, request-response, Storage | `apps/api/tests/test_workspaces_isolation.py` | exact |
| `apps/api/tests/conftest.py` | fixture support | CRUD, request-response | itself | exact extension |
| `apps/api/src/api/routers/jobs.py` | router / DTO provider | request-response, aggregate read | its `workspace_budget()` endpoint | exact |
| `apps/api/tests/test_jobs_router.py` | router integration test | request-response | itself | exact extension |
| `apps/dashboard/components/SettingsMembersPanel.tsx` (or a renamed Settings tab wrapper) | client component | request-response, stateful UI | `SettingsMembersPanel.tsx` + `JobStepper.tsx` | role-match |
| `apps/dashboard/components/OperationsPanel.tsx` | client component | request-response | `MembersList.tsx` / `JobStepper.tsx` | role-match |
| `apps/dashboard/tests/OperationsPanel.test.tsx` | component test | request-response | `apps/dashboard/tests/JobStepper.test.tsx` | exact technique |
| `scripts/benchmark_retrieval.py` | benchmark utility | batch, transform | itself | exact extension only if metrics lack per-channel percentiles |
| `docs/ops/benchmark-records/phase-07-*.json`, `docs/ops/hnsw-order-benchmark.md` | immutable evidence / decision record | batch, append-only | Phase 4 records + benchmark document | exact |

## Pattern Assignments

### `apps/api/tests/fixtures/pipeline.py` (test fixture, local-stack event-driven pipeline)

**Analog:** `apps/api/tests/conftest.py:33-45, 190-207, 349-374`; worker handler `run_*` entry points.

Put Phase 7-only helpers below a `fixtures/` module, not into production code. Reuse `local_stack`, `authed_client`, and `user_db`; keep test users function-scoped and loopback-only. `conftest.py` deliberately avoids environment-derived endpoints because `.env.local` can point at cloud.

```python
# apps/api/tests/conftest.py:349-374
@pytest.fixture
def authed_client() -> Callable[..., Any]:
    @asynccontextmanager
    async def _open(actor: TenantActor | None, **settings_overrides: Any) -> AsyncIterator[httpx.AsyncClient]:
        _assert_loopback()
        app = create_app(_local_settings(**settings_overrides), git_sha="test-sha")
        headers = {"Authorization": f"Bearer {actor.access_token}"} if actor else {}
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers) as client:
                yield client
    return _open
```

**Provider-double seam:** call `run_parse`, `run_compile`, `run_link_sync`, `handle_embed`/an extracted injected `run_embed` seam against a real `ServiceDb`; use an `httpx.MockTransport` only for URL content and deterministic OpenRouter responses. Preserve `complete_job_and_chain()`—do not patch it and do not `UPDATE jobs`.

```python
# apps/worker/src/worker/handlers/compile.py:82-104
async def handle_compile(...):
    async with service_client(settings) as db_client, openrouter_client(settings) as llm_client:
        await run_compile(ServiceDb(db_client), llm_client, settings=settings, ...)

# apps/worker/src/worker/db/service.py:674-695
async def complete_job_and_chain(self, job_id: str, *, next_type: str | None = None, next_payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    # completion and next enqueue are one transaction
    return await self._rpc("complete_job_and_chain", params)
```

**Fixture contract:** create exactly one text source through `POST /sources/text`; one file through the real API upload path (and its workspace-prefixed Storage object); one URL source whose network fetch is deterministically intercepted. Return ids, job ids, principals, deterministic compile result, and vector generator. All database/queue/Storage reads and mutations remain real local-Supabase calls.

---

### `apps/api/tests/test_pipeline_e2e.py` (OPS-02)

**Analog:** `apps/api/tests/test_jobs_router.py:27-30, 70-87`; `apps/api/src/api/routers/retrieval.py:54-93`.

Drive source creation at HTTP level, assert 202 and the returned ids, drain real jobs through handler functions/queue RPCs, then call the retrieval route using an injected deterministic `app.state.retrieval_service` or its deterministic embedding client. Assert persisted state and evidence identity—not LLM prose.

```python
# apps/api/tests/test_jobs_router.py:27-30
async def _enqueue(client, workspace_id):
    response = await client.post(TEXT_PATH.format(workspace_id=workspace_id), json=_body())
    assert response.status_code == status.HTTP_202_ACCEPTED, response.text
    return response.json()

# apps/api/src/api/routers/retrieval.py:64-77
service = getattr(request.app.state, "retrieval_service", None)
if service is None:
    service = RetrievalService(HttpQueryEmbeddingClient(...))
result = await service.retrieve(workspace_id, body.query, body.requested_k, _user_db(...))
```

**Assertions:** every terminal chain job is `succeeded` (or an explicitly expected stage state), source chunks/pages/links/embeddings exist in the workspace, `GET .../jobs` contains server-provided labels with no payload, and retrieval returns a known source/wiki evidence id. The current job UI contract purposefully narrows response data, so do not assert payload or errors.

---

### `apps/api/tests/test_reingestion_idempotency.py` (OPS-03)

**Analog:** `apps/api/src/api/routers/sources.py:175-235`; `apps/worker/src/worker/handlers/parse.py:152-230`; `apps/worker/src/worker/db/service.py:321-337`.

**Duplicate contract:** submit identical normalized text through the API and assert no row-count increase; expect the router's established duplicate response rather than simulating a duplicate insert. Capture row counts before/after for `raw_sources`, `source_chunks`, pages and embeddings where relevant.

```python
# sources.py:193-207
try:
    row = await db.insert_one(_RAW_SOURCES_TABLE, values=values)
except DatabaseError as error:
    if error.sqlstate != DUPLICATE_SQLSTATE:
        raise
    existing = await _existing_source_id(db, workspace_id=workspace_id, content_hash=str(values["content_hash"]))
    raise SourceAlreadyIngested(raw_source_id=existing) from None
```

**Shrink contract:** run a genuinely multi-chunk long source, mutate/reprocess it through the supported source/worker path with a body producing fewer chunks, then query rows ordered by `chunk_index`. Assert contiguous `range(new_count)`, no index `>= new_count`, and no embedding rows for deleted chunks. A same-sized smoke test is invalid.

```python
# parse.py:190-193
removed = await db.delete_source_chunks_from(
    workspace_id=workspace_id, raw_source_id=raw_source_id, from_index=len(rows)
)

# service.py:330-337
return await self._delete("source_chunks", params={
    "workspace_id": f"eq.{workspace_id}",
    "raw_source_id": f"eq.{raw_source_id}",
    "chunk_index": f"gte.{from_index}",
})
```

---

### `apps/api/tests/test_tenant_isolation_full_path.py` and `conftest.py` extension (OPS-04)

**Analog:** `apps/api/tests/test_workspaces_isolation.py:31-53, 61-107, 163-235`; `apps/api/tests/conftest.py:227-283, 377-392`.

Use a table-driven matrix for all nine tables—`workspaces`, `workspace_members`, `raw_sources`, `wiki_pages`, `source_chunks`, `wiki_embeddings`, `wiki_links`, `prompt_templates`, `jobs`—and Storage paths plus queue RPCs. Seed derived rows only through explicitly legitimate test setup paths, then execute all assertions through requester JWTs. Extend the principal factory for owner/editor/viewer, owner of B, non-member, and anonymous; never create a test assertion with a service-role client.

```python
# test_workspaces_isolation.py:61-82
async with authed_client(alice) as client:
    _assert_carries_a_bearer_token(client)
    response = await client.request(method, path.format(workspace_id=bob.workspace_id), ...)
assert response.status_code == status.HTTP_403_FORBIDDEN
assert response.json() == FORBIDDEN_BODY

# test_workspaces_isolation.py:218-235
async with user_db(alice) as db:
    blocked = await db.select("workspaces", match={"id": bob.workspace_id})
    own = await db.select("workspaces", match={"id": alice.workspace_id})
assert blocked == []
assert [row["id"] for row in own] == [alice.workspace_id]
```

**Matrix technique:** each row declares setup, own-control action, foreign action, and expected result shape. Run cross-tenant directions both ways. For SELECT assert `[]`; for blocked API writes/RPCs assert the canonical 403/`FORBIDDEN_BODY` where the route maps zero affected rows; for direct PostgREST `WITH CHECK`/definer denial assert SQLSTATE `42501` rather than merely “an exception.” Include anonymous 401 cases separately so lack of credentials cannot satisfy a forbidden assertion.

**Storage:** exercise API-generated workspace-prefixed objects. Foreign GET/list/delete must use user JWTs. The worker file parser's first-segment check is a second boundary, not permission to seed/inspect Storage with service role.

```python
# parse.py:106-124
if storage_path.split("/", 1)[0] != workspace_id:
    raise StorageObjectMissing()
```

---

### `scripts/benchmark_retrieval.py` and append-only evidence (OPS-05)

**Analog:** `scripts/generate_retrieval_benchmark_corpus.py:29-35, 102-158`; `scripts/benchmark_retrieval.py:174-202`.

Do not introduce a benchmark or synthetic-vector generator: the canonical generator validates 1024 dimensions and 25,000 target + 25,000 decoy rows per relation, loads labels before decoys, runs `ANALYZE`, and restricts cleanup to its fixed workspace.

```python
# generate_retrieval_benchmark_corpus.py:29-35
if (doc.get("dimension"), doc.get("target_rows_per_relation"), doc.get("decoy_rows_per_relation")) != (1024, 25000, 25000):
    raise ValueError("benchmark_manifest_cardinality_mismatch")

# benchmark_retrieval.py:185-191
response = asyncio.run(service.retrieve(workspace, query["query"], query["requested_k"], db))
channels = {name: _channel_record(response.meta[name], reverse) for name in CHANNELS}
record = {..., "query_results": results, "metrics": _metrics(results)}
_validate_record(record)
```

**Required extension:** add per-channel latency percentile aggregation only if absent from the record. Preserve actual `RetrievalService.retrieve()` and its five channel envelopes; do not query a synthetic path directly or alter `strict_order`, graph policy, weights, k, or candidate limits.

Write each successful local arm to a new immutable `docs/ops/benchmark-records/phase-07-*.json`; the runner already rejects overwriting output. Record the EXPLAIN plan, Git SHA, corpus/golden/manifest hashes, seed, DB identity, repeat count, policy content/hash, and comparator output. For strict-versus-relaxed comparison, execute consecutive arms from the same clean commit and invoke `compare-order-records`; it rejects unmatched pins/policy and invalid mode pairs.

```python
# benchmark_retrieval.py:197-202
if _pins(left) != _pins(right) or left["policy_content"] != right["policy_content"]:
    raise VerificationError("order_pair_pin_or_policy_mismatch")
if {left.get("order_mode"), right.get("order_mode")} != {"strict_order", "relaxed_order"}:
    raise VerificationError("order_pair_mode_invalid")
```

---

### `apps/api/src/api/routers/jobs.py` and `apps/api/tests/test_jobs_router.py` (OPS-06 API)

**Analog:** `apps/api/src/api/routers/jobs.py:27-55, 87-110, 177-200`; `apps/api/tests/test_jobs_router.py:33-53, 184-196`.

Add one `GET /workspaces/{workspace_id}/operations` endpoint in this router, using the existing requester-JWT `UserDb` factory. Reuse exact `CHAIN_ORDER` and `STEP_LABELS` server constants and current budget semantics: UTC first-of-month, max 1,000 usage records, display-only `authoritative: false`. Return a fixed DTO with budget, five stage rows (queued/running/dead), and `observed_at`; do not return job `payload`, `last_error`, usage metadata, provider, or model.

```python
# jobs.py:27-40
CHAIN_ORDER = ("parse", "compile", "link_sync", "embed", "conflict_check")
STEP_LABELS = {"parse": "원문 파싱", "compile": "위키 컴파일", ...}

# jobs.py:184-200
cap_rows = await db.select("workspaces", match={"id": str(workspace_id)}, columns="monthly_budget_micros", limit=1)
usage = await _usage_rows_since(db, workspace_id=workspace_id, month_start=month_start)
return {"cap_micros": cap_micros, "spent_micros": spent_micros, "remaining_micros": cap_micros - spent_micros, "truncated": len(usage) == _BUDGET_USAGE_LIMIT, "authoritative": False}
```

**Authorization:** establish an editor-or-owner helper on the server (use membership/RLS rows, not dashboard role inference). Test unauthenticated 401, viewer 403, foreign/non-member 403 or indistinguishable empty response according to the selected router contract, editor and owner 200, fixed stage ordering/labels, zero counts, aggregate/truncation behavior, and absence of sensitive keys. Extend the existing all-job-routes credential matrix with the new path.

---

### `apps/dashboard/components/SettingsMembersPanel.tsx`, `OperationsPanel.tsx`, and `OperationsPanel.test.tsx` (OPS-06 UI)

**Analogs:** `SettingsMembersPanel.tsx:21-56`; `api-client.ts:48-104`; `JobStepper.tsx:176-186`; `apps/dashboard/tests/JobStepper.test.tsx`.

Retain the existing Settings route/page and evolve the client wrapper into a keyboard-operable member/operations tab container. Receive the current member role from the established Settings data path (or resolve it server-side before props): only owner/editor render the Operations tab and only those roles initiate the request. The 640px workaround is mandatory.

```tsx
// SettingsMembersPanel.tsx:25-56
const [refreshToken, setRefreshToken] = useState(0);
return (
  <div className="flex flex-col gap-xl" style={{ maxWidth: "640px" }}>
    ...
  </div>
);

// api-client.ts:48-62
export async function apiFetch<T>(path: string, init?: ApiFetchInit): Promise<T> {
  const { data: { session } } = await createClient().auth.getSession();
  if (!session) throw new Error("apiFetch called without an active session");
  // fresh bearer token for every request
}
```

`OperationsPanel` owns initial fetch plus explicit refresh state. On initial loading, render neutral skeleton cards/rows. On manual refresh retain last successful snapshot, set `aria-busy`, disable the 44px-or-larger icon-plus-text `운영 현황 새로고침` control, and on failure show only the contracted Korean message. Render Korean-only text, local formatted amounts/timestamp, cap-zero branch without a percentage bar, `truncated` warning, all five server-order rows, and an internally horizontally-scrollable stage container at narrow widths. Do not poll, retry/cancel jobs, reconstruct status labels, or show raw API errors.

**Component tests:** mock `apiFetch` and exercise owner/editor initial load, viewer absent/no request, refresh success timestamp, refresh failure retaining old DOM data, disabled/`aria-busy`, cap-zero, partial aggregate warning, empty pipeline note, server-provided labels, and error copy. Follow current Testing Library interaction style; dashboard verification remains `pnpm --dir apps/dashboard test && pnpm --dir apps/dashboard typecheck`.

## Shared Patterns and Contracts

### Local integration safety

- All DB-dependent tests use the loopback-only local fixture and skip visibly when the stack is down (`conftest.py:190-207`). The pytest gate runs with `-rs`; a skip is not validation.
- Use real Postgres/RLS/queue/Storage/HNSW. Mock only OpenRouter/embedding and URL transport at their client seams.
- Tests must not import `worker.db.service` into API production code: worker service role bypasses RLS; API routes construct `UserDb` from `credentials.credentials` (`sources.py:114-138`).

### Queue correctness

- Job state transitions are RPC-owned. Drain helpers must claim then complete/fail/cancel through `ServiceDb` methods; never mutate `public.jobs` directly.
- `complete_job_and_chain()` is transactional and repeat-safe (`service.py:674-695`); calling a handler twice must not create an extra chained job.

### Tenant/RLS assertion discipline

- Cross-tenant reads normally yield zero rows; routes can map blocked writes to canonical 403. Do not collapse those two outcomes.
- Every foreign deny case needs a same-workspace allowed control, both cross directions, and a separate anonymous 401 case.
- Use service role only for tightly-scoped test setup that has no requester-path equivalent; never use it for the assertion action or to read a foreign Storage object.

### Operations DTO/UI boundary

- API owns stage types, Korean labels, aggregation, membership authorization, and suppression of sensitive internals.
- Dashboard owns rendering, roles-as-defense-in-depth, local presentation, and manual refresh UX. It must call `apiFetch`, which fetches the current session for each request and safely parses error bodies.

### Benchmark evidence integrity

- Existing corpus/golden hashes and fixed 50k-per-relation corpus are authoritative. Preserve policy defaults.
- Records are append-only; never edit/reuse an output name. Comparison requires the same clean Git SHA as well as all data and runner pins.

## Verification Commands

```bash
UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q \
  apps/api/tests/test_pipeline_e2e.py \
  apps/api/tests/test_reingestion_idempotency.py \
  apps/api/tests/test_tenant_isolation_full_path.py \
  apps/api/tests/test_jobs_router.py

pnpm --dir apps/dashboard test && pnpm --dir apps/dashboard typecheck

UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -rs
```

For OPS-05, start local Supabase, execute the pinned benchmark arms and comparator under one clean commit, and append the records before updating `docs/ops/hnsw-order-benchmark.md` with the plan/result interpretation.
