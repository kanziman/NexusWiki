## Context

현재 `apps/dashboard/app/w/[workspaceId]/layout.tsx`는 단순 상단 헤더(`NavShell`)와 중앙 컨테이너로 구성되어 있습니다. v2 디자인 시스템(`docs/design-systems/v2/workspace-home-prd.md` 및 `nexuswiki-workspace-home.html`)에 따라 LNB(좌측 사이드바) + 상단 바 + 메인 콘텐츠 영역의 3분할 반응형 셸 레이아웃으로 개편이 필요합니다.

## Goals / Non-Goals

**Goals:**
- v2 디자인 토큰(`--nw-*`, `--font-*`)을 활용한 3분할 셸 레이아웃 구조 구축.
- 데스크톱(900px+) 고정 사이드바, 모바일(390px, 640px) 서랍(Drawer) 토글 지원.
- 가로 스크롤 없는 반응형 레이아웃 보장 (390/640/900/1280/1680px).
- `WorkspaceEntryChooser.tsx`의 '프로젝트' 잔재 어휘 제거 및 '워크스페이스'로 통일.

**Non-Goals:**
- Ask SSE 스트리밍 연동 (`ASK-01`에서 처리).
- 카테고리 렌즈 필터링 로직 구현 (`HOME-02`에서 처리).
- 컬렉션 스키마 및 UI 연동 (`OD-01` 미해결 항목, 이번 범위 제외).

## Decisions

- **Decision 1: 레이아웃 셸 컴포넌트 분리 (`WorkspaceSidebar` + `WorkspaceHeader`)**
  - *Rationale*: 서버 컴포넌트인 `layout.tsx`에서 테넌시 검증 및 워크스페이스 목록을 조회하고, 사이드바와 반응형 드로어 제어를 클라이언트 셸 컴포넌트로 위임합니다.
  - *Alternatives considered*: 전체 레이아웃을 클라이언트 컴포넌트로 전환하는 방안은 SSR 테넌시 검증 및 보안(RLS) 이점을 잃으므로 배제.

- **Decision 2: 반응형 브레이크포인트 및 모바일 드로어**
  - *Rationale*: 640px 이하에서는 상단 바의 메뉴 버튼으로 사이드바를 오버레이 드로어로 열고 닫으며, 900px 이상에서는 상시 노출 사이드바로 배치합니다.

## Risks / Trade-offs

- **[Risk] 하위 페이지(sources, wiki, settings 등)의 레이아웃 호환성 깨짐** → 메인 콘텐츠 영역의 패딩 및 flex/grid 확장을 유연하게 구성하여 기존 하위 페이지들이 가로 스크롤 없이 자연스럽게 배치되도록 격리합니다.
