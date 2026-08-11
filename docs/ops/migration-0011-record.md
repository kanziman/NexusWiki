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

## HNSW caveat and rollback

The vector RPC contract pins `strict_order`, `ef_search=200`, and
`max_scan_tuples=40000`. Local contract tests prove those settings are present;
they do not establish that HNSW is the chosen plan at production corpus size.
That benchmark decision remains Phase 4 Plan 04 work.

This is an immutable remote migration. Do not edit or remove `0011` after
application. To reverse its behavior, add a later migration that revokes or
replaces the RPCs and, if necessary, clears/rebuilds lexical materialization;
never delete this ledger entry or alter the applied file.
