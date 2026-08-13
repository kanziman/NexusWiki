## 1. Wiki library

- [x] 1.1 Extend the workspace-scoped wiki index query and add a client library component that renders count, bounded previews, verification/dispute labels, and direct detail links.
- [x] 1.2 Add accessible text search, category filtering, and a distinct no-results state while preserving the existing no-pages empty state.

## 2. Wiki detail navigation

- [x] 2.1 Extend the detail route data with the page category and resolved outgoing link information required for document context and related-document navigation.
- [x] 2.2 Refine `WikiPageContent` with a breadcrumbed document header, readable body layout, optional heading navigation, and optional related-documents region while retaining verification behavior.

## 3. Verification

- [x] 3.1 Add or update route and component tests for library filtering, states, detail context, heading navigation, and related documents.
- [x] 3.2 Run dashboard tests, typecheck, lint, strict change validation, and a browser check of populated and responsive wiki views.
