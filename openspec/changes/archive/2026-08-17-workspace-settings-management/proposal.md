# Proposal: workspace-settings-management

## Why

NexusWiki v2 워크스페이스 설정 화면(`/w/[workspaceId]/settings`)은 워크스페이스의 기본 정보(이름, 슬러그) 관리, 멤버 로스터 및 초대(RBAC), 백그라운드 운영 상태(예산 및 5단계 파이프라인)를 체계적으로 제공해야 한다.
기존 설정 화면은 2탭 구조로 되어 있어 기본 정보 편집 기능이 부재하고, 멤버 초대 폼이 owner가 아닌 역할에게도 노출되는 버그가 존재한다.

## What Changes

1. **설정 3탭 셸 레이아웃 (`SETTINGS-01`)**:
   - `일반`(General), `멤버`(Members), `운영 현황`(Operations - owner/editor 전용) 3탭 구조 구현
   - v2 디자인 시스템 CSS 토큰 및 반응형 탭 내비게이션 적용
2. **워크스페이스 기본 정보 관리 (`SETTINGS-02`)**:
   - `WorkspaceGeneralSettings` 컴포넌트 추가
   - 워크스페이스 이름 및 슬러그 조회/수정 기능 제공
   - owner만 수정 가능하도록 RBAC 및 유효성 검사 적용
3. **멤버 초대 폼 owner 게이트 버그 수정 (`SETTINGS-03`)**:
   - `SettingsMembersPanel`에서 `canInvite = currentRole === "owner"`로 초대 폼 노출 제어
   - viewer/editor에게는 초대 폼을 렌더링하지 않고 멤버 목록만 제공
4. **운영 현황 카드 v2 디자인 연동 (`SETTINGS-04`)**:
   - `OperationsPanel`의 예산 사용량 및 5단계 파이프라인(parse, compile, link_sync, embed, conflict_check) 모니터링 연동 및 검증

## Validation Plan

- 단위 테스트: `WorkspaceGeneralSettings.test.tsx`, `SettingsMembersPanel.test.tsx`, `MembersList.test.tsx`, `InviteForm.test.tsx`, `OperationsPanel.test.tsx`
- TypeScript typecheck, ESLint, Next.js build 전체 통과
- GitHub Issue #27 연결
