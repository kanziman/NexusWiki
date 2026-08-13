## 1. Content viewer shell

- [x] 1.1 Add a `ContentViewer` component that reads `?tab=wiki|source|graph|mindmap&slug=` from the URL and renders the matching pane, defaulting to an empty/no-selection state when no `slug` is present. — `apps/dashboard/components/ContentViewer.tsx`
- [x] 1.2 Update `apps/dashboard/app/w/[workspaceId]/ask/page.tsx` to render `AskConversation` and `ContentViewer` side by side (fixed-ratio flex layout, no resizable dependency).

## 2. Wiki document tab

- [x] 2.1 Wire the `wiki` tab to fetch and render the wiki page for `?slug=` using the same lookup as `wiki/[slug]/page.tsx` (decoded slug, workspace-scoped, generic not-found), reusing `WikiPageContent`. — lookup logic extracted to `apps/dashboard/lib/wiki-lookup.ts` and shared by both.

## 3. Raw source tab

- [x] 3.1 Fetch `wiki_pages.sources` for the active `?slug=` wiki page and resolve it against `raw_sources` (`in()` query), rendering an empty state when there are no backing sources or any are missing. — also added `?chunkId=` handling for citation-originated single-chunk views (discovered during implementation: a citation marker's `source` kind points at one `source_chunks` row, not a wiki page's backing-sources list — these are different data shapes, both now live in `SourceTab`).

## 4. 2D graph tab

- [x] 4.1 Wire the `graph` tab to render the existing `GraphCanvas` + `GraphLensFilter`, unchanged.

## 5. Mind map tab

- [x] 5.1 Add a mind-map rendering mode that reuses `GraphCanvas`'s existing `wiki_links` fetch but with a `breadthfirst` Cytoscape layout rooted at the active `?slug=` page. — `GraphCanvas` gained optional `layoutName`/`rootSlug` props, default behavior (`cose`) unchanged for the existing graph tab.

## 6. Citation click integration

- [x] 6.1 Change `AskConversation.tsx`'s `handleMarkerClick` to update the URL's `tab`/`slug` query params (wiki or source tab depending on the marker's kind) instead of opening `CitationSidePanel`. — wiki-kind markers resolve id→slug first (marker only carries `wiki_pages.id`, `ContentViewer` is slug-based); source-kind markers push `?chunkId=`. `CitationSidePanel.tsx` left in place, unused by this route (Non-Goal — not deleted).

## 7. Legacy route redirects

- [x] 7.1 Add a `redirect()` to `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx` that runs after the existing slug lookup succeeds, forwarding to `/ask?slug=<slug>&tab=wiki`. Keep the existing not-found/malformed-slug handling untouched (no redirect on failure).
- [x] 7.2 Add a `redirect()` to `apps/dashboard/app/w/[workspaceId]/graph/page.tsx` forwarding to `/ask?tab=graph`. — this route no longer fetches data itself (`ContentViewer`'s graph tab does), so `GraphLensFilter`/`GraphCanvas` imports moved out of the page file.

## 8. Verification

- [x] 8.1 Run dashboard tests, typecheck, and lint. — 117 tests passed, typecheck clean, lint clean.
- [x] 8.2 Add/update tests: ContentViewer tab switching, wiki-route redirect (success + not-found does NOT redirect), graph-route redirect, citation marker click updates query params instead of opening the overlay panel. — `tests/ContentViewer.test.tsx`(신규), `tests/graph-page-route.test.tsx`(신규), `tests/wiki-page-route.test.tsx`(리다이렉트 검증으로 갱신 + not-found 시 미호출 케이스 추가), `tests/AskConversation.test.tsx`(마커 클릭 → push 검증으로 갱신).
- [x] 8.3 Browser-check `unified-workspace-viewer`, modified `wiki-page-routing`, and modified `dashboard-design-consistency` spec scenarios if credentials are available this session; otherwise static verification only (same caveat as prior changes in this session). — 이번 세션도 클라우드 Supabase 자격 증명 없음(Change A/B와 동일 사유, 사용자가 이미 정적 검증으로 진행하기로 결정함). 정적 확인: 탭 전환/리다이렉트/마커 통합 전부 테스트로 직접 검증됨.
- [x] 8.4 Run `openspec validate add-unified-workspace-viewer --strict`.

## 9. Spec sync

- [x] 9.1 Run `openspec-sync-specs` to merge this change's delta specs into `openspec/specs/unified-workspace-viewer/`, `openspec/specs/wiki-page-routing/`, and `openspec/specs/dashboard-design-consistency/` before archiving. — `openspec validate --specs`: 13 passed, 0 failed.
