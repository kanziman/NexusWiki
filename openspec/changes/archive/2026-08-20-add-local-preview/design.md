## Context

See [proposal.md](proposal.md) for the motivation. The dashboard's protected
workspace routes load server-side data through the requester's Supabase session,
and several client components independently call Supabase or the API. A preview
route must therefore have an explicit data and action boundary rather than
pretending to be a real authenticated workspace.

## Goals / Non-Goals

**Goals:**

- Keep the production workspace route, middleware, RLS use, and API clients
  unchanged.
- Reuse visual components where their inputs can be supplied as props.
- Make representative review flows deterministic and network-free.

**Non-Goals:**

- Simulating a real Supabase session, persistence, upload pipeline, or SSE
  server.
- Publishing a demo, staging route, or public preview URL.
- Exhaustively reproducing every loading and failure state.

## Decisions

### Development layout guard owns availability

`app/preview/layout.tsx` will call `notFound()` unless `NODE_ENV` is
`development`; child routes inherit that boundary. This is chosen over a
middleware-only guard because it protects the complete route tree even if the
matcher changes, and over build-time route removal because local route tests
remain simple. Preview paths are deliberately outside the existing auth
matcher, while protected `/w/*` behavior remains untouched.

### Fixtures and explicit adapters replace global mock mode

A typed fixture module will own the complete mock workspace model. Preview
routes will compose reusable screen components from fixture props, with focused
preview adapters for components that currently perform live reads or writes.
This is chosen over environment branches inside Supabase/API clients: those
branches could accidentally affect production behavior or conceal a live call.
It is also preferred to browser request interception, which would make the
review experience depend on untyped endpoint emulation.

### Preview actions are local and visibly non-persistent

Interactive visual state lives in client component state. Any control whose
production meaning is an external mutation is replaced or intercepted by a
single preview notice pattern. Mock Ask completes with a deterministic answer
and resolved citation targets instead of opening SSE. This avoids credentials,
network side effects, and timing-dependent screenshots while preserving the
reviewer's main information flow.

## Risks / Trade-offs

- [Shared components remain coupled to live services] → extract only the
  presentational seams required by preview and cover them with route tests.
- [Preview diverges visually from production] → reuse existing shell and
  display components, and keep fixtures in one typed module.
- [A future deployment exposes mock data] → enforce the server layout guard and
  test the production not-found outcome.
- [Reviewers mistake preview actions for persistence] → label or toast every
  mutation affordance consistently in Korean.

## Migration Plan

No data or API migration is required. The change adds local-only code. Rollback
is a normal code revert; no existing route, database object, or session behavior
needs cleanup.
