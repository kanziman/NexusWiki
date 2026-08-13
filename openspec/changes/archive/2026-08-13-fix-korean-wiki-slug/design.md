## Context

See `proposal.md` for the route failure motivating this change. Next.js route parameters can reach the Server Component as a percent-encoded slug or as Unicode, while stored wiki slugs use Unicode. The existing Supabase query already provides workspace and requester scoping through its workspace predicate and RLS-backed server client.

## Goals / Non-Goals

**Goals:**

- Canonicalize the route slug at the route boundary before the existing page lookup.
- Preserve the generic not-found response when canonicalization cannot complete safely.
- Cover successful and malformed values through route-level regression tests.

**Non-Goals:**

- Change stored slug format, RLS policies, or database queries beyond the slug value.
- Redirect URLs or alter client-side wiki-link generation.

## Decisions

- Use `decodeURIComponent` once at the route boundary. It preserves ASCII and already-decoded Unicode while converting percent-encoded Unicode before the database lookup. Double decoding would incorrectly reinterpret a literal percent sequence.
- Catch decode failures and return the existing generic not-found component before calling Supabase. This prevents malformed URL values from becoming server errors or disclosing data.
- Keep the existing workspace predicate and Supabase client unchanged, so normalization has no effect on tenant or requester access control.

## Risks / Trade-offs

- [A literal stored slug containing a valid percent escape sequence changes under decoding] → Stored slugs are generated from normalized titles; decode only once at the HTTP route boundary, matching the route contract.
- [Malformed input attempts to trigger an error path] → Test that no page query occurs and that the generic not-found response is returned.
