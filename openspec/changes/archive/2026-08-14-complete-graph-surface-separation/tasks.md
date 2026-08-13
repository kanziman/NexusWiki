## 1. Canvas surface separation

- [x] 1.1 Give `apps/dashboard/components/GraphCanvas.tsx`'s canvas wrapper a `--nw-canvas` (#fcfcfa) background so it reads as a distinct surface from the filter section (`--nw-surface`, #ffffff).
- [x] 1.2 Confirm `apps/dashboard/app/w/[workspaceId]/graph/page.tsx`'s filter section keeps its existing `--nw-surface` background and `aria-label="지식 그래프"` on the canvas section is unchanged. (확인만, 코드 변경 없음 — 30/41번 줄 그대로.)

## 2. Verification

- [x] 2.1 Run dashboard tests, typecheck, and lint (`pnpm --filter dashboard test`, `typecheck`, `lint`). — 107 tests passed, typecheck clean, lint clean.
- [x] 2.2 Browser-check `/w/[workspaceId]/graph` against `graph-surface-separation` spec scenarios (member can distinguish control region from canvas before interacting; keyboard focus reaches a labelled canvas region). **사용자 승인 하에 정적 검증으로 대체**: 로컬 dev server(3000번 포트)가 클라우드 Supabase(`dajhhwbkfdaqnuenulsb.supabase.co`)를 바라보고 있어 이 세션에 로그인 자격 증명이 없다. 대신 정적으로 확인: `--nw-canvas`는 이미 `body` 배경(globals.css:76)으로 쓰이고 있어 값 자체는 검증된 토큰이고, `bg-[var(--nw-canvas)]` arbitrary-value 클래스는 typecheck/lint/test 전부 클린 통과. 실제 브라우저 시각 확인은 자격 증명이 생기면 사용자가 직접 하기로 함.
- [x] 2.3 Run `openspec validate complete-graph-surface-separation --strict`. — "Change 'complete-graph-surface-separation' is valid"
