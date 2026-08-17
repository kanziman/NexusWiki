## Context

`/ask`(`AskConversation.tsx`)와 `/wiki/[slug]`(`WikiPageContent.tsx`)는 완전히 분리된 라우트다. `GraphLensFilter.tsx`는 이미 "URL이 상태"인 패턴(`useSearchParams`/`useRouter`, `router.push`)을 쓰고 있다. `wiki_pages.sources`(원문 역추적 id 배열)는 스키마에 있지만 어떤 화면도 안 읽는다. `GraphCanvas.tsx`는 `wiki_links`를 클라이언트에서 fetch해 Cytoscape로 렌더링한다(force-directed류 레이아웃, 정확한 레이아웃 이름은 구현 시 `GraphCanvas.tsx` 확인). See proposal.md - Why.

## Goals / Non-Goals

**Goals:**
- `/ask`를 상시 셸로 승격하고 우측에 위키/소스/그래프/마인드맵 뷰어를 붙인다.
- 기존 `/wiki/[slug]`, `/graph` URL을 깨지 않는다 (리다이렉트).
- 새 백엔드 작업 없이 기존 데이터(`wiki_pages.sources`, `wiki_links`)만으로 소스/마인드맵 탭을 만든다.

**Non-Goals:**
- `/sources`, `/wiki` 목록 라우트 변경 — Change B(라우트 기반 선택 통일)와 무관하게 그대로 둔다.
- shadcn/ui, Magic UI, react-resizable-panels 도입 — 이전 대화에서 이미 스코프 제외 결정됨. 좌우 분할은 CSS flex/grid로 충분하고(리사이즈 드래그는 이번 change의 요구사항이 아님), quiet editorial 라이트 테마를 유지한다.
- primary 색상(빨강/검정) 불일치 정리 — 별도 change 대상.

## Decisions

- **좌우 분할은 고정 비율 flex, 리사이즈 드래그 없음**: 이번 change의 목표는 "같은 화면에 동시 노출"이지 사용자가 드래그로 폭을 조절하는 것이 아니다. `react-resizable-panels` 없이 `flex` 두 칸(예: `flex-[2]`/`flex-[3]`)으로 충분 — Non-Goal 참고. 나중에 리사이즈가 필요해지면 별도 change로 추가한다.
- **탭/대상 상태는 쿼리 파라미터**: `?tab=wiki|source|graph|mindmap&slug=<wiki-slug>`. `GraphLensFilter.tsx`가 이미 쓰는 패턴과 동일해 새 상태 관리 라이브러리가 필요 없다. `source` 탭은 `slug`로 위키를 특정한 뒤 그 위키의 `sources` 배열을 보여주는 구조라 별도 소스 id 파라미터는 필요 없다(위키 문서 하나당 원시 소스 여러 개를 한 번에 보여줌).
- **레거시 라우트는 Next.js `redirect()`로 구현**: `/wiki/[slug]/page.tsx`는 기존 조회 로직(slug 디코딩·조회·not-found)을 그대로 실행해 페이지 존재를 검증한 뒤(그래야 `wiki-page-routing` 스펙의 malformed/cross-workspace 시나리오가 그대로 유지됨), 존재가 확인되면 `redirect(`/ask?slug=${slug}&tab=wiki`)`로 넘긴다. `/graph/page.tsx`는 조건 없이 `redirect("/ask?tab=graph")`.
- **원시 소스 탭**: `wiki_pages.sources`(raw_source id 배열)를 `raw_sources`에 `in()` 조회 — `CitationSidePanel.tsx`의 `source_chunks` 단건 조회 패턴과는 다르게(그건 인용 앵커 하나당 청크 하나) 이번엔 위키 페이지당 여러 원시 소스이므로 목록 형태로 렌더링한다.
- **마인드맵 탭**: `GraphCanvas.tsx`가 이미 fetch하는 `wiki_links` 엣지 데이터를 재사용하되, Cytoscape 레이아웃 옵션만 `breadthfirst`(현재 위키 페이지를 루트로) 로 바꿔 별도 인스턴스로 렌더링한다. 데이터 재사용이 핵심 — 새 쿼리를 만들지 않는다.
- **인용 마커 클릭 동작 변경**: `AskConversation.tsx`의 `handleMarkerClick`이 지금은 `setPanelPart`(오버레이 상태)를 호출하는데, 이걸 `router.push`로 우측 뷰어의 쿼리 파라미터를 바꾸는 것으로 교체한다. `CitationSidePanel`은 이 change에서 더 이상 Ask 화면에 쓰이지 않지만, 컴포넌트 자체는 삭제하지 않는다(다른 곳에서 재사용 가능성 — Non-Goal이자 최소 변경 원칙).

## Risks / Trade-offs

- [Risk] `/wiki/[slug]`가 리다이렉트를 거치면서 기존 "그 페이지 하나만 보는" 조용한 읽기 경험이 항상 Ask 패널과 함께 뜨는 것으로 바뀐다 — 사용자가 원치 않을 수 있음 → Mitigation: 이건 사용자가 이미 명시적으로 선택한 방향("새 통합 라우트로 승격")이므로 이번 change에서는 그대로 받아들이고, 향후 피드백에서 "Ask 패널 접기" 같은 요청이 나오면 별도 change로 다룬다.
- [Risk] `wiki_pages.sources`에 담긴 id가 삭제된 원문을 가리킬 수 있음(하드 delete 정책 불명) → Mitigation: `raw_sources` 조회 결과가 비어 있으면 "원문을 찾을 수 없음" 같은 빈 상태로 처리하고 에러를 던지지 않는다 — `wiki-page-routing`의 "malformed/not-found는 조용히 처리" 관례와 동일.
- [Risk] 리다이렉트 체인이 늘어나며 첫 로드가 한 번의 왕복만큼 느려짐 → Mitigation: Server Component에서 `redirect()`는 응답 자체가 302이므로 클라이언트 왕복이 아니라 서버 사이드 한 홉 — 실사용상 체감 차이는 미미할 것으로 판단, 별도 성능 작업 없음.

## Migration Plan

1. `unified-workspace-viewer` 신규: `/ask` 셸 + `ContentViewer` 먼저 만들고 기존 `/wiki/[slug]`, `/graph`는 건드리지 않는다 (병행 가동 가능한 상태).
2. `ContentViewer`의 4개 탭이 각각 기존 컴포넌트 재사용으로 정상 동작함을 확인한 뒤에만 `/wiki/[slug]`, `/graph`에 `redirect()`를 추가한다 — 이 순서를 지키면 리다이렉트가 깨진 화면으로 연결되는 상황을 피할 수 있다.
3. 롤백은 리다이렉트 두 줄만 제거하면 원래 독립 라우트로 즉시 복귀 가능 — 위험도가 낮다.
