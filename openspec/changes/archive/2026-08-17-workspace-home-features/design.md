## Context

`apps/dashboard/app/w/[workspaceId]/page.tsx`를 v2 디자인 시스템(`workspace-home-prd.md` 및 `nexuswiki-workspace-home.html`)에 맞추어 개편합니다. 사용자가 진입 시 한눈에 워크스페이스 현황(통계)을 파악하고, Ask 히어로를 통해 첫 질문을 신속히 시작하며, 2열 지식 그리드에서 검증된 위키와 작성 대기 백로그를 탐색할 수 있도록 컴포넌트를 분리하여 구현합니다.

## Goals / Non-Goals

**Goals:**
- `AskHero.tsx`: 질문 입력창, 3종 스타터 칩, 검색 스코프 드롭다운(워크스페이스 전체/선택 카테고리/현재 문서 주변) 제공.
- `CategoryLensFilter.tsx`: 전체 + 4종 카테고리(개념/엔티티/가이드/맵) 필터링 렌즈 컴포넌트 구현.
- `KnowledgeGrid.tsx`: 좌측 위키 피드(검증 완료 뱃지, 카테고리 표시명, 인용 소스 수) + 우측 미해결 백로그 피드 및 소스 추가 CTA 2컬럼 레이아웃.
- `page.tsx`: RLS를 통한 안전한 지표(문서 수, 소스 수, 백로그 수, 최종 업데이트) 조회 및 컴포넌트 통합.

**Non-Goals:**
- SSE 스트리밍 응답 바인딩 (`ASK-01`에서 처리, AskHero에서는 `/w/[workspaceId]/ask?q=...` 라우팅만 수행).
- 컬렉션 스키마 바인딩 (`OD-01` 미해결 항목).

## Decisions

- **Decision 1: AskHero 클라이언트 컴포넌트화**
  - *Rationale*: 질문 입력 상태 관리, 칩 클릭 시 자동 채움 및 포커스, 스코프 메뉴 토글을 위해 클라이언트 컴포넌트로 분리합니다.
- **Decision 2: 카테고리 필터링의 URL Query 및 클라이언트 상태 지원**
  - *Rationale*: URL query param (`?category=...`)과 상호 연동되어 LNB 렌즈 및 본문 필터 렌즈 어디서든 일관되게 동작하도록 구성합니다.
- **Decision 3: 백엔드 스키마 기반 실재 쿼리 사용**
  - *Rationale*: `wiki_pages`, `raw_sources`, `wiki_links` 테이블에 실재하는 컬럼만 조회하며 가공되지 않은 통계 수치를 RLS 하에 계산합니다.

## Risks / Trade-offs

- **[Risk] 데이터가 없는 신규 워크스페이스의 레이아웃 붕괴** → 위키 및 백로그 데이터가 0개일 때 친절한 빈 상태(Empty State) 안내와 '첫 소스 추가' 가이드를 표시하도록 방어합니다.
