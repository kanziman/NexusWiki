---
phase: 01-bootstrap-and-ground-truth
reviewed: 2026-08-05T06:57:43Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - .dockerignore
  - .env.sample
  - Dockerfile
  - apps/api/src/api/health_check.py
  - apps/api/src/api/main.py
  - apps/dashboard/app/page.tsx
  - apps/dashboard/components/HealthBadge.tsx
  - apps/dashboard/lib/workspace-path.ts
  - apps/dashboard/package.json
  - apps/dashboard/pnpm-lock.yaml
  - apps/dashboard/vitest.config.ts
  - apps/worker/src/worker/__main__.py
  - apps/worker/src/worker/rtt.py
  - apps/worker/tests/test_rtt.py
  - checklists.json
  - docs/ops/railway-deploy-record.md
  - docs/ops/rtt-baseline.md
  - packages/core/src/nexuswiki_core/logging.py
  - pyproject.toml
  - railway.json
  - scripts/smoke_dashboard.sh
  - scripts/smoke_tracer.sh
  - scripts/verify_storage_policies.sh
  - supabase/migrations/0005_storage.sql
  - supabase/tests/0005_storage_policies.sql
  - uv.lock
findings:
  critical: 1
  warning: 5
  info: 0
  total: 6
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-08-05T06:57:43Z
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

The phase establishes a coherent bootstrap, but the shared logging redactor can still emit secrets placed inside ordinary list payloads. Five additional robustness gaps leave worker tests outside the default suite, make the dashboard lint command unusable, permit malformed workspace routes, make container builds depend on a mutable tool image, and allow the smoke script to interfere with an unrelated container that happens to use its fixed name.

Validation performed during review: the default Python suite passed 7 tests, the separately targeted worker RTT suite passed 5 tests, dashboard Vitest passed 2 tests, dashboard type checking passed, and `scripts/smoke_tracer.sh` passed. `pnpm --dir apps/dashboard lint` failed before linting because no ESLint 9 flat configuration exists.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Sensitive values inside sequences bypass log redaction

**File:** `packages/core/src/nexuswiki_core/logging.py:37-43`

**Issue:** `_redact_mapping` only recurses when a value is another `MutableMapping`. Lists and tuples are left untouched, so a normal structured event such as `{"payloads": [{"authorization": "Bearer real-secret"}]}` is returned with the credential intact and is rendered to the log. This violates the module's stated guarantee that sensitive keys are masked before rendering and can disclose credentials or user content in production logs.

**Fix:** Walk both mappings and sequence containers with a recursive value redactor. For example, redact matching mapping keys, recursively transform every mapping value, and recursively transform each element of lists/tuples. Add regression tests for a list of mappings and for mappings nested inside multiple sequence levels.

## Warnings

### WR-01: Default pytest execution silently omits the worker test suite

**File:** `pyproject.toml:20-22`

**Issue:** `testpaths` includes only `packages/core/tests` and `apps/api/tests`, while the reviewed RTT tests live under `apps/worker/tests`. Consequently `uv run pytest` reports 7 passing tests without collecting any of the 5 RTT tests; they only run when addressed explicitly. A regression in the production worker probe can therefore pass the project's default test gate.

**Fix:** Add `apps/worker/tests` to `testpaths`, then assert the expected collection in CI or run each workspace's test directory explicitly.

### WR-02: The declared dashboard lint command cannot run

**File:** `apps/dashboard/package.json:10`

**Issue:** The project pins ESLint 9 and exposes `eslint .`, but there is no `eslint.config.js`, `.mjs`, or `.cjs`. Running the declared script exits with ESLint's “couldn't find an eslint.config” error before inspecting source, so lint is not an effective quality gate.

**Fix:** Add an ESLint 9 flat configuration compatible with `eslint-config-next` (or deliberately pin/configure an older supported ESLint setup), and verify `pnpm --dir apps/dashboard lint` succeeds.

### WR-03: Workspace IDs are interpolated into URLs without validation or encoding

**File:** `apps/dashboard/lib/workspace-path.ts:1-6`

**Issue:** The helper rejects only whitespace-only values and directly interpolates all other input. Values containing `/`, `?`, `#`, or traversal segments produce a different route than a single workspace segment (for example, `workspacePath("abc?tab=secret")` yields `/w/abc?tab=secret`). Any caller that passes an external or malformed identifier can navigate to the wrong workspace route or inject query/fragment components.

**Fix:** Validate the identifier against the actual workspace-ID format (preferably UUID) and/or interpolate `encodeURIComponent(workspaceId)`. Extend tests with slash, query, fragment, and traversal-like inputs.

### WR-04: The Docker build executes an unpinned mutable `uv` image

**File:** `Dockerfile:6`

**Issue:** `COPY --from=ghcr.io/astral-sh/uv:latest` resolves to whatever artifact owns the tag at build time. Identical source commits can therefore build with different installer behavior, and compromise or accidental replacement of that mutable tag is immediately incorporated into the builder. This also undermines the deployment record's attempt to establish same-source reproducibility.

**Fix:** Pin the `uv` image to a reviewed version and immutable digest, then update it through an explicit dependency-upgrade process.

### WR-05: Fixed smoke-test container names can stop an unrelated container

**File:** `scripts/smoke_tracer.sh:15-18`

**Issue:** Image mode always names containers `nexuswiki-smoke-api` and `nexuswiki-smoke-worker`, and the unconditional cleanup stops both names. If either name already belongs to another process, `docker run` fails but the EXIT trap still stops that pre-existing container. Concurrent smoke runs also collide with one another.

**Fix:** Generate unique container names from the process ID or a temporary suffix, record which `docker run` calls actually started successfully, and stop only those recorded containers during cleanup.

---

_Reviewed: 2026-08-05T06:57:43Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
