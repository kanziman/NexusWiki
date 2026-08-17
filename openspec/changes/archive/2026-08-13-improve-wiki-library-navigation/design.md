## Context

The current wiki index is a server-rendered title-only list. `WikiPageContent` renders verification context and raw content with resolved inline links, but has no document-level header, heading navigation, or related-document surface. See `proposal.md` and `specs/wiki-library-navigation/spec.md` for the intended behavior.

## Goals / Non-Goals

**Goals:**

- Keep the existing requester-JWT and RLS-scoped queries while making the loaded wiki collection navigable in the browser.
- Reuse existing wiki page fields and resolved link data; do not add API endpoints or persistence solely for presentation.
- Make the reading view more scannable without changing the wiki compilation or verification contracts.

**Non-Goals:**

- Full-text search beyond the pages loaded for the active workspace.
- Editing wiki content, changing verification permissions, or changing the existing wiki slug route behavior.
- Adding source-citation provenance not currently exposed by the wiki route.

## Decisions

### Server-scoped data with client-side library controls

The index route will continue to load workspace-scoped pages on the server and hand the minimal page data needed for search, category filtering, status display, and previews to a client library component. This retains RLS as the data boundary and provides instant filtering without a new API or query protocol.

Alternative considered: URL-driven server-side search and filtering. It would support very large libraries, but adds navigation state and a query contract before the product has demonstrated that the loaded collection is too large for local filtering.

### Presentation fields come from existing page data

The page query will include category, verification status, dispute state, and content so the library can derive labels and a bounded plain-text preview. The content preview is presentation-only and never treated as an authoritative full-text index.

Alternative considered: a new summary column or endpoint. That would impose database and API work for a view that can be derived safely from already visible page content.

### Heuristic in-page headings and resolved related links

The detail component will derive a table of contents only from recognizable line-based Markdown headings in the compiled text, assigning stable in-page anchors at render time. It will also use the already available resolved outgoing link records to render a deduplicated related-documents region. Both regions are optional so unstructured pages retain a clean reading surface.

Alternative considered: changing the compiler to persist section metadata or extending the route with linked-page titles. Those are valuable future upgrades, but exceed the UI-only scope and would require worker/API contract changes.

### Responsive document reading layout

The reading body will stay constrained to a readable line length. Heading navigation becomes a supporting column on wider viewports and an inline disclosure or compact navigation block on narrow viewports. Existing semantic colors and typography tokens remain the visual system.

## Risks / Trade-offs

- [Loaded-client filtering does not scale indefinitely] → Keep filtering confined to already RLS-visible data and revisit server-side search when workspace page counts demand it.
- [Compiled content may not use Markdown headings consistently] → Render heading navigation only when recognized; never invent sections.
- [Resolved link records contain slugs but not titles] → Use readable slug-derived fallback labels initially and avoid extra per-link queries; improve when the route can supply page titles in one scoped query.
- [Long titles and Korean text can wrap unexpectedly] → Test title wrapping and controls at narrow widths with realistic multilingual content.

## Migration Plan

1. Deploy as a dashboard-only change with no data migration.
2. Verify empty, populated, filtered, no-results, heading-present, and heading-absent states in automated tests and a browser session.
3. Roll back by reverting the dashboard components; stored wiki data and routes remain compatible.
