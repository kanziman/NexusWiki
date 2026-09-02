## Context

동기는 [`proposal.md`](proposal.md)의 Why를, 표시 계약은 [`specs/wiki-library-navigation/spec.md`](specs/wiki-library-navigation/spec.md)를 따른다. 근거 계획서는 `docs/design-systems/wiki-library-redesign-plan.md`다.

현재 라이브러리 `h1`은 `"위키"`이고, 통계는 전체 문서 수와 검증 수 두 칸이다. 카테고리 칩에는 개수가 없고, `entities` 라벨은 `WikiLibrary.tsx`에서 `"항목"`이며 홈 `KnowledgeGrid.tsx`의 `CATEGORY_LABELS`는 `"엔티티"`다. 발췌는 `cleanExcerpt`가 160자로 자르지만 가로 폭을 제한하지 않는다. 위키 인덱스 라우트는 `sources`를 읽지 않으므로 행에 인용 수를 그릴 데이터가 없다. 일괄 선택 바는 목록 위에 인라인으로 끼어들며, `data-testid="bulk-action-bar"`는 선택이 있을 때만 붙는다.

검증 라벨과 색 판정은 `lib/verification-label.ts`의 `isVerified`·`verificationLabel`이 소유한다. 삭제 버튼은 `isOwner`, 일괄 검증·발행은 `canVerify`다.

## Goals / Non-Goals

**Goals:**

- 라이브러리 헤더·필터·행·일괄 선택 표면을 계획서 Phase 1~4의 읽기 경험으로 맞춘다.
- 기존 테스트 셀렉터와 권한 게이트, 검증 라벨 원장을 유지한다.
- 인용 수는 `wiki_pages.sources` 배열 길이로 표시한다.

**Non-Goals:**

- 위키 상세 리더, 목차, 관련 문서 그리드를 이 change에서 바꾸지 않는다.
- `/` 키 검색 포커스 단축키를 신설하지 않는다.
- 위키 직접 작성·초안 생성 UI를 추가하지 않는다.
- 홈 대시보드의 `AskHero`·`h1` 테스트를 이 change에서 고치지 않는다. 그 단언은 `workspace-home-redesign` 범위다.
- API, 워커, 마이그레이션, RLS를 바꾸지 않는다.
- 다크 모드, `prefers-color-scheme`, Tailwind `dark:` 변형을 도입하지 않는다.

## Decisions

### D-1. 이 앱은 단일 테마다

토큰은 `docs/design-systems/v2/nexuswiki-design-system.css`의 `:root`에 있는 것만 쓴다. hex를 새로 도입하지 않는다. 계획서 콘셉트 코드의 `text-emerald-600`, `hover:text-red-500`, `hover:bg-red-50`는 구현에서 `--good`·`--danger` 등 v2 토큰으로 치환한다.

### D-2. 검증 카피와 권한 게이트는 기존 원장을 따른다

검증 라벨은 `lib/verification-label.ts`가 계속 판정한다. 일괄 검증·발행 노출은 `canVerify`, 삭제는 `isOwner`다. 테스트가 검증하는 `data-od-id="wiki-library-header"`, `data-od-id="wiki-library-list"`, `data-testid="select-all-checkbox"`, `data-testid="bulk-verify-btn"`, `data-testid="bulk-publish-btn"`는 유지한다. 플로팅 바로 옮겨도 이 식별자는 같은 컨트롤에 남긴다.

### D-3. 인용 수는 인덱스 조회에 `sources`를 추가해 계산한다

`apps/dashboard/app/w/[workspaceId]/wiki/page.tsx`의 `pageColumns`에 `sources`를 넣고, 라이브러리 행은 배열 길이를 인용 수로 보여 준다. 조회수 컬럼은 스키마에 없으므로 쓰지 않는다. 새 RPC를 만들지 않으며 요청자 세션만 사용한다.

### D-4. 카테고리 라벨은 홈 지식 그리드와 같게 맞춘다

라이브러리의 `entities` 라벨 `"항목"`을 `KnowledgeGrid.tsx`의 `"엔티티"`로 맞춘다. `concepts`·`guides`·`maps`는 이미 같다. 필터 칩과 행 메타가 서로 다른 한국어를 쓰지 않게 한다.

### D-5. 전체 선택 바와 플로팅 액션 바를 분리한다

현재 페이지 전체 선택 체크박스는 툴바와 카드 리스트 사이의 서브 컨트롤 바에 남긴다. 일괄 검증·발행·선택 해제는 1개 이상 선택됐을 때만 하단 중앙 플로팅 바가 담당한다. 인라인 바가 목록을 밀어내던 동작을 없애기 위해서다.

### D-6. 검색 단축키는 추가하지 않는다

검색 인풋의 지우기 버튼과 기존 디바운스 필터는 유지한다. `/` 키로 검색을 포커스하는 동작은 신설하지 않는다.

## Risks / Trade-offs

- [Risk] `WikiLibrary.test.tsx`가 빈 상태에서 `h1` 이름을 `"위키"`로 단언한다. → 타이틀을 `위키 라이브러리`로 바꾸는 Phase 1과 같은 슬라이스에서 단언을 고친다.
- [Risk] 카테고리 라벨 `"항목"` → `"엔티티"`가 칩 접근 가능한 이름을 바꾼다. → 필터 테스트가 라벨 문자열에 의존하면 함께 갱신한다.
- [Risk] `sources`를 인덱스 조회에 추가하면 즐겨찾기 필터 경로의 select 문자열도 같이 바뀐다. → `pageColumns` 한곳에서만 조립해 두 분기가 어긋나지 않게 한다.
- [Risk] 플로팅 바가 좁은 화면에서 페이지네이션이나 하단 셸을 가릴 수 있다. → 하단 여백을 두고 키보드로 일괄 버튼에 도달할 수 있는지 Phase 5에서 확인한다.

## Migration Plan

1. 위키 인덱스 조회와 `WikiLibrary` UI를 함께 배포한다. 데이터베이스 마이그레이션은 없다.
2. `WikiLibrary`·`WikiBulkActions` 테스트와 typecheck·lint·strict validation으로 회귀를 확인한다.
3. 문제가 있으면 이 change의 UI 커밋만 되돌린다. 일괄 검증·발행 API 계약은 바꾸지 않으므로 데이터 롤백은 필요 없다.
