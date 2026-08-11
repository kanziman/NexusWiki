# Migration 0011 application record

## Scope

`0011_retrieval.sql` adds the lexical writer boundary and authenticated
retrieval primitives: source/wiki lexical search, wiki vector search, the
existing source-vector primitive, and bounded wiki graph expansion.

## Local proof

On 2026-08-11 (Asia/Seoul), the following completed against the local stack:

- `supabase db reset --local` applied `0001` through `0011_retrieval.sql` in
  order with no migration error.
- `scripts/verify_retrieval_contract.sh` printed `retrieval_contract: ok`.
- `bash scripts/ci_check_retrieval_contract.sh` passed.
- `uv run pytest -q apps/worker/tests/test_handlers.py apps/worker/tests/test_service_client.py apps/api/tests/test_hybrid_search_integration.py` returned `32 passed, 1 skipped`; the skip is the integration test's local-stack guard.

The first remote attempt failed at function creation because both lexical
`ts_rank_cd(...)` expressions were unaliased while their `ORDER BY` clauses
used `rank`. The failure occurred inside the migration transaction and was not
recorded in the remote ledger. Commit `bc4fba0` corrected only those two
expressions to `AS rank`; a local read-only reproduction confirmed the aliased
query succeeds.

## Remote application

Pre-push ledger: remote ended at `0010`; local `0011` had an empty remote
column. After explicit re-authorization, this command completed:

```text
supabase db push --include-all
Finished supabase db push: 0011_retrieval.sql
```

Post-push `supabase migration list` reports every migration `0001` through
`0011` with matching local and remote values. `0011` appears exactly once.

A read-only remote `pg_proc` check recorded:

| Function group | SECURITY INVOKER | Volatility | authenticated EXECUTE | service_role EXECUTE |
|---|---:|---|---:|---:|
| search / graph RPCs | yes | stable | yes | no |
| lexical writer RPCs | yes | volatile | no | yes |

No credentials, tokens, connection strings, or query contents are recorded in
this document.

## Local HNSW JSON-plan regression proof

The Plan 06 contract uses a rollback-only fixture with 25,000 authenticated
workspace rows and 25,000 foreign-workspace decoy rows in **each** vector
relation (50,000 `source_chunks` and 50,000 `wiki_embeddings`). Its vectors are
deterministic, valid 1024-dimensional pgvector values; both relations are
analysed before observation. This cardinality makes the local planner choose the
named HNSW indexes without `enable_seqscan = off` or any other forced planner
method.

Run after a reset local stack:

```text
supabase db reset
scripts/verify_retrieval_contract.sh
bash scripts/ci_check_retrieval_contract.sh
```

The contract must print `retrieval_contract: ok` only after recursively finding
`source_chunks_embedding_idx` and `wiki_embeddings_embedding_idx` in separate
`EXPLAIN (FORMAT JSON)` plans. The observation is a direct query under
`authenticated` plus the fixture JWT claims, the same workspace/non-null
predicate, `extensions.<=>` order, clamped 1..100 limit, and transaction-local
`strict_order` / `ef_search=200` / `max_scan_tuples=40000` settings as the RPCs.
It intentionally does not claim an outer RPC Function Scan proves its internal
plan. A separate catalog/body assertion proves the deployed RPCs retain that
same ACL, volatility, GUC, predicate, ordering, and limit contract.

`pg_temp.retrieval_contract_preflight(workspace_id, manifest_identity,
expected_source_rows, expected_wiki_rows)` is available after sourcing the SQL
with `-v retrieval_contract_preflight_only=1` in an already-authenticated
benchmark session. That mode creates no fixtures and does not roll back caller
data: it fails closed on manifest/count mismatch or either missing named HNSW
scan. Plan 07 must invoke it after every exact corpus load.

The local environment version is reported by the reset/psql runtime; record its
PostgreSQL and pgvector values alongside any operational benchmark, rather than
copying them from this migration ledger.

## HNSW caveat and rollback

The vector RPC contract pins `strict_order`, `ef_search=200`, and
`max_scan_tuples=40000`. Local contract tests prove those settings are present;
they do not establish that HNSW is the chosen plan at production corpus size.
This local planner contract is a regression guard, not a production performance
claim. Operational order-mode and hardware conclusions remain benchmark work.

This is an immutable remote migration. Do not edit or remove `0011` after
application. To reverse its behavior, add a later migration that revokes or
replaces the RPCs and, if necessary, clears/rebuilds lexical materialization;
never delete this ledger entry or alter the applied file.
