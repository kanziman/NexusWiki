## Why

지식 공백(`apps/dashboard/components/BacklogList.tsx`)은 홈 대시보드·위키 라이브러리·원문 소스 관리가 벤토와 카드-로우로 옮겨간 뒤에도 2칸 평면 통계 바와 5열 `<table>`에 머물러 있다. 인용 위키가 2~3편 이상인 주제에서만 행이 세로로 늘어나 목록 리듬이 깨지고, 필터 탭은 `전체 N` 하나뿐이라 **여러 문서가 동시에 인용하는 공백**을 먼저 메우려 해도 추려낼 방법이 없다. 이 화면의 목적이 "무엇부터 메울지 고르는 것"인데 정작 우선순위 신호가 목록 안에 묻혀 있다.

근거: `docs/design-systems/backlog-redesign-plan.md` §1.

## What Changes

1. **Phase 1 — 4열 벤토 메트릭 스트립**
   - 2칸 평면 통계 바를 `미해결 레드링크`·`영향받는 위키`·`최다 인용 공백`·`가장 오래 대기 중` 4칸 벤토로 교체한다. 네 지표 모두 이미 내려오는 `initialItems`(`impact`·`first_detected_at`·`referencing_pages`)에서 산출하며, 새 조회·새 RPC·새 마이그레이션을 만들지 않는다.
   - ⚠️ 계획서 §2의 4번 칸 `자동 해결 준비도`는 값이 항상 `대기 중 / 소스 추가 시 즉시 컴파일`인 고정 안내문이라 채택하지 않는다. 데이터에서 나오지 않는 칸은 지표가 아니라 장식이다. 대신 어느 공백이 가장 오래 방치됐는지를 보여 준다.
2. **Phase 2 — 다중/단일 인용 세그먼트 필터**
   - 필터를 `전체 N`·`다중 인용 N`(`impact >= 2`)·`단일 인용 N`(`impact == 1`) 세 갈래로 늘리고, 탭과 검색 인풋의 높이를 맞춰 툴바 수평선을 정렬한다. 검색과 필터는 함께 걸린다.
3. **Phase 3 — 일체형 카드-로우 컨테이너**
   - 5열 `<table>`을 단일 래퍼 컨테이너 안의 5열 CSS Grid로 교체한다. 열은 `백로그 주제`·`인용 중인 위키`·`인용 빈도`·`최초 감지`·`해결 액션`이며, 헤더 행과 데이터 행이 같은 그리드를 공유한다.
   - 인용 위키 칩은 한 줄에 최대 2개 + `+N개 더` 배지로 고정해, 인용 수에 따라 행 높이가 달라지지 않게 한다.
   - **`<table>`을 버리되 표 시맨틱은 버리지 않는다.** 인용 빈도는 이 화면의 정렬 축이므로 행·열 관계가 보조기술에 남아야 한다. 그리드에 `role="table"`/`row`/`columnheader`/`cell`을 얹는다.
4. **Phase 4 — 집계 조회 실패를 빈 결과와 구분**
   - `backlog/page.tsx`가 `wiki_links`·`wiki_pages` 조회의 `error`를 검사해 실패 사실을 내려보내고, 실패한 집계에 의존하는 벤토 칸과 빈 상태가 `모든 위키 링크가 정상적으로 연결되어 있습니다` 같은 단정 대신 불러오지 못했음을 말하게 한다.
5. **Phase 5 — 테스트와 접근성**
   - `BacklogList`·`backlog-page-route` 테스트, typecheck, lint를 통과시킨다.

**정본 어휘는 그대로 둔다.** 계획서 §4는 `aria-label="백로그 필터"`·`"백로그 검색"`을 보존 계약으로 적었지만, 이는 아카이브된 `2026-09-02-backlog-vocabulary-unification`이 이 목적지의 정본 명칭으로 고정한 **`지식 공백`**과 충돌한다. 계획서가 아니라 스펙을 따른다 — 기존 `지식 공백` 표기와 접근 가능한 이름을 유지한다.

제품 API·스키마·RLS·워커는 바꾸지 않는다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `backlog-ask`: 지식 공백 목록의 표시 계약을 갱신한다. `Consistent backlog document hierarchy`에 인용 빈도 필터·툴바 정렬·인용 수에 무관한 균일 행·표 시맨틱 보존 조건을 더하고, 우선순위 요약 지표와 집계 조회 실패 시 단정 금지 계약을 추가한다.

## Impact

- `apps/dashboard/components/BacklogList.tsx` — 통계 바·툴바·테이블 마크업 교체, 필터 추가
- `apps/dashboard/app/w/[workspaceId]/backlog/page.tsx` — 조회 경로는 그대로 두고 `error` 검사만 추가
- `apps/dashboard/tests/BacklogList.test.tsx` — 필터·벤토·균일 행 단언 추가. `getByRole("table")`·`getAllByRole("row")` 단언은 ARIA 역할을 유지하므로 그대로 통과해야 한다
- `apps/dashboard/tests/backlog-page-route.test.tsx` — 회귀 확인
- `docs/design-systems/v2/nexuswiki-design-system.css` — `sources-redesign`이 남긴 `.content.sources` 사용처 주석 중 `BacklogList` 관련 항목을 실제 상태에 맞게 갱신

`BacklogDetailModal`·`RedLinkCta`·`Pagination`은 그대로 재사용하며 이 change에서 고치지 않는다. API, 워커, 마이그레이션, RLS 정책 변경 없음. 조회는 기존 요청자 세션(`user_client`)만 사용한다.
