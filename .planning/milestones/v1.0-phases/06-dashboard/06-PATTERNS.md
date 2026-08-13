# Phase 6: Dashboard - Pattern Map

**Mapped:** 2026-08-12
**Files analyzed:** ~28 (new App Router routes/components/lib + 3 existing files to modify)
**Analogs found:** codebase-internal analogs for shared scaffolding (layout/css/component/lib); backend response-shape analogs for every data-fetching surface. No prior dashboard route/page/client exists yet — this is the first App Router feature work in the repo, so most "closest analog" is the *backend endpoint it calls*, not a sibling frontend file.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `apps/dashboard/middleware.ts` (new) | middleware | request-response (cookie/session gate) | none in dashboard (new pattern) — spec source: `@supabase/ssr` Next.js middleware recipe; auth boundary rationale: `apps/api/src/api/errors.py` 403/404-collapse convention (D-12) | no direct analog — external library recipe |
| `apps/dashboard/app/layout.tsx` (existing, modify) | provider/layout | request-response | itself (extend in place) | exact |
| `apps/dashboard/app/globals.css` (existing, modify) | config | n/a | itself + `docs/design-systems/design-tokens.css` | exact |
| `apps/dashboard/lib/workspace-path.ts` (existing, reuse) | utility | n/a | itself | exact |
| `apps/dashboard/lib/supabase-browser.ts` (new) | utility/provider | request-response | `apps/dashboard/lib/workspace-path.ts` (module shape: single exported pure function, no class) | role-match |
| `apps/dashboard/lib/supabase-server.ts` (new) | utility/provider | request-response | `apps/dashboard/lib/workspace-path.ts` | role-match |
| `apps/dashboard/lib/api-client.ts` (new — fetch wrapper for `apps/api`) | service | request-response | `apps/api/src/api/routers/sources.py` `_user_db()` adapter-factory pattern (JWT-per-request, never a shared credential) | role-match (cross-language, pattern-level) |
| `apps/dashboard/app/(auth)/login/page.tsx` (new) | route/page | request-response | none (first page) — form shape from UI-SPEC Copywriting Contract | no analog |
| `apps/dashboard/app/w/[workspaceId]/layout.tsx` (new) | layout/provider | request-response | `apps/dashboard/app/layout.tsx` | role-match |
| `apps/dashboard/components/WorkspaceSwitcher.tsx` (new) | component | request-response | `apps/dashboard/components/HealthBadge.tsx` (styling/export convention) | role-match |
| `apps/dashboard/app/w/[workspaceId]/settings/page.tsx` (invite form) (new) | route/page | CRUD | `apps/api/src/api/routers/workspaces.py` (PATCH/DELETE shape, `WorkspaceUpdateRequest` extra=forbid pattern informs client-side payload shaping) | role-match |
| `apps/dashboard/components/InviteForm.tsx` (new) | component | CRUD | `apps/api/src/api/routers/workspaces.py::WorkspaceUpdateRequest` (request/response contract) | role-match |
| `apps/dashboard/components/MembersList.tsx` (new) | component | CRUD | none direct — row-list shape, see Shared Patterns "List row" | no analog |
| `apps/dashboard/app/w/[workspaceId]/sources/page.tsx` (dropzone) (new) | route/page | file-I/O + event-driven (job polling) | `apps/api/src/api/routers/sources.py` (three ingest endpoints: text/file/url, 202 + `{job_id, raw_source_id}` response) | exact (backend contract) |
| `apps/dashboard/components/Dropzone.tsx` (new) | component | file-I/O | `apps/api/src/api/routers/sources.py` `ingest_file_source`/`ingest_text_source`/`ingest_url_source` (3-tab request shapes) | exact (backend contract) |
| `apps/dashboard/components/JobStepper.tsx` (new) | component | event-driven (polling) | `apps/api/src/api/routers/jobs.py` (job status/list endpoints) — see note below, file exists but not read line-by-line; classify by grep match `@router` decorators found | role-match |
| `apps/dashboard/app/w/[workspaceId]/ask/page.tsx` (new) | route/page | streaming | `apps/api/src/api/routers/ask.py` (`POST /workspaces/{id}/ask`, SSE `event: name\ndata: json\n\n` framing, event order `meta`→`delta*`→`citations`→`done`) | exact (backend contract) |
| `apps/dashboard/components/AskConversation.tsx` (new) | component | streaming | `apps/api/src/api/routers/ask.py` `_format_sse` framing + `AskRequest` schema | exact (backend contract) |
| `apps/dashboard/components/CitationMarker.tsx` (new) | component | transform (client-side citation-anchor resolution) | `apps/api/src/api/routers/ask.py` (anchor alias scheme from 05-CONTEXT D-01~D-11, consumed not re-derived) | role-match |
| `apps/dashboard/components/CitationSidePanel.tsx` (new) | component | request-response | none direct — depends on retrieval/wiki read endpoints (`apps/api/src/api/routers/retrieval.py`, `wiki.py`) | role-match |
| `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx` (new) | route/page | CRUD (read-only) | `apps/api/src/api/routers/wiki.py` (read endpoint shape — not read line-by-line this pass, grep confirms `@router` present) | role-match |
| `apps/dashboard/components/WikiPageContent.tsx` (new) | component | CRUD (read-only) | none direct — static-content render, no state | no analog |
| `apps/dashboard/components/RedLinkCta.tsx` (new) | component | request-response | UI-SPEC copy contract row "Red-link CTA" | no analog |
| `apps/dashboard/app/w/[workspaceId]/graph/page.tsx` (new) | route/page | request-response (batch fetch) | `apps/api/src/api/routers/graph.py` (depth≤2/fan-out-cap/cycle-guard RPC boundary, per 05-CONTEXT D-07.1/D-11 — not read line-by-line this pass, grep confirms `@router` present) | role-match |
| `apps/dashboard/components/GraphCanvas.tsx` (new) | component | batch | `apps/api/src/api/routers/graph.py` (1000-row PostgREST cap, category-filter narrowing) | role-match |
| `apps/dashboard/components/GraphLensFilter.tsx` (new) | component | request-response | none direct | no analog |

## Pattern Assignments

### `apps/dashboard/middleware.ts` (new)

**No in-repo analog** — first middleware file in the dashboard app. Governing constraints, not code to copy:

- CLAUDE.md constraint: Next.js **≥ 15.2.3** required — CVE-2025-29927 lets `x-middleware-subrequest` header forgery skip middleware, and per `06-CONTEXT.md` D-02 this middleware **is** the tenant gate.
- D-02 (locked decision): `middleware.ts` is the **only** cookie writer. Use `@supabase/ssr`'s `createServerClient` + `getAll`/`setAll` cookie adapter (official recipe), not a hand-rolled cookie parser.
- Error-shape precedent to mirror conceptually (not copy verbatim, different language) — `apps/api/src/api/errors.py:178-208` `_render_isolation_failure`: **do not distinguish "resource doesn't exist" from "not a member"** in the redirect/response — both cases should redirect to login/workspace-picker uniformly, never leak existence via a different status/redirect target. This directly extends 02-CONTEXT D-12 (no-enumeration) into the frontend gate.

### `apps/dashboard/lib/api-client.ts` (new)

**Analog:** `apps/api/src/api/routers/sources.py` lines 114-127 (`_user_db` factory)

**Auth pattern to mirror** (concept, not literal code — Python → TS):
```python
def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    settings: ApiSettings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )
```
Rule to carry over: **always attach the requester's own Supabase access token per call**, never a shared/service credential — the client-side `fetch` wrapper must read the session token from the `@supabase/ssr` browser/server client per request, matching the "user JWT only, service_role never on user paths" rule from CLAUDE.md `checklists.json > decisions.db_access`.

**Error-shape contract to consume** (`apps/api/src/api/errors.py` bodies, exact JSON keys the client must branch on):
- `403` → `{"detail": "forbidden"}` (fixed string, no resource info — `apps/api/src/api/errors.py:52`)
- `409` duplicate source → `{"detail": "already_ingested", "raw_source_id": ...}` (`apps/api/src/api/errors.py:225-228`)
- `402` budget → `{"detail": "budget_exceeded"}` (`apps/api/src/api/errors.py:240-243`) → maps to UI-SPEC copy "이번 달 워크스페이스 사용량 한도를 초과했습니다..."
- `413` → `{"detail": "text_too_large"|"payload_too_large", "limit": N}` (`apps/api/src/api/errors.py:250-253`, `276-279`)
- `422` → `{"detail": "invalid_source", "reason": "<token>"}` — reason is a **machine token** (`unsupported_mime`, `empty_body`, `bad_url_scheme`, `url_credentials`, `bad_url_host`, `url_too_long`) not prose — client owns the Korean copy mapping, per `apps/api/src/api/errors.py:113-127`
- `409` job — `{"detail": "not_retryable"|"not_cancellable"}` (`apps/api/src/api/errors.py:297-314`)
- Client must map **0 affected rows → already rendered as 403 by the API**, so the dashboard never needs its own row-count logic — it only branches on HTTP status + `detail` token.

### `apps/dashboard/app/w/[workspaceId]/ask/page.tsx` + `components/AskConversation.tsx`

**Analog:** `apps/api/src/api/routers/ask.py` (full file, 100 lines)

**Endpoint contract**:
```
POST /workspaces/{workspace_id}/ask
Body: { query: string (min 1), requested_k?: int (1-8, default 8), template_id?: string|null }
```

**SSE framing to parse** (`apps/api/src/api/routers/ask.py:76-78`):
```python
async def _format_sse(events: AsyncIterator[tuple[str, dict[str, Any]]]) -> AsyncIterator[str]:
    async for name, payload in events:
        yield f"event: {name}\ndata: {json.dumps(payload)}\n\n"
```
→ Client must parse raw `event: <name>\ndata: <json>\n\n` frames from a `fetch` + `ReadableStream` (per 05-CONTEXT D-02, `EventSource` is explicitly disallowed since it can't send the `Authorization` bearer header). Event order is fixed: `meta` → `delta*` (zero or more) → `citations` → `done`. D-09 (locked): citation markers render as gray placeholders until the `citations` event arrives, then swap in-place — never render a marker as a real link before that event.

**Max query length enforced server-side** — `apps/api/src/api/routers/ask.py:88-90`: `422 invalid_query` if `len(query) > settings.RETRIEVAL_MAX_QUERY_CHARS`. Client should soft-validate the same bound but must handle the 422 regardless.

### `apps/dashboard/components/Dropzone.tsx` + `app/w/[workspaceId]/sources/page.tsx`

**Analog:** `apps/api/src/api/routers/sources.py` (full file, 437 lines) — three endpoints matching D-06's three tabs exactly:

```
POST /workspaces/{id}/sources/text  { title, text, source_type?, collection_purpose? }  -> 202 { job_id, raw_source_id }
POST /workspaces/{id}/sources/url   { url, title?, collection_purpose? }                -> 202 { job_id, raw_source_id }
POST /workspaces/{id}/sources/file  ?filename=&title=  body=<raw bytes>                  -> 202 { job_id, raw_source_id }
```

**Critical implementation detail** (`apps/api/src/api/routers/sources.py:334-346`): the file endpoint takes **raw bytes as body, not multipart** — filename/title are query params. Client code: `fetch(url + '?filename=...&title=...', { method: 'POST', headers: {'Content-Type': file.type}, body: file })`. Do not build a `FormData`/multipart upload — the backend does not accept it.

**Dedup response to branch on** (D-07): `409` with `{"detail": "already_ingested", "raw_source_id": "..."}` → render the "이미 수집됨 — 건너뜀" banner (verbatim per UI-SPEC copy contract), not a generic error toast.

**Job-stage names for the stepper** (D-05, verbatim in UI-SPEC): "업로드 → 파싱 → 컴파일 → 링크 동기화 → 임베딩" — these must map 1:1 to whatever stage/status vocabulary `apps/api/src/api/routers/jobs.py` exposes on GET; confirm exact field names against that router at implementation time (not fully read this pass — recommend planner have the phase-6 plan re-grep `apps/api/src/api/routers/jobs.py` for the response schema before building `JobStepper.tsx`).

### `apps/dashboard/app/w/[workspaceId]/settings/page.tsx` + `components/InviteForm.tsx`, `MembersList.tsx`

**Analog:** `apps/api/src/api/routers/workspaces.py` (full file, 94 lines)

```python
class WorkspaceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
```
Pattern to mirror client-side: strict allow-listed payload shape, no passthrough of unknown fields — matches CLAUDE.md's "extra=forbid" convention. Note this specific router only has PATCH/DELETE on `workspaces` itself (name update, deletion) — it does **not** show the invite/member-role endpoint; the invite form's actual target endpoint lives elsewhere (likely a `members` sub-route not read in this pass — planner should grep `apps/api/src/api/routers/` for a members/invite router before finalizing `InviteForm.tsx`'s request shape). Role vocabulary is fixed by schema: `owner(3) > editor(2) > viewer(1)` (`supabase/migrations/0001_core_schema.sql`), UI-SPEC default = `viewer`.

### `apps/dashboard/components/HealthBadge.tsx` → styling/export convention analog for ALL new components

**Analog:** `apps/dashboard/components/HealthBadge.tsx` (full file, 16 lines) — this is the **only** existing dashboard component and is the canonical style/export reference for every new component in this phase:

```tsx
"use client";

type HealthBadgeProps = {
  status: "ok" | "degraded" | "unknown";
};

const labels: Record<HealthBadgeProps["status"], string> = {
  ok: "정상",
  degraded: "저하",
  unknown: "알 수 없음",
};

export function HealthBadge({ status }: HealthBadgeProps) {
  return <span data-status={status}>{labels[status]}</span>;
}
```

Conventions to copy: `"use client"` directive at top when the component has interactivity; named export (not default) for components; `Props` type named `<Component>Props`; Korean-language label maps keyed by a literal-union type, not inline ternaries; `data-status`/`data-*` attributes for state that tests assert on (see matching test below) rather than relying on CSS class presence.

**Matching test analog** — `apps/dashboard/tests/HealthBadge.test.tsx` (full file, 22 lines): Vitest + Testing Library, `describe`/`it` in Korean, asserts on `getByText` + `toHaveAttribute("data-status", ...)`. Every new interactive component should get a sibling test file under `apps/dashboard/tests/` following this exact structure.

### `apps/dashboard/app/layout.tsx` (extend)

**Analog:** itself, current 19-line file:
```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "NexusWiki",
  description: "출처까지 추적할 수 있는 살아 있는 위키",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```
Extend in place: add `next/font/google` Inter loading (per UI-SPEC Design System table — swap into `--font-family-base` slot), wrap `children` with auth/session provider. Keep `lang="ko"` and the existing `metadata` block as-is — do not rewrite, only add.

### `apps/dashboard/app/globals.css` (extend)

**Analog:** itself, current 8-line file — line 8 has the explicit marker comment `/* 디자인 토큰(...)의 @theme 편입은 Phase 6 UI 작업 범위 */` marking the exact integration point. Add Tailwind 4 `@theme` block mapping `docs/design-systems/design-tokens.css` custom properties into Tailwind's token namespace, plus the two new semantic colors specified in UI-SPEC (`--color-success-text: #0a7d34`, `--color-warning-text: #8a5300`) added directly to `design-tokens.css` per UI-SPEC's explicit instruction ("Executor should add these two ... during the `globals.css` `@theme` integration task").

### `apps/dashboard/lib/workspace-path.ts` (reuse as-is)

**Analog:** itself, full file:
```typescript
export function workspacePath(workspaceId: string): string {
  if (workspaceId.trim().length === 0) {
    throw new TypeError("workspaceId must not be empty");
  }

  return `/w/${workspaceId}`;
}
```
D-03 (workspace switching navigates via `workspacePath()`, URL owns tenancy) consumes this directly — `WorkspaceSwitcher.tsx`'s `onSelect` handler should call `router.push(workspacePath(id))`, not construct the path inline. No modification needed to this file itself.

---

## Shared Patterns

### JWT-per-request (never a shared/service credential)
**Source:** `apps/api/src/api/routers/sources.py:114-138` (`_user_db`, `_user_storage` adapter factories), reinforced by `apps/api/src/api/routers/workspaces.py:53-66`
**Apply to:** `apps/dashboard/lib/api-client.ts` and every route/component that calls `apps/api` — every fetch must attach the current user's Supabase access token (read via `@supabase/ssr`), matching `checklists.json > decisions.db_access` (service_role is worker/migration-only, BYPASSRLS makes user-path use of it a full isolation break).

### 403/no-enumeration error contract
**Source:** `apps/api/src/api/errors.py:178-208` (`_render_isolation_failure`), `:52` (`FORBIDDEN_BODY = {"detail": "forbidden"}`)
**Apply to:** `middleware.ts`, `api-client.ts`, and any route that redirects on auth failure — never distinguish "workspace doesn't exist" from "you're not a member" in UI copy, redirect target, or status code. This is a locked cross-phase invariant (02-CONTEXT D-12), and the frontend must not reintroduce enumeration by rendering a different error for the two cases.

### Component/test file shape
**Source:** `apps/dashboard/components/HealthBadge.tsx` + `apps/dashboard/tests/HealthBadge.test.tsx`
**Apply to:** all new components — `"use client"` when interactive, named exports, `<Name>Props` type, Korean label maps as `Record<T, string>` constants, `data-*` attributes for test-observable state, sibling Vitest+Testing-Library test in `apps/dashboard/tests/`.

### Design tokens — consume, do not reinvent
**Source:** `docs/design-systems/design-tokens.css` (168+ lines: color/radius/spacing/typography custom properties), constrained by `06-UI-SPEC.md`'s Spacing Scale / Typography sections (multiples-of-4 subset only, 2-weight cap: 400 body / 600 label-heading-display)
**Apply to:** every new component's className/style — use `var(--color-*)`, `var(--spacing-*)`, `var(--rounded-*)`, `var(--font-*)` (via the Tailwind `@theme` mapping added to `globals.css`), never raw hex/px values. UI-SPEC's per-role table (Body/Label/Heading/Display) is the binding contract, not the raw token file's full 4-weight/9-spacing set.

### SSE parsing (Ask UI only)
**Source:** `apps/api/src/api/routers/ask.py:76-78` (`_format_sse`)
**Apply to:** `AskConversation.tsx` — POST + `fetch` + manual `ReadableStream` reader parsing `event: name\ndata: json\n\n` frames; `EventSource` is explicitly disallowed (05-CONTEXT D-02) because it cannot carry the `Authorization` bearer header this project requires on every user-path request.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `apps/dashboard/middleware.ts` | middleware | request-response | First middleware file in this app; no in-repo precedent, follow `@supabase/ssr` official Next.js recipe + CVE-2025-29927 constraint |
| `apps/dashboard/app/(auth)/login/page.tsx` | route/page | request-response | First page beyond the placeholder `app/page.tsx`; build from UI-SPEC copy contract directly |
| `apps/dashboard/components/MembersList.tsx` | component | CRUD | No existing list-row component in the dashboard; UI-SPEC "populated" state table + Airbnb list-row token guidance (`--spacing-base` 16px row padding) is the only spec |
| `apps/dashboard/components/WikiPageContent.tsx` | component | CRUD (read) | Static-content render, no existing analog; source of truth is `wiki.py` response shape (not read line-by-line this pass — planner should re-grep before this component's plan task) |
| `apps/dashboard/components/RedLinkCta.tsx` | component | request-response | No analog; copy fully specified in UI-SPEC copy table |
| `apps/dashboard/components/GraphLensFilter.tsx` | component | request-response | No analog; behavior spec is category-filter reuse of `wiki_pages.category`, per 06-CONTEXT Claude's Discretion note |

## Follow-up for planner (not fully resolved this pass)

`apps/api/src/api/routers/jobs.py`, `wiki.py`, `graph.py`, and `retrieval.py` were confirmed to exist and expose `@router` decorators via grep, but were **not** read line-by-line in this pass (stayed within the 3-5 strong analog budget — `ask.py`, `sources.py`, `workspaces.py`, `errors.py` covered the highest-value contracts: streaming, file/CRUD ingest, workspace CRUD, error taxonomy). Before writing `JobStepper.tsx`, `WikiPageContent.tsx`, `CitationSidePanel.tsx`, and `GraphCanvas.tsx`/`GraphLensFilter.tsx` plan tasks, read those four routers directly for exact response field names (job status enum values, wiki page JSON shape, graph RPC response shape, retrieval channel names) — the phase planner or the implementing plan's own research step should do this targeted read rather than re-deriving from this pattern map.

## Metadata

**Analog search scope:** `apps/dashboard/` (full tree, 6 real files besides `.next`/config), `apps/api/src/api/routers/` (8 files, 4 read in full), `apps/api/src/api/errors.py` (read in full), `docs/design-systems/design-tokens.css` (first 100 lines read)
**Files scanned:** ~20
**Pattern extraction date:** 2026-08-12
</content>
