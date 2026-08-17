## Context

The dashboard has an existing neutral canvas and token set, but many pages own their own spacing and information hierarchy. See `proposal.md` for motivation.

## Goals / Non-Goals

**Goals:** establish a quiet editorial knowledge-work register, shared component vocabulary, semantic states, and responsive validation across workspace routes.

**Non-Goals:** change product workflows, API/data contracts, authentication, or replace the current visual identity with a new brand.

## Decisions

### Token-first consolidation

Extend and consume semantic tokens instead of introducing page-local colors, spacing, or shadows. This lets all destinations converge without a brand rewrite.

### Common primitives before route polish

Create page frame/header, section heading, status badge, control bar, document row, and empty-state primitives before updating individual routes. This avoids repeating temporary styles.

### Density follows task type

Library and operations screens remain compact; long-form Ask and Wiki reading surfaces constrain line length. Do not force a uniform card grid across unlike tasks.

### State-rich accessibility

Every control gets default, hover, focus-visible, disabled, and loading behavior. Semantic status always includes readable text; color is secondary.

## Risks / Trade-offs

- [Broad visual edits can regress route behavior] → migrate route-by-route with component and browser checks.
- [Token expansion can become a second design system] → name only semantic roles and remove page-local replacements as routes migrate.
- [Dense screens can become noisy] → preserve one primary action per page and use dividers/typography before cards.

## Migration Plan

1. Audit and capture all target states and viewport widths.
2. Land primitives and token aliases with visual regression coverage.
3. Migrate routes in Home/Sources, Ask/Wiki, then Graph/Settings waves.
4. Verify keyboard, contrast, responsive behavior, and real workflow states before release.
