---
status: testing
phase: 06-dashboard
source: [06-VERIFICATION.md]
started: 2026-08-13T00:20:00+09:00
updated: 2026-08-13T00:45:00+09:00
---

## Current Test

number: 1
name: Full ingest flow — dropzone to job-chain completion
expected: |
  Drop a file/URL/text source with apps/api + worker + supabase running. Real stage names
  shown throughout (업로드 → 파싱 → 컴파일 → 링크 동기화 → 임베딩), never an indeterminate
  spinner. A dead job shows a retry button. Polling stops once the chain reaches a terminal
  state, and resumes on retry/cancel (WR-04 fix).
awaiting: user response — needs apps/api + worker running with real OPENROUTER_API_KEY
  (blocked at .env directory permission level for this session — user must run these two
  services themselves, or grant .env access)

## Tests

### 1. Full ingest flow — dropzone to job-chain completion
expected: 실제 단계 이름으로 진행 표시, dead job 재시도 버튼, 종료 상태에서 폴링 정지·재시도 시 재개
result: [pending]
reason: "apps/api + worker require OPENROUTER_API_KEY from .env, which this session's permission settings deny reading (Bash and Read tool both denied at the directory level). Needs the user to run the services or grant access."

### 2. Full ask flow — dual-citation markers
expected: |
  Ask a real question against seeded evidence. Placeholder markers are inert during
  streaming; after the citations SSE frame they become clickable numbered badges. Clicking
  a wiki-kind marker and a source-kind marker within the same dual-cited sentence each opens
  exactly its own cited content (single-card-per-click is the accepted interpretation of
  D-10 per the applied override — this test also confirms/refutes whether that's sufficient
  in practice).
result: [pending]
reason: "Same .env blocker as test 1 — apps/api's /ask endpoint needs OPENROUTER_API_KEY."

### 3. Wiki viewer — all verification states + red links
expected: |
  Seed wiki_pages covering all 4 verification states (verified/expired/partial/unverified) +
  disputed + a resolved/red WikiLink pair. Read-only banner always shown. Correct callout per
  state. Disputed always takes visual priority over the verification callout. Resolved
  WikiLinks navigate; red links show the "아직 작성되지 않음 · 지금 생성" CTA and route to
  /sources with prefill (WINDOWS.md #12).
result: pass
source: automated
evidence: |
  Seeded a throwaway workspace with 6 wiki_pages (verified/expired/partial/unverified/disputed
  + a resolved-link target) plus a resolved and an unresolved wiki_link, via docker exec psql
  against the local Supabase stack. Drove the dashboard (next dev, port 3000) with a plain
  Playwright script (no gstack) as a real logged-in user. Confirmed: read-only banner on every
  page; exact callout text per state (검증됨/검증 만료됨/부분 검증됨/no callout for
  unverified); disputed page shows the disputed callout and NOT the verified callout (priority
  confirmed); resolved WikiLink renders as a real link; red WikiLink renders the CTA with
  aria-label="지금 생성". All seed data deleted afterward, verified 0 rows remaining.
  ⚠️ Found and fixed a real bug along the way (unrelated to this test's own assertions but
  discovered while getting the dashboard running): lib/env.ts's requireEnv() used
  `process.env[name]` (dynamic bracket access), which Next.js/webpack cannot statically inline
  into the client bundle — this broke EVERY client-side env read, including login itself. This
  was a regression from this session's own WR-05 code-review fix. Fixed with a switch-based
  lookup (see commit 1a11a1d) that stays both statically analyzable and per-call fresh (a
  first attempt using a module-scope object literal broke 14 vitest tests that mock
  process.env between calls — reverted in favor of the switch).

### 4. Graph canvas — 1000-node cap notice
expected: |
  Seed a workspace with >1,000 wiki_pages, load the graph canvas. The exact cap notice
  "이 워크스페이스는 그래프 표시 한도(1,000개 노드)를 초과했습니다 — 카테고리 필터로 범위를
  좁혀주세요." appears — never a silent truncation — and does NOT appear at exactly 1,000
  rows (WR-01 off-by-one fix).
result: pass
source: automated
evidence: |
  Seeded 1001 wiki_pages in a throwaway workspace via psql, loaded /graph as a real logged-in
  user via Playwright. First attempt failed: found and fixed a second real bug —
  GraphCanvas.tsx's edge query filtered `from_wiki_id IN (...)` with up to 1000 UUIDs, producing
  a URL long enough that the request failed outright (browser reported it as a CORS error; the
  real cause was URL-length rejection) — this broke the graph canvas completely exactly in the
  large-workspace case UI-06 exists to handle gracefully. Fixed by scoping the edge query to
  workspace_id only and relying on the client-side nodeIdSet filter the component already had
  (commit 613e5bc). After the fix: PostgREST content-range header confirmed count=1001, the
  exact cap-notice copy rendered. All seed data deleted afterward, verified 0 rows remaining.

### 5. Member removal under RLS-blocked condition
expected: |
  Attempt to remove a member in a state where RLS should block the delete. The
  "멤버를 제거하지 못했습니다." banner is shown and the member stays in the list (06-REVIEW-FIX.md
  WR-03 fix — confirms a 0-row delete result is detected, not silently treated as success).
result: pass
source: automated
evidence: |
  Created a throwaway workspace with an owner + a second (editor) member. Loaded /settings as
  the owner in a real browser session (client caches isOwner=true from the initial fetch).
  Without refreshing, transferred real ownership to the second member out-of-band via psql
  (workspaces.owner_id, then both members' workspace_members.role — the protect_owner_membership
  trigger requires owner_id to move first). Clicked the still-rendered "제거" button on the
  now-actual-owner: the RLS policy blocked the delete (0 rows, no error), the fix's
  post-delete .select() row-count check detected it, and the "멤버를 제거하지 못했습니다." error
  banner rendered. Confirmed via psql that the member was NOT removed. Restored original
  ownership and cleaned up all seed data afterward, verified 0 rows remaining.

## Summary

total: 5
passed: 3
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

## Bugs Found and Fixed During UAT (not user-reported issues — found via automated live testing)

- **lib/env.ts dynamic env access** (test 3): broke all client-side env reads including login.
  Fixed in commit `1a11a1d`.
- **GraphCanvas.tsx edge-query URL-length failure** (test 4): broke the graph canvas entirely
  near the 1000-node cap. Fixed in commit `613e5bc`.

Both fixes verified: `tsc --noEmit` clean, 77/77 vitest passing, and live Playwright re-run
confirming the fix in the browser.
