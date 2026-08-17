## Why

지금 질문하기(`/ask`)와 위키 열람(`/wiki/[slug]`)은 완전히 분리된 페이지다. 사용자가 Ask에서 인용 마커를 클릭하면 400px짜리 오버레이 패널(`CitationSidePanel`)이 잠깐 뜨는 게 전부이고, 위키 문서 전체나 그래프를 보려면 다른 라우트로 이동해야 한다. Cairni 레퍼런스(`docs/ref/ref0.png`, `ref2.png`)처럼 좌측 AI 대화와 우측 콘텐츠 뷰어를 한 화면에서 같이 쓰고 싶다는 게 이 change의 목적이다 (Linear HHH-20).

## What Changes

- `/w/[workspaceId]/ask`를 상시 셸로 승격한다: 좌측 = 기존 `AskConversation`(그대로 재사용), 우측 = 신규 `ContentViewer` — 위키 문서 / 원시 소스 / 2D 지식 그래프 / 마인드맵 4개 탭.
- `?slug=<wiki-slug>`, `?tab=wiki|source|graph|mindmap` 쿼리 파라미터로 우측 패널 대상을 제어한다 (`GraphLensFilter.tsx`가 이미 쓰는 "URL이 상태" 패턴 재사용).
- `/wiki/[slug]`, `/graph`는 이 통합 뷰(`/ask?slug=...&tab=wiki`, `/ask?tab=graph`)로 리다이렉트한다.
- Ask 대화 중 `CitationMarker` 클릭 시, 지금처럼 별도 오버레이(`CitationSidePanel`)를 여는 대신 우측 `ContentViewer`의 탭을 해당 위키/소스로 전환한다.
- **원시 소스 탭(신규)**: `wiki_pages.sources`(위키→원문 역추적 id 배열, `0001_core_schema.sql:151-152`에 이미 존재하지만 현재 어떤 화면에서도 쓰이지 않음)를 `raw_sources`/`source_chunks`에 조인해 렌더링.
- **마인드맵 탭(신규)**: `GraphCanvas.tsx`가 이미 가져오는 `wiki_links` 간선 데이터를 그대로 쓰고, 현재 위키 페이지를 중심으로 한 `breadthfirst` 계열 Cytoscape 레이아웃으로 렌더링 — 새 백엔드/데이터 작업 없음.
- **BREAKING**: `/wiki/[slug]`, `/graph`의 기존 URL은 계속 동작하지만(리다이렉트) 더 이상 그 자체로 렌더되는 최종 목적지가 아니다.

## Capabilities

### New Capabilities

- `unified-workspace-viewer`: AI 대화와 위키/소스/그래프/마인드맵 뷰어를 한 화면에서 동시에 제공하고, 인용 클릭이 뷰어 탭 전환으로 이어지는 통합 열람 경험.

### Modified Capabilities

- `wiki-page-routing`: "위키 상세 라우트"가 `/wiki/[slug]` 단독이 아니라 리다이렉트를 거친 통합 뷰(`/ask?slug=...`)까지 포함하도록 범위가 넓어진다. 기존 시나리오(정규 slug 디코딩, malformed 처리, cross-workspace 격리)는 결과 화면이 바뀔 뿐 그대로 유지되어야 한다.
- `dashboard-design-consistency`: "Home, Sources, Ask, Wiki, Graph, Settings" 목적지 목록에서 Wiki·Graph가 독립 목적지가 아니라 Ask 내부의 뷰어 탭이 되므로, "일관된 페이지 프레임" 요구사항이 탭 전환에도 적용됨을 명시한다.

## Impact

- `apps/dashboard/app/w/[workspaceId]/ask/page.tsx`, 신규 `ContentViewer` 컴포넌트, `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx`·`graph/page.tsx`(리다이렉트로 축소), `AskConversation.tsx`(마커 클릭 동작 변경), `CitationMarker.tsx`/`CitationSidePanel.tsx`(재사용 방식 변경).
- Sources/Wiki 목록 라우트(`/sources`, `/wiki`)와 Change B에서 만든 `/sources/[id]`는 변경하지 않는다 — 이 change는 "읽기/질문하기" 소비 경험만 다룬다.
- Linear HHH-20 (id `507cd780-57a9-4058-9aac-a8b8ba5ecdf4`).
