## Why

HHH-20(통합 워크스페이스 뷰어) 배포 직후 재점검에서 네 가지를 발견했다:

1. `NavShell`의 "그래프" 메뉴가 `/ask?tab=graph`로 리다이렉트만 하는 죽은 링크가 됐다 — 사용자가 직접 요청.
2. `ask/page.tsx`의 `h-[calc(100vh-var(--spacing-xxl)*2)]`가 이 코드베이스가 이미 두 번 겪고 기록한 "WINDOWS #11"(커스텀 `--spacing-*` @theme 토큰과 Tailwind 이름 있는 `w-*/h-*/max-w-*` 유틸리티 충돌) 회피 컨벤션을 어겼다.
3. `AskConversation.handleMarkerClick`의 위키 조회가 `workspace_id` 스코프 없이 실행된다 — RLS가 실제 경계라 뚫리진 않지만, 코드베이스 나머지 전부가 지키는 방어적 스코핑 관례와 불일치.
4. `ContentViewer`의 탭이 `role="tablist"`/`"tab"`을 선언하면서도 tabpanel 연결(`aria-controls`)과 화살표 키 이동이 없어, `unified-workspace-viewer`/`dashboard-design-consistency` 스펙이 요구하는 "일관된 키보드 포커스 처리"를 실제로 충족하지 못한다.

Linear HHH-22.

## What Changes

- `NavShell.tsx`의 `ROUTES`에서 `{ segment: "/graph", label: "그래프" }` 제거.
- `ask/page.tsx`의 좌우 분할 컨테이너 높이를 Tailwind arbitrary-value 클래스 대신 인라인 `style`로 지정(`GraphCanvas.tsx`/`CitationSidePanel.tsx`와 동일 패턴).
- `handleMarkerClick`의 위키 slug 조회에 `.eq("workspace_id", workspaceId)` 추가.
- `ContentViewer`의 탭 버튼과 콘텐츠 패널을 `id`/`aria-controls`/`role="tabpanel"`로 연결하고, 방향키(←/→)로 탭 간 이동 + roving tabindex를 구현한다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

없음 — 관련 스펙(`unified-workspace-viewer`, `dashboard-design-consistency`) 요구사항 문구는 이미 정확하며 바뀌지 않는다. 이번 change는 그 요구사항을 실제로 충족시키는 구현 갭(항목 4)과 그 외 정리 항목(1~3)을 처리한다 (`.openspec.yaml`에 `skip_specs: true` 선언).

## Impact

- `apps/dashboard/components/NavShell.tsx`, `apps/dashboard/tests/NavShell.test.tsx`
- `apps/dashboard/app/w/[workspaceId]/ask/page.tsx`
- `apps/dashboard/components/AskConversation.tsx`, `apps/dashboard/tests/AskConversation.test.tsx`
- `apps/dashboard/components/ContentViewer.tsx`, `apps/dashboard/tests/ContentViewer.test.tsx`
- Linear HHH-22 (id `8dcfd3e7-aa98-4a80-9438-80f82bb4c49e`).
