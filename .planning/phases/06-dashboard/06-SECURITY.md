---
phase: 06
slug: dashboard
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-13
---

# Phase 6 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser → middleware.ts | Unauthenticated request first touches the tenant gate; must not be bypassable (CVE-2025-29927) | Request cookies, session state |
| Browser → Supabase Auth | Email+password crosses to GoTrue over TLS | Credentials |
| Server Component → PostgREST | RSC reads use the requester's own session JWT; RLS is the only isolation enforcement | Workspace/wiki/source rows |
| Browser → invite_workspace_member RPC | Owner session crosses into a SECURITY DEFINER function reading `auth.users` (never directly queryable by the caller's own JWT) | Email → user_id resolution |
| Browser → workspace_members DELETE | Direct table write, RLS-enforced, no definer function | Membership rows |
| Browser → apps/api | Every apiFetch/raw-fetch call carries the caller's own bearer token | JWT, ingest/ask/verify payloads |
| Browser → PostgREST (wiki_pages/source_chunks by id) | Direct RLS-scoped reads keyed by server-issued citation anchor ids only | Cited chunk/page content |
| Browser → PostgREST (wiki_pages/wiki_links, category-filtered) | Direct RLS-scoped reads, client-side (graph canvas) | Graph nodes/edges |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01 | Spoofing | middleware.ts | high | mitigate | `x-middleware-subrequest` bypass closed by Next.js >=15.2.3 (pinned 15.5.22); middleware.ts is the sole cookie writer (D-02) | closed |
| T-06-02 | Information Disclosure | app/w/[workspaceId]/layout.tsx | medium | mitigate | RLS 0-row result redirects to `/` uniformly, no not-found-vs-forbidden distinction (D-12) | closed |
| T-06-03 | Tampering | Session storage | high | mitigate | Session lives only in the httpOnly cookie `@supabase/ssr` writes; no localStorage/sessionStorage auth-state reads/writes anywhere in apps/dashboard | closed |
| T-06-04 | Spoofing | npm installs (Task 0) | high | mitigate | Package legitimacy checkpoint (blocking-human) before any `pnpm add`, approved 2026-08-12 | closed |
| T-06-05 | Information Disclosure | Login error copy | low | accept | Single fixed error string doesn't distinguish account-not-found vs wrong-password — standard login-form practice | closed |
| T-06-06 | Tampering | WorkspaceSwitcher onSelect | low | accept | Switcher only lists ids RLS already proved the user can see; arbitrary pasted ids still redirect at the layout's RLS-scoped read | closed |
| T-06-07 | Information Disclosure | NavShell route links | low | accept | Links relative to the current already-authorized workspace id; no cross-tenant id embedded | closed |
| T-06-08 | Elevation of Privilege | invite_workspace_member | high | mitigate | `has_workspace_role(p_workspace_id,'owner')` is the first statement, raises 42501 before any auth.users read | closed |
| T-06-09 | Elevation of Privilege | invite_workspace_member p_role | high | mitigate | Server-side role allow-list check (22023) independent of client Select | closed |
| T-06-10 | Information Disclosure | invite_workspace_member NW404 | medium | accept | Owner-only email-registration enumeration; judged and accepted, standard invite-by-email practice | closed |
| T-06-11 | Information Disclosure | workspace_members_list | medium | mitigate | `is_workspace_member(p_workspace_id)` gates the function; non-member gets 0 rows | closed |
| T-06-12 | Tampering | workspace_members DELETE | high | mitigate | Enforced by pre-existing `workspace_members_delete_owner` RLS policy (0004) — **live-verified this session** via a real RLS-blocked-delete UAT test (06-UAT.md test 5) | closed |
| T-06-13 | Information Disclosure | apiFetch error parsing | low | mitigate | Malformed/non-JSON error bodies fall back to generic `unknown_error` detail, never rethrow raw body | closed |
| T-06-14 | Spoofing | apiFetch auth | high | mitigate | Token read fresh per call from current session, never module-level cached | closed |
| T-06-15 | Information Disclosure | sources list direct read | low | mitigate | `.select()` excludes `content` column from the list view | closed |
| T-06-16 | Denial of Service | JobStepper polling | low | accept | ~3s polling bounded by on-screen source count (max 50, page-limited) | closed |
| T-06-17 | Tampering | File-tab raw-bytes upload | medium | mitigate | MIME allow-list + size cap enforced server-side (apps/api sources.py), unchanged from Phase 3 | closed |
| T-06-18 | Tampering | CitationMarker streaming render | high | mitigate | Unresolved anchors render identically as inert placeholders pre-resolution; never clickable before the citations SSE frame | closed |
| T-06-19 | Spoofing | CitationSidePanel content-identity | high | mitigate | Fetches strictly by server-issued exact id, never fuzzy/derived match | closed |
| T-06-20 | Information Disclosure | prompt_templates direct read | low | mitigate | Scoped by pre-existing `prompt_templates_select_global_or_member` RLS policy | closed |
| T-06-21 | Elevation of Privilege | verify action visibility | medium | mitigate | `canVerify` computed server-side from actual role; PATCH write path independently RLS-backed regardless of client prop | closed |
| T-06-22 | Tampering | WikiPageContent | high | mitigate | No inline-edit surface exists at all — removes the bug class rather than gating it | closed |
| T-06-23 | Spoofing | RedLinkCta navigation target | low | accept | URL-encoded LLM-derived title only pre-fills a form field a human reviews before submitting | closed |
| T-06-24 | Information Disclosure | node/edge fetch (graph canvas) | medium | mitigate | Both queries scoped by `.eq("workspace_id", workspaceId)` AND RLS; forged workspaceId cannot surface another tenant's graph | closed |
| T-06-25 | Denial of Service | 1000-node Cytoscape render | low | accept | Bounded by PostgREST's own `max_rows=1000`; cap notice steers users to narrow via category rather than silently degrading | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-05 | Single fixed login-error string, standard practice | planner (06-01-PLAN.md) | 2026-08-12 |
| AR-06-02 | T-06-06 | Switcher navigation already gated by RLS-scoped layout read | planner (06-02-PLAN.md) | 2026-08-12 |
| AR-06-03 | T-06-07 | Nav links never embed cross-tenant ids | planner (06-02-PLAN.md) | 2026-08-12 |
| AR-06-04 | T-06-10 | Owner-only email-registration enumeration, industry-standard invite UX | planner (06-03-PLAN.md) | 2026-08-12 |
| AR-06-05 | T-06-16 | Polling fan-out bounded by page size (max 50) | planner (06-05-PLAN.md) | 2026-08-12 |
| AR-06-06 | T-06-23 | Prefill is a reviewed form default, never executed/trusted | planner (06-07-PLAN.md) | 2026-08-12 |
| AR-06-07 | T-06-25 | Bounded by PostgREST max_rows=1000; explicit cap notice, not silent degradation | planner (06-08-PLAN.md) | 2026-08-12 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-13 | 25 | 25 | 0 | gsd-security-auditor (ASVS L1, verify-mitigations mode) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-13
