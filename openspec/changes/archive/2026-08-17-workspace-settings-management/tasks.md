## 1. 워크스페이스 기본 정보 컴포넌트 구현 (SETTINGS-02)

- [x] 1.1 `apps/dashboard/components/WorkspaceGeneralSettings.tsx` 구현 (이름·슬러그 조회 및 수정, 유효성 검사, owner RBAC 게이트)

## 2. 설정 화면 3탭 레이아웃 및 멤버 초대 게이트 구현 (SETTINGS-01, SETTINGS-03)

- [x] 2.1 `apps/dashboard/components/SettingsMembersPanel.tsx` 3탭(`일반`, `멤버`, `운영 현황`) 구조로 개편
- [x] 2.2 `SettingsMembersPanel.tsx`에서 `canInvite = currentRole === "owner"`로 초대 폼 노출 제어 (버그 수정)
- [x] 2.3 `apps/dashboard/app/w/[workspaceId]/settings/page.tsx`에서 워크스페이스 정보(이름, 슬러그) 조회 및 props 전달

## 3. 운영 현황 및 검증 (SETTINGS-04)

- [x] 3.1 단위 테스트 작성 (`WorkspaceGeneralSettings.test.tsx`, `SettingsMembersPanel.test.tsx` 갱신)
- [x] 3.2 TypeScript typecheck, Vitest, ESLint, Next.js build 전체 검증
