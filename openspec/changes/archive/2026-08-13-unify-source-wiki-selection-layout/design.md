## Context

Sources currently presents processing rows in place while Wiki routes to a standalone detail reading view. The dashboard design system now supplies shared page and status primitives.

## Goals / Non-Goals

**Goals:** define one document-row visual contract and one detail-header/back-link contract for both libraries.

**Non-Goals:** alter source ingestion, wiki compilation, API routes, or add arbitrary client-side selection state.

## Decisions

### URL remains the selected state

Wiki keeps its detail route. Sources uses an accessible inline expansion below the selected row, so ingestion and job processing remain local to the existing library surface. The expanded state is presentation-only; it reveals no data beyond the already RLS-scoped source row and never replaces a URL route.

### Shared document primitives

Rows share title, metadata, state badge, hit target, and focus treatment. Detail headers share labelled return link, type label, title, and status context.

## Risks / Trade-offs

- [Sources have no detail route today] → first inspect the existing source data contract; avoid inventing a detail page without enough safe content.
