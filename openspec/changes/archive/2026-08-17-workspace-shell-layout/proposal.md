## Why

NexusWiki v2 마일스톤 2의 대시보드 화면 구현(Phase 1: 홈 대시보드)을 시작하기 위해, 전체 워크스페이스 화면의 뼈대가 되는 3분할 셸 레이아웃(LNB 사이드바 + 탑바 + 콘텐츠 영역)과 반응형 구조를 구축해야 합니다. 또한 기존 진입 화면에 남아 있던 3계층 잔재 어휘('프로젝트')를 불변식 §1에 맞추어 '워크스페이스'로 통일합니다.

## What Changes

- **워크스페이스 셸 레이아웃 (LNB + 탑바 + 콘텐츠 영역)**: v2 디자인 시스템 CSS 토큰(`nexuswiki-design-system.css`)을 기반으로 사이드바(LNB), 상단 바, 메인 콘텐츠 영역 3분할 레이아웃을 구축합니다.
- **반응형 뷰포트 지원**: 390px(모바일 드로어/서랍), 640px, 900px, 1280px, 1680px 전 뷰포트에서 가로 스크롤 없이 유연하게 적응하도록 레이아웃 규칙을 적용합니다.
- **WorkspaceEntryChooser 어휘 정정**: `WorkspaceEntryChooser.tsx` 및 관련 컴포넌트의 구버전 잔재 '프로젝트' 문구를 '워크스페이스'로 통일하여 불변식 §1을 완전히 준수합니다.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `workspace-home-dashboard`: v2 3분할 셸 레이아웃(LNB + 탑바 + 콘텐츠)과 모바일 뷰포트 서랍(drawer) 내비게이션, 반응형 요구사항을 추가합니다.

## Impact

- **대상 파일**:
  - `apps/dashboard/app/w/[workspaceId]/layout.tsx`
  - `apps/dashboard/components/WorkspaceSidebar.tsx` (신규/개편)
  - `apps/dashboard/components/NavShell.tsx`
  - `apps/dashboard/components/WorkspaceEntryChooser.tsx`
- **의존성/API**: 기존 RLS 테넌시 및 워크스페이스 조회 흐름을 유지하며 프론트엔드 레이아웃 셸을 개선합니다.
