# NexusWiki Quiet Editorial Dashboard Design

**Status:** Approved for planning

## Goal

Refresh the NexusWiki dashboard's shared application shell and Sources page with a quiet, editorial visual language inspired by Meng To's product sensibility. Preserve all existing user flows, API contracts, security boundaries, and source-processing behavior.

## Scope

### Included

- Shared workspace shell: page canvas, header, workspace selector placement, navigation, responsive behavior, typography, buttons, inputs, focus states, and semantic colors.
- Sources page: page introduction, source-entry surface, source list rows, empty state, and job-progress presentation.
- Responsive and keyboard-accessible treatment for the changed components.
- Focused component tests updated only where markup or accessible labels change.

### Excluded

- Changes to Ask, Wiki, Graph, Settings, login, API routes, Supabase queries, RLS, ingestion jobs, SSE, source schemas, and user-facing product behavior.
- New source types, dashboard analytics, dark mode, or changes to persisted design-token documentation outside the dashboard.

## Visual System

The dashboard will use a warm white canvas, near-black ink, soft gray separators, and a single near-black primary action. Existing semantic success, warning, and error colors remain for status meaning. The current Airbnb-style pink accent, pill-heavy controls, prominent soft cards, and elevated shadows are removed from the scoped surfaces.

Inter remains the font. Page titles become the primary hierarchy tool: large, tight tracking, and medium weight. Supporting copy and metadata become quieter through size and neutral contrast, rather than lighter-weight text that risks accessibility.

## Shared Shell

The shell constrains primary content to a comfortable reading width while retaining fluid gutters at small widths. The header is a thin, white-to-warm-white band with a fine bottom rule. It contains the Nexus wordmark, workspace switcher, and compact route navigation. The active route has a short, high-contrast underline; inactive routes remain plain text links. No route gains an icon solely for decoration.

On narrow viewports, the header wraps or scrolls its route navigation without creating page-level horizontal overflow. The workspace switcher remains discoverable, and every interactive element retains a visible keyboard focus state.

## Sources Page

The page begins with a simple `Sources` title and one-line explanation. Source entry becomes a restrained bordered section with a compact mode switcher (file, URL, text) and one clear action. It must keep the current drag-and-drop target, validation, loading behavior, errors, prefilled text flow, and API calls unchanged.

The source library becomes a ruled list instead of separate rounded cards. Each row presents the source icon/type, title, date, and processing status in a stable visual order. Long titles truncate gracefully with an accessible full-value affordance. On compact screens, secondary metadata moves beneath the title and job steps retain enough width to remain readable.

The zero-source experience uses the existing approved Korean copy exactly, but frames it as a calm first-library invitation rather than a blank card.

## Component Boundaries

- `NavShell` owns the revised shared header and route state styling.
- Workspace layout owns canvas width and responsive page gutters.
- `SourcesList` owns page-level source framing and list-row layout only.
- `Dropzone` retains all ingestion state and submission logic; its markup/classes change only to express the new surface.
- `JobStepper` remains behaviorally unchanged and receives only scoped presentation adjustments if needed for row layout.

No data-fetching or state ownership moves between server and client components.

## Accessibility and Failure Behavior

All existing form labels, tab semantics, error announcements, disabled states, and focus visibility remain intact. Color is never the only signal for the active navigation state or ingestion/job state. Existing error messages and backend failure mapping are unchanged.

## Verification

- Run the dashboard's existing Vitest suite and TypeScript typecheck.
- Add or adjust focused tests for any changed navigation active state, list metadata layout, or accessible title behavior.
- Inspect desktop and 360px-wide layouts for no page-level horizontal overflow, usable navigation, readable job states, and visible focus indicators.
- Verify file, URL, and text ingestion still call the same endpoints and preserve their existing error handling.
