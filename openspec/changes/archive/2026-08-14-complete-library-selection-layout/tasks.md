## 1. Source detail route

- [x] 1.1 Add `apps/dashboard/app/w/[workspaceId]/sources/[id]/page.tsx` — Server Component mirroring `wiki/[slug]/page.tsx`'s pattern: fetch the single `raw_sources` row scoped by `workspace_id` + `id`, generic not-found fallback on error/missing row.
- [x] 1.2 Move the existing `DetailHeader` + 유형/등록일 `<dl>` markup from `SourcesList.tsx`'s accordion into this new route, with `libraryHref` pointing at the real `/w/[workspaceId]/sources` list route (not the `#sources-library` anchor).

## 2. Unify SourcesList selection

- [x] 2.1 Remove `selectedId` state and the inline accordion `<section>` from `SourcesList.tsx`.
- [x] 2.2 Replace the "상세 보기" toggle button with a `next/link` `Link` to `{workspacePath(workspaceId)}/sources/{source.id}`, matching `WikiLibrary.tsx`'s row pattern.
- [x] 2.3 Keep Dropzone and per-row JobStepper on the list page unchanged. (변경 없음, 확인만.)

## 3. Verification

- [x] 3.1 Run dashboard tests, typecheck, and lint. — 110 tests passed (3 new), typecheck clean, lint clean.
- [x] 3.2 Add/update component or route tests for the new source detail route and the updated `SourcesList` row (selection navigates, return link present). — `tests/source-detail-route.test.tsx`(신규), `tests/SourcesList.test.tsx`(케이스 추가)
- [x] 3.3 Browser-check `library-selection-layout` spec scenarios if credentials are available this session; otherwise static verification only, same caveat as `complete-graph-surface-separation`. — 이번 세션도 클라우드 Supabase 자격 증명 없음 (Change A와 동일 사유, 사용자가 이미 정적 검증으로 진행하기로 결정함). 정적 확인: 새 라우트가 `wiki/[slug]/page.tsx`와 동일한 조회/폴백 패턴을 그대로 재사용했고, 라우트/컴포넌트 테스트가 return-link href와 not-found 문구를 직접 검증함.
- [x] 3.4 Run `openspec validate complete-library-selection-layout --strict`. — "Change 'complete-library-selection-layout' is valid"
