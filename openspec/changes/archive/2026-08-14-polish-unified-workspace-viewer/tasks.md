## 1. Remove dead graph nav entry

- [x] 1.1 Remove `{ segment: "/graph", label: "그래프" }` from `NavShell.tsx`'s `ROUTES`.
- [x] 1.2 Update `NavShell.test.tsx` to drop "그래프" from the expected link labels.

## 2. Fix layout height utility

- [x] 2.1 ~~Replace `ask/page.tsx`'s `lg:h-[calc(100vh-var(--spacing-xxl)*2)]` Tailwind class with an inline `style` literal~~ — **투자 결과 false alarm으로 판명, 코드 변경 없음.** `.planning/STATE.md:177`의 원본 기록을 다시 읽어보니 WINDOWS #11은 "Tailwind **이름 있는** 유틸리티(`max-w-xl`, `h-sm` 등)의 접미사가 커스텀 `--spacing-*` 키 이름과 겹칠 때"만 발생한다(`max-w-xl` → 32px로 오해석된 실측 사례). `h-[calc(...)]`는 arbitrary-value 문법이라 이름 조회 자체가 없어 해당 없음. 실제로 `pnpm build` 후 컴파일된 CSS를 확인해 `height:calc(100vh - var(--spacing-xxl) * 2)`가 그대로(왜곡 없이) 나오는 것을 검증했다. 처음엔 인라인 style로 바꿨다가 `lg:` 반응형 브레이크포인트를 잃는 실제 회귀를 만들 뻔했고, 검증 후 원래 코드로 되돌렸다.

## 3. Scope the wiki lookup in handleMarkerClick

- [x] 3.1 Add `.eq("workspace_id", workspaceId)` to `AskConversation.tsx`'s `handleMarkerClick` wiki-slug query.
- [x] 3.2 Update `AskConversation.test.tsx`'s supabase mock/assertions — extended `makeQueryBuilder` to track `.eq()` calls per table and added a dedicated wiki-marker-click test asserting `workspace_id`/`id` are both used to scope the lookup.

## 4. Complete tab accessibility

- [x] 4.1 Wire `id`/`aria-controls` between `ContentViewer`'s tab buttons and their content panels, and add `role="tabpanel"`/`aria-labelledby` on each panel.
- [x] 4.2 Add roving `tabIndex` (active tab `0`, others `-1`) and arrow-key (←/→) navigation across the tab buttons, with wraparound.

## 5. Verification

- [x] 5.1 Run dashboard tests, typecheck, lint, and a production build. — 121 tests passed, typecheck clean, lint clean, `pnpm build` succeeded.
- [x] 5.2 Add/update tests: NavShell no longer has a graph link, ContentViewer tab/panel ARIA wiring and arrow-key navigation (including wraparound), AskConversation wiki-marker workspace scoping.
- [x] 5.3 Browser-check if credentials are available this session; otherwise static verification only (same caveat as prior changes in this session). — 이번 세션도 클라우드 Supabase 자격 증명 없음. 항목 1/3/4는 테스트로 직접 검증. 항목 2는 `pnpm build`로 컴파일된 CSS를 직접 파싱해 검증(위 섹션 2 참고) — false alarm으로 판명, 코드 변경 없음.
- [x] 5.4 Run `openspec validate polish-unified-workspace-viewer --strict`.
