## Context

See [proposal.md](proposal.md) for motivation. The dashboard root route currently performs an RLS-scoped workspace query but redirects any non-empty result to the first workspace. The workspace layout independently validates the URL workspace ID and supplies the existing switcher with the same RLS-scoped workspace list.

## Goals / Non-Goals

**Goals:**

- Make the root and post-login entry decision consistent for zero, one, and many accessible workspaces.
- Reuse request-scoped Supabase access so the database remains the tenant-isolation authority.
- Make the chosen workspace explicit in the URL and preserve the existing layout backstop.

**Non-Goals:**

- Persisting a last-visited workspace preference.
- Changing membership, invitation, workspace creation, or workspace data APIs.
- Replacing the existing header workspace switcher.

## Decisions

### Resolve entry on the server from the requester's session

The root route and selection surface will query `workspaces` through the existing server Supabase client, which carries the requester's JWT. This gives the UI only RLS-visible records and avoids a privileged aggregation endpoint. The alternative, querying from a client component, would add loading and client-side authorization states without improving the security boundary.

### Use cardinality to select the route

The entry resolver will sort workspaces deterministically by the existing name ordering: zero keeps invitation guidance, one redirects to `/w/<id>`, and multiple renders the chooser. This preserves the current direct-entry behavior for single-workspace users while preventing an arbitrary first project from being selected for multi-workspace users. A last-visited preference is deferred because it requires new persistent state and a fallback policy.

### Keep URL-scoped authorization as a second boundary

The chooser only emits destinations for its RLS-visible list. The `/w/[workspaceId]` layout continues to query and validate the URL ID before rendering child content. This defense in depth means stale UI state or a manually edited URL cannot turn the chooser into an oracle for inaccessible workspaces.

### Reuse the switcher contract

The existing `WorkspaceSwitcher` receives the validated current ID and RLS-scoped list from the workspace layout. The new entry UI will use the same destination helper and list shape, avoiding a separate client-side workspace source of truth.

## Risks / Trade-offs

- [A server redirect occurs before a user sees a chooser for a single workspace] → This is intentional; the deterministic direct path minimizes an unnecessary step.
- [A workspace is removed between selection render and navigation] → The workspace layout's existing access check returns the generic protected-route outcome.
- [Name ordering can feel arbitrary for returning multi-workspace users] → Document it as the temporary deterministic policy; introduce an explicit preference in a later change if needed.
- [Client session state can lag immediately after login] → Continue the existing full navigation to the root route so server components read refreshed auth cookies.

## Migration Plan

1. Add the server-rendered multi-workspace selection surface and cardinality-aware root resolver.
2. Preserve the current workspace-layout authorization backstop and verify it with inaccessible URL coverage.
3. Deploy without schema or API migration; rollback by restoring the root's existing single-target redirect behavior.
