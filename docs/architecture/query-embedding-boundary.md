# Query-embedding boundary decision

- **Date:** 2026-08-11
- **Owner:** NexusWiki engineering
- **Status:** Approved

## Selected topology

The worker process owns query embedding. It runs a small HTTP listener alongside
the queue loop and accepts requests only from Railway's private network. The API
calls the listener with `QUERY_EMBEDDING_INTERNAL_URL` and a dedicated
`QUERY_EMBEDDING_INTERNAL_TOKEN`; that token authenticates this internal call and
is distinct from the embedding-provider credential.

The listener has no generated public domain or public route. `railway.json`
declares this private-only deployment property, and
`scripts/ci_check_query_embedding_boundary.sh` guards it in CI.

## Required invariants

- `OPENROUTER_API_KEY` remains worker-only and is absent from API and browser
  settings.
- The API can hold only the internal URL, internal caller token, and bounded
  operational request settings.
- The worker authenticates the internal bearer token before doing provider work.
- Text size, timeout, concurrency/rate, and cost are bounded at the boundary.
- The worker returns only a validated 1024-dimensional vector and redacts
  provider failures.
- The worker boundary has no database client. Retrieval uses requester-JWT
  `UserDb.rpc` only; it uses no service-role database client.
- Tests inject a fake embedding function rather than requiring a provider key.

## Rejected alternatives

Direct browser embedding and adding `OPENROUTER_API_KEY` to `ApiSettings` are
rejected because either would expose the provider credential outside the worker
capability boundary.

## Rollback and migration cost

This is a one-way decision at this phase. Reversing it requires a Railway
network/deployment redesign, migration of the internal API contract and caller
credential, and coordinated rollout of API and worker services. The rollback
cost is therefore **high** and requires a staged migration rather than a simple
configuration revert.
