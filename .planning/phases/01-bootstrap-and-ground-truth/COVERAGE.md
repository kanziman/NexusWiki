# Phase 1: Bootstrap and Ground Truth — API Coverage

**Detector:** `gsd-core/bin/lib/api-coverage.cjs` over the ROADMAP Phase 1 scope
**Result:** `{ "detected": false, "signals": [] }`
**Date:** 2026-08-02

## Declaration

No external API integration: this phase provisions and deploys against **platform infrastructure**
(Supabase Cloud project + Railway services), it does not wrap a third-party product API whose verb
surface a user would expect to be complete.

Concretely, what the phase touches instead:

- **Supabase CLI / control plane** — `supabase link`, `supabase db push`, dashboard Auth settings.
  These are provisioning operations against our own project, not a capability surface we expose to users.
- **Supabase PostgREST** — exactly one read shape (`GET /rest/v1/workspaces?select=id&limit=1`), used
  twice: as the `/health/ready` DB-roundtrip probe (계획 01-01) and as the RTT probe (계획 01-08).
  The transport decision itself is explicitly deferred to Phase 2 (DOM-01 spike) — 01-CONTEXT.md D-11
  keeps this behind a thin adapter precisely so Phase 1 does not pre-empt it.
- **Supabase Auth REST** — three calls used only as **verification probes** for BOOT-10
  (`/auth/v1/signup` ×2, `/auth/v1/token`, plus admin delete for cleanup). No auth surface is built
  in this phase; JWT verification and workspace context are Phase 2 (SEC-01~06).
- **Railway API/CLI** — service creation, region selection, per-service environment variable scoping.
  Infrastructure configuration, not a product integration.

The one place a coverage matrix would genuinely apply in this project — the OpenRouter and OpenAI
embedding APIs — is out of scope here: Phase 1 makes zero LLM or embedding calls
(01-SPEC.md §Boundaries). That matrix belongs to Phase 3 (COMP-01) and Phase 4.

---
*Reasoned no-integration declaration per the `api-coverage` gate. Detector returned `detected: false`;
this file records the judgment rather than fabricating matrix rows.*
