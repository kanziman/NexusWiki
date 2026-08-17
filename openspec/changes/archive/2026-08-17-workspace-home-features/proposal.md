## Why

NexusWiki v2 워크스페이스 홈 대시보드의 핵심 기능인 질문 시작점(Ask 히어로 캔버스 + 스타터 칩), 카테고리 렌즈 필터(개념/엔티티/가이드/맵), 그리고 컴파일된 위키 문서와 미완성 백로그를 보여주는 2컬럼 지식 그리드를 구현하여 사용자가 지식을 탐색하고 질문을 즉시 시작할 수 있도록 합니다.

## What Changes

- **Ask 히어로 캔버스 (`AskHero.tsx`)**: 다중 라인 질문 입력창, 검색 범위(스코프) 선택 메뉴, 질문하기 버튼, 추천 스타터 질문 칩 3종 제공. (HOME-03)
- **카테고리 렌즈 필터링 (`CategoryLensFilter.tsx` 및 홈 쿼리 연동)**: 전체 및 4종 카테고리(개념/엔티티/가이드/맵) 필터 렌더링 및 선택 시 위키 피드 필터링. (HOME-02)
- **2컬럼 지식 그리드 (`KnowledgeGrid.tsx`)**: 좌측에는 최신 컴파일된 위키 문서 목록(검증 완료 뱃지, 카테고리 표시)과 우측에는 미해결 링크 백로그 목록 및 소스 연결 CTA 제공. (HOME-04)
- **홈 대시보드 메인 페이지 갱신 (`page.tsx`)**: 히어로 통계 요약(문서 수, 소스 수, 백로그 수, 최종 업데이트 일시) 및 위 컴포넌트 통합.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `workspace-home-dashboard`: Ask 히어로 캔버스 질문 시작점, 스타터 칩, 카테고리 렌즈 필터링, 그리고 위키 및 미완성 백로그 2컬럼 지식 피드 요구사항을 추가합니다.

## Impact

- **대상 파일**:
  - `apps/dashboard/app/w/[workspaceId]/page.tsx`
  - `apps/dashboard/components/AskHero.tsx` (신규)
  - `apps/dashboard/components/KnowledgeGrid.tsx` (신규)
  - `apps/dashboard/components/CategoryLensFilter.tsx` (신규)
- **의존성/API**: Supabase RLS 쿼리(`workspaces`, `wiki_pages`, `raw_sources`, `wiki_links`)를 안전하게 호출하여 테넌시 격리된 지식 데이터를 바인딩합니다.
