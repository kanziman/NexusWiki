## Context

동기는 [`proposal.md`](proposal.md)의 Why를, 표시 계약은 [`specs/backlog-ask/spec.md`](specs/backlog-ask/spec.md)를 따른다. 근거 계획서는 `docs/design-systems/backlog-redesign-plan.md`다.

현재 상태 중 설계를 제약하는 것들:

- `apps/dashboard/app/w/[workspaceId]/backlog/page.tsx`는 이미 주제별로 `impact`·`first_detected_at`·`referencing_pages`를 집계해 `BacklogList`에 내려준다. 벤토 네 지표는 전부 이 배열에서 나온다 — 새 조회가 필요 없다.
- 같은 파일이 `linksData ?? []`·`pagesData ?? []`로 error를 흘려보낸다. 지금은 조회가 실패해도 화면이 `모든 위키 링크가 정상적으로 연결되어 있습니다`라고 단정한다. 이 화면에서는 특히 나쁘다 — "메울 공백이 없다"는 안심시키는 거짓말이기 때문이다.
- ⚠️ **`BacklogList.test.tsx`는 `getByRole("table")`(:77)과 `getAllByRole("row")`(:84)에 의존한다.** 앞선 `sources-redesign`은 이 의존이 없어 그냥 `<div>` 그리드로 갔지만 여기서는 다르다. 테스트 주석이 "인용 빈도는 배지가 아니라 표의 정렬 축 열이다"라고 이유까지 적어 뒀다.
- 정본 어휘는 `지식 공백`이다. 테스트가 `heading name:"지식 공백"`·`region name:"지식 공백 요약"`·`textbox name:"지식 공백 검색"`을 단언한다.
- `.doc-chip`(인용 위키 칩)은 v2에 이미 있고 소스 화면과 공유한다. `.field.search`는 높이 36px 고정이며 소스·위키 라이브러리와 공유한다.
- 이 라우트에는 `loading.tsx`가 없다. 홈·위키·소스와 달리 스켈레톤 자체가 존재하지 않는다.

## Goals / Non-Goals

**Goals:**

- 벤토·툴바·목록을 앞선 세 화면이 세운 관용구로 맞춘다.
- 인용 빈도로 우선순위를 고를 수 있게 한다 — 이 화면의 존재 이유다.
- 표 시맨틱과 기존 테스트 계약을 모두 보존한다.
- 조회 실패가 "공백 없음"으로 둔갑하지 않게 한다.

**Non-Goals:**

- `BacklogDetailModal`(발췌 모달) 내부는 바꾸지 않는다.
- `backlog/loading.tsx`를 **신설하지 않는다.** 지금 없으므로 이 change가 만든 불일치가 아니다. 스켈레톤 신설은 그 자체로 별도 결정이며, 세 화면의 스켈레톤과 나란히 다룰 change에서 한다.
- `/` 키 검색 포커스 단축키를 신설하지 않는다(계획서 §2에 있으나 앞선 두 change에서 이미 배제한 결정을 뒤집지 않는다).
- 정렬 순서(인용 빈도 내림차순)를 사용자가 바꾸는 기능을 넣지 않는다.
- API·워커·마이그레이션·RLS를 바꾸지 않는다. 다크 모드도 도입하지 않는다.

## Decisions

### D-1. `<table>`을 버리되 ARIA 표 역할은 얹는다

`sources-redesign`은 `<table>` → `<div>` 그리드로 가면서 표 시맨틱을 그냥 놓았다. 소스 목록은 셀 단위로 비교하는 표가 아니라 카드 행이었고, 테스트도 table role에 의존하지 않았기 때문이다.

여기서는 반대다. **인용 빈도가 정렬 축**이고, 사용자는 "3회 인용 vs 1회 인용"을 열 단위로 비교해서 무엇부터 메울지 고른다. 시맨틱을 놓으면 스크린리더 사용자에게서 이 화면의 핵심 기능이 사라진다. 테스트가 이미 그 이유를 주석으로 적어 둔 것도 같은 판단이다.

따라서 CSS Grid 컨테이너에 `role="table"`, 헤더 행에 `role="row"` + 각 헤더 셀에 `role="columnheader"`, 데이터 행에 `role="row"` + 각 값에 `role="cell"`을 얹는다. 기존 `getByRole("table")`·`getAllByRole("row")` 단언이 그대로 통과한다 — 테스트를 고치지 않아도 되는 것이 이 선택이 옳다는 신호다.

⚠️ `display: grid`는 `<table>`의 기본 role을 지우므로, `<table>` 요소를 쓰면서 CSS Grid를 얹는 방식은 오히려 role을 잃는다. 명시적 ARIA role이 필요한 이유다.

대안: 테스트에서 table/row 단언을 지운다. → 접근성 회귀를 테스트 수정으로 덮는 것이라 채택하지 않는다.

### D-2. 벤토 4번 칸은 `가장 오래 대기 중`이다

계획서 §2·§3.1의 `자동 해결 준비도`는 값이 항상 `대기 중`이고 푸터가 항상 `소스 추가 시 즉시 컴파일`이다. 데이터가 없는 칸이라 어떤 워크스페이스에서도 같은 글자를 보여 준다 — 지표 자리를 차지한 안내문이다.

대신 `first_detected_at`이 가장 이른 미해결 주제를 값(경과 시간)과 푸터(주제명)로 보여 준다. 나머지 세 칸이 "얼마나 많은가"를 말하므로, 네 번째는 "얼마나 오래 방치됐는가"라는 다른 축을 더한다. 이미 있는 데이터이고 다른 칸과 겹치지 않는다.

동률 처리: 같은 시각이 여럿이면 `impact` 내림차순, 그다음 `target_slug` 오름차순으로 하나를 고른다. 최다 인용 칸도 같은 방식으로 동률을 깬다 — 스펙이 "같은 데이터는 늘 같은 요약을 낸다"를 요구하기 때문이다.

### D-3. 필터 경계는 `impact >= 2`다

`다중 인용`은 두 개 이상의 위키가 인용하는 주제다. 여러 문서가 같은 공백을 가리킨다는 것은 그 개념이 실제로 지식 그물의 구멍이라는 뜻이라, 하나만 인용하는 주제보다 먼저 메울 값어치가 있다.

필터는 `role="tablist"`/`aria-selected`를 쓴다. 상호배타 단일 선택이고 소스 화면이 같은 시맨틱을 쓴다. 탭 이름에 개수를 실어(`전체 9`·`다중 인용 2`·`단일 인용 7`) 필터를 고르기 전에도 분포가 보이게 한다.

⚠️ 필터와 검색은 **함께** 걸린다. 한쪽이 다른 쪽을 리셋하면 "다중 인용 중에서 캐시 관련"을 찾을 수 없다. 필터 변경과 검색어 변경 모두 페이지를 1로 되돌린다.

### D-4. 툴바 높이는 36px에 맞춘다

계획서는 38px를 말하지만 `.field.search`가 36px를 고정하고 있고 이 규칙은 소스·위키 라이브러리와 공유한다. `sources-redesign` D-2와 같은 이유로 36px로 맞춘다 — 스펙이 요구하는 것은 픽셀 값이 아니라 두 컨트롤의 정렬이다.

### D-5. 조회 실패는 빈 상태와 다르게 말한다

`page.tsx`가 `linksData`·`pagesData`의 error를 검사해 boolean으로 내려보내고, `BacklogList`는 실패 시 `EMPTY_HEADING`/`EMPTY_BODY` 대신 불러오지 못했음을 표시한다. `sources-redesign`이 세운 방식과 소스 상세 라우트의 선례를 그대로 따른다.

`EMPTY_HEADING`("작성 대기 중인 백로그가 없습니다")과 `EMPTY_BODY`("모든 위키 링크가 정상적으로 연결되어 있습니다") 문구 자체는 바꾸지 않는다 — 승인된 카피이고, 실패 시에는 아예 다른 문구를 쓴다.

### D-6. 헤더와 행은 하나의 `grid-template-columns` 값을 공유한다

`sources-redesign` D-5와 같다. 컨테이너에 CSS 변수로 컬럼 정의를 한 번만 쓰고 헤더·데이터 행이 함께 참조해, 한쪽만 고쳐 축이 어긋나는 상태를 구조적으로 막는다.

### D-7. 시각은 Tailwind 유틸리티 + v2 토큰으로 쓴다

`sources-redesign` D-1과 같다. 계획서가 제안한 `.metrics-grid`·`.backlog-table-container` 같은 새 클래스는 만들지 않는다. 이미 있고 이 용도인 `.doc-chip`은 재사용한다.

이 change 이후 `.table`·`.table-wrap`·`.doc-chips`·`.stats`의 사용처가 또 줄어들므로, `sources-redesign`이 v2 CSS에 남긴 사용처 현황 주석을 실제 상태에 맞게 갱신한다. 규칙 자체는 여전히 `PreviewWorkspace`가 쓰므로 지우지 않는다.

## Risks / Trade-offs

- [Risk] ARIA role을 손으로 얹으면 `<table>`이 공짜로 주던 것(캡션, 헤더-셀 연관)을 빠뜨리기 쉽다. → 헤더 셀에 `role="columnheader"`를 붙이고, 행 안의 값이 라벨 없는 숫자로만 남지 않게 한다(`3회`처럼 단위를 텍스트로 함께 둔다). Phase 5에서 기존 role 단언이 통과하는지 확인한다.
- [Risk] 68px 고정 행 높이는 긴 한국어 주제명과 슬러그 두 줄을 압박한다. → 주제명에 `title` 속성을 유지하고 말줄임을 쓴다. 슬러그는 이미 mono 10.5px로 작다.
- [Risk] 필터 추가로 `전체 N` 하나만 있던 `role="tab"` 개수가 3개가 된다. 기존 테스트가 단일 탭을 전제하면 깨진다. → Phase 5에서 확인하고, 깨지면 필터 도입과 같은 슬라이스에서 고친다.
- [Risk] `가장 오래 대기 중` 칸이 `impact`가 낮은 주제를 최상단 요약에 올려, 인용 빈도 정렬과 다른 우선순위를 암시할 수 있다. → 값을 "대기 시간"으로 명시하고 최다 인용 칸을 그 옆에 둔다. 두 축을 나란히 보여 주는 것이 목적이지 하나를 권하는 것이 아니다.
- [Trade-off] `sources-redesign`(PR #122)이 아직 머지되지 않은 상태에서 그 브랜치 위에 쌓는다. → v2 CSS 주석과 `.table-wrap` 사용처가 두 change에서 겹치므로 순차 처리가 충돌이 없다. 대신 이 PR은 #122가 머지될 때까지 대기한다.

## Migration Plan

1. `BacklogList` UI와 `backlog/page.tsx`의 error 검사를 함께 배포한다. 데이터베이스 마이그레이션도 API 변경도 없다.
2. `pnpm --dir apps/dashboard test`(`BacklogList`·`backlog-page-route` 포함)·`typecheck`·`lint`·`openspec validate backlog-redesign --strict`로 회귀를 확인한다.
3. 문제가 있으면 이 change의 UI 커밋만 되돌린다. 조회 계약을 바꾸지 않으므로 데이터 롤백은 필요 없다.
