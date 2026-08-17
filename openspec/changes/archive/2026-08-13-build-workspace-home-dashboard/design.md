## Context

The home route is a placeholder; the workspace layout already validates the URL through RLS. Sources and wiki pages are existing workspace-scoped records.

## Goals / Non-Goals

**Goals:** reuse existing RLS reads and routes for a concise first-use and returning-user home.

**Non-Goals:** new backend models, analytics, graph controls, or operations dashboard duplication.

## Decisions

- Query a small, newest-first bounded set of sources and pages in the server route using the requester client; RLS remains the tenant boundary.
- Use existing URL helpers and routes for every action, avoiding a new navigation state.
- Prefer a focused empty state over fabricated activity metrics.

## Risks / Trade-offs

- [Recent queries add home latency] → Bound each list and select only presentation fields.
- [Activity can be empty while processing] → Present sources and processing state honestly.
