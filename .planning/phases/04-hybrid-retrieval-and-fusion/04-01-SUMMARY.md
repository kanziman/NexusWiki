---
phase: 04-hybrid-retrieval-and-fusion
plan: 01
status: complete
---

# Phase 4 Plan 01 Summary

The approved one-way query-embedding topology is recorded in
`docs/architecture/query-embedding-boundary.md`. The worker owns a private,
bearer-authenticated and bounded query-vector endpoint; the API holds only the
dedicated internal URL/token and request bounds, never a provider credential.

Implemented the first retrieval tracer:

- immutable versioned retrieval policy and rank-only reciprocal-rank fusion;
- canonical source/wiki evidence DTOs, deterministic ties, deduplication, and
  per-channel contribution metadata;
- authenticated evidence-only retrieval route using requester-JWT `UserDb.rpc`;
- dense failure degrades to lexical retrieval and cancellation is preserved;
- private-network Railway declaration and CI boundary assertion.

## Verification

Passed on 2026-08-11:

```text
uv run ruff check …                         All checks passed
uv run pytest -q …                          43 passed in 0.14s
bash scripts/ci_check_query_embedding_boundary.sh
git diff --check
```

The focused suite includes the new policy/RRF, worker query-embedding, and API
retrieval tests plus relevant existing settings and health contracts.

## Deviation

The execution sandbox cannot create `.git/index.lock`, so atomic task commits
and this summary commit must be performed by the parent executor with the same
scoped file sets. No code-scope deviation was made.
