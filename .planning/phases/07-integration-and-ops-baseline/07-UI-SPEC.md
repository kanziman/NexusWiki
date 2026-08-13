---
phase: 7
slug: integration-and-ops-baseline
status: draft
shadcn_initialized: false
preset: none
created: 2026-08-13
---

# Phase 7 — UI Design Contract

> Visual and interaction contract for the OPS-06 Settings-page panel. OPS-02 through OPS-05 are test and benchmark deliverables and introduce no user-facing surface.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none — preserve the Phase 6 decision; no shadcn initialization or registry is needed for this additive panel |
| Preset | not applicable |
| Component library | Existing React/Tailwind 4 components; use native accessible buttons and semantic tabs, matching `SettingsMembersPanel` rather than introducing a new dependency |
| Icon library | `lucide-react`, already used by the dashboard |
| Font | `next/font/google` Inter through `--font-family-base` |
| Shell | Existing `/w/[workspaceId]/settings` page and `SettingsMembersPanel`-style 640px content column |
| Data behavior | Fetch once on panel entry/page load; refresh only after an explicit user click. Never add a polling timer or background refetch loop. |
| Authorization | Render the operational panel only for `owner` and `editor`. Viewers must neither receive the panel nor its operational aggregate request. Server/API authorization remains authoritative. |

This phase inherits the approved Phase 6 token integration and its documented 2-weight / 4px-grid usage subset. Do not modify `docs/design-systems/design-tokens.css` merely to implement this panel.

---

## Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon-to-label gaps; compact status-dot spacing |
| sm | 8px | Metric-label/value spacing; inline status rows |
| base | 16px | Card padding, form/control gaps, table-cell vertical rhythm |
| lg | 24px | Panel sections and tab-panel padding |
| xl | 32px | Separation between Members and Operations sections |
| xxl | 48px | Major settings-page section break |
| section | 64px | Page-level outer spacing where the existing shell uses it |

Exceptions: refresh control has a minimum 44×44px hit target; compact non-interactive status badges may use 4px horizontal/vertical internal padding. No 2px or 12px spacing tokens may be introduced or consumed.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.5 |
| Label | 14px | 600 | 1.29 |
| Heading | 16px | 600 | 1.25 |
| Display | 28px | 600 | 1.43 |

Use exactly these two weights: 400 and 600. Panel title and card headings use Heading; metric amounts use Heading, not a new display size; table labels, timestamps, and stage names use Label; explanatory and error text use Body.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--color-canvas` `#ffffff` | Settings background and metric-card surfaces |
| Secondary (30%) | `--color-surface-soft` `#f7f7f7` + `--color-hairline` `#dddddd` | Tab strip, pipeline summary cards, dividers, skeleton blocks |
| Accent (10%) | `--color-primary` `#ff385c` | Active Operations tab, explicit “운영 현황 새로고침” control, budget-progress fill only when not warning/dead |
| Destructive | `--color-primary-error-text` `#c13515` | Dead-job count and failed-load state only; never the default refresh action |
| Success text | `--color-success-text` `#0a7d34` | Completed/healthy pipeline state, when count is zero dead jobs |
| Warning text | `--color-warning-text` `#8a5300` | Budget nearing/exceeding cap and truncated aggregate warning |

Accent is reserved for the active tab, the manual refresh affordance, and the ordinary budget-progress indicator. Pipeline state is communicated with text, icon, and count together; color alone must not carry its meaning.

---

## Panel Layout and Interaction Contract

1. Keep the existing Settings page as the route. Add an in-page, keyboard-operable two-tab control: `멤버` and `운영 현황`. `멤버` remains the default for all roles. For an owner/editor, `운영 현황` is available; a viewer sees only `멤버` and no empty/forbidden Operations placeholder.
2. `운영 현황` has one primary visual anchor: a top summary row headed `이번 달 사용량`, showing `spent / monthly budget` in local currency formatting plus a labeled progress bar. Show remaining amount as secondary text. When `cap_micros` is zero, show `예산이 설정되지 않았습니다` and no misleading percentage bar.
3. Place a secondary `파이프라인 상태` section below it. Render the five known stages in server order—원문 파싱, 위키 컴파일, 링크 동기화, 임베딩, 지식 충돌 검사—as a compact table/list with columns `단계`, `대기`, `실행 중`, `실패`. Counts are workspace-wide snapshots, not a per-source stepper.
4. Put the icon-plus-text refresh control at the panel heading’s right edge. It must announce loading through `aria-busy`, disable while its request is in flight, and preserve the last successful snapshot while a refresh fails. On success, update the visible `마지막 갱신: {local date/time}` label.
5. Use server-provided stage labels where available. Do not duplicate job-status logic in the dashboard, expose job payloads/errors, or add retry/cancel controls to this summary surface.
6. Responsive behavior: at narrow widths, stack cost metrics vertically and allow the stage list to scroll horizontally inside its own bordered container; do not clip stage labels or counts. The 640px Settings column remains the wide-layout maximum.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Operations tab | `운영 현황` |
| Panel heading | `운영 현황` |
| Primary CTA | `운영 현황 새로고침` |
| Cost section heading | `이번 달 사용량` |
| Pipeline section heading | `파이프라인 상태` |
| Snapshot timestamp | `마지막 갱신: {local date/time}` |
| Empty pipeline | `처리 중이거나 대기 중인 작업이 없습니다.` |
| Empty cost/budget | `이번 달 사용 기록이 없습니다.` / `예산이 설정되지 않았습니다.` |
| Partial aggregate warning | `표시할 수 있는 사용 기록이 많아 합계가 일부만 반영되었을 수 있습니다. 정확한 한도 판단은 작업 등록 시 적용됩니다.` |
| Load/refresh error | `운영 현황을 불러오지 못했습니다. 운영 현황 새로고침을 시도해주세요.` |
| Dead-job status | `실패한 작업 {count}건` |
| Budget warning | `이번 달 예산에 가깝습니다.` |
| Budget exceeded | `이번 달 예산을 초과했습니다. 새 작업 등록이 제한될 수 있습니다.` |
| Destructive confirmation | 없음 — 이 패널은 읽기/새로고침 전용이며 취소·재시도·삭제를 제공하지 않는다 |

All visible copy is Korean. Do not show raw API error tokens, `last_error`, UUIDs, provider/model names, or a false claim that the displayed aggregate is the authoritative enqueue cap.

---

## UI Considerations

Applicable state considerations resolved: 13 covered, 2 backstop, 0 unresolved.

| Category | Element(s) | Status | Resolution / Reason |
|----------|------------|--------|---------------------|
| loading | Operations panel / refresh control | ✅ covered | Initial load uses neutral skeleton metric cards and stage rows; refresh retains the last snapshot, disables the control, and exposes `aria-busy` rather than replacing useful data with a spinner. |
| error | Operations panel / refresh control | ✅ covered | Use the documented load/refresh error copy with the explicit `새로고침` recovery action; retain prior successful data on a refresh failure. |
| empty | cost summary | ✅ covered | Zero usage renders the documented zero-usage copy and `$0`-equivalent formatted amount; an unset cap renders its separate documented copy without a percentage. |
| empty | pipeline stage list | ✅ covered | All stage counts at zero render the documented empty-pipeline note below the zero-count stage list. |
| populated | cost summary / pipeline stage list | ✅ covered | Show a dated monthly cost snapshot and five compact per-stage rows with queued/running/dead counts. |
| partial | aggregate usage | ✅ covered | `truncated: true` renders the documented partial-aggregate warning and preserves the snapshot; it never presents the number as authoritative. |
| partial | pipeline stage data | ✅ covered | A missing/unknown stage renders `집계 불가` in that row, while other known stage rows remain visible; it is not silently treated as zero. |
| overflow | pipeline stage list | ✅ covered | The five-row normal list fits the column; narrow viewports use an internal horizontal scroll container rather than clipping labels/counts. |
| overflow | tab labels / headings | 🧪 backstop | Verify long localized workspace/settings labels wrap or truncate with an accessible full-name tooltip; the two fixed tab labels themselves fit. |
| long-text | timestamp / warning / API-derived stage label | ✅ covered | Timestamp and warnings wrap naturally; stage label is server-owned but limited to one line with `title` tooltip and ellipsis if unexpectedly long. |
| zero-one-many | dead-job counts | ✅ covered | Use Korean count form `{count}건`; zero is expressed as `0건` in the row and the panel-level empty note handles all-zero state. |
| nav | Settings tabs | ✅ covered | Tabs have selected state, keyboard arrow navigation, visible focus ring, and role-based availability; URL/nav structure is not changed. |
| interactive-control | manual refresh | ✅ covered | 44px target, text label plus icon, disabled/in-flight semantics, and explicit success timestamp. |
| static-content | cost amounts | 🧪 backstop | Add a component test for unusually large formatted values and locale/date formatting to prevent overlap with the refresh control. |
| error | forbidden viewer access | ✅ covered | Viewer never requests or renders Operations data. Direct API access must be rejected by server authorization; dashboard need not reveal whether data exists. |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party | none | not applicable |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** approved — UI checker verified all six dimensions; the refresh control uses the explicit `운영 현황 새로고침` label.
