## Why

원문 소스 관리(`apps/dashboard/components/SourcesList.tsx`)는 홈 대시보드·위키 라이브러리가 벤토 메트릭과 카드-로우로 옮겨간 뒤에도 3칸 평면 통계 바와 6열 `<table>`에 머물러 있다. 연결된 위키 칩이 3~5개인 소스에서만 행이 세로로 늘어나 목록 리듬이 깨지고, 좁은 화면에서는 `overflow-x-auto` 가로 스크롤이 강제되며, 필터 탭과 검색창이 서로 다른 높이로 놓여 툴바 수평선이 어긋난다. 무엇보다 청킹 진행률과 위키 인용 연결률이라는 이 화면의 핵심 신호가 숫자 나열에 묻혀 읽히지 않는다.

근거: `docs/design-systems/sources-redesign-plan.md` §1.

## What Changes

1. **Phase 1 — 4열 벤토 메트릭 스트립**
   - 3칸 평면 통계 바를 `총 등록 원문`·`생성된 청크`·`위키 인용 연결률`·`파이프라인 상태` 4칸 벤토로 교체한다. 네 지표 모두 이미 페이지가 내려주는 `chunkStats`·`citingPages`와 로드된 소스 목록에서 산출하며, 새 조회·새 RPC·새 마이그레이션을 만들지 않는다.
2. **Phase 2 — 세그먼트 툴바 높이 통일**
   - MIME 필터 탭과 검색 인풋의 높이를 하나로 맞춰 툴바 수평선을 정렬한다. 탭의 `role="tablist"`/`aria-selected` 시맨틱은 그대로 두고 시각만 세그먼트 칩으로 맞춘다. `/` 키 검색 포커스 단축키는 신설하지 않는다.
3. **Phase 3 — 일체형 카드-로우 컨테이너**
   - 6열 `<table>`을 단일 래퍼 컨테이너 안의 5열 CSS Grid 카드-로우로 교체한다. 열은 `소스 파일`·`연결된 위키 문서`·`청크 및 좌표`·`파이프라인`·`작업`이며, 헤더 행과 데이터 행이 같은 그리드를 공유해 컬럼 축이 어긋나지 않는다.
   - 기존 `업로드` 열은 삭제하지 않고 소스 제목 아래 메타 라인으로 접는다. 상대 시각과 절대 일자를 함께 유지한다.
   - 연결된 위키 칩은 한 줄에 최대 2개 + `+N개 더` 배지로 고정해, 인용 수에 따라 행 높이가 달라지지 않게 한다.
4. **Phase 4 — 테스트와 접근성**
   - `SourcesList`·`SourceDeletion`·`source-detail-route` 테스트, typecheck, lint를 통과시킨다.

제품 API·스키마·RLS·워커는 바꾸지 않는다. 다크 모드나 `prefers-color-scheme`도 도입하지 않는다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `source-management-wiki`: 소스 라이브러리의 표시 계약을 갱신한다. MIME 필터 탭 요구사항에 툴바 정렬 조건을 더하고, 파이프라인 요약 지표와 인용 수에 무관하게 균일한 목록 행이라는 표시 계약을 추가한다.

## Impact

- `apps/dashboard/components/SourcesList.tsx` — 통계 바·툴바·테이블 마크업 교체
- `apps/dashboard/app/w/[workspaceId]/sources/page.tsx` — 조회는 그대로 두되, 벤토가 필요로 하는 집계를 props로 이미 받는지 확인하고 필요한 최소 계산만 조정
- `apps/dashboard/tests/SourcesList.test.tsx` — 업로드 일자 단언이 새 메타 라인 위치와 맞도록 갱신
- `apps/dashboard/tests/SourceDeletion.test.tsx`, `apps/dashboard/tests/source-detail-route.test.tsx` — 회귀 확인

`JobStepper`·`Dropzone`·`Pagination`은 그대로 재사용하며 이 change에서 고치지 않는다. API, 워커, 마이그레이션, RLS 정책 변경 없음. 조회는 기존 요청자 세션(`user_client`)만 사용한다.
