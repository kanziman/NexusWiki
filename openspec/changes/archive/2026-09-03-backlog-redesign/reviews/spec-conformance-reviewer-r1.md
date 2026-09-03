# Spec Conformance 리뷰 — backlog-redesign r1

- 판정: pass
- 대상: working tree diff (`git diff`), 브랜치 `feat/backlog-redesign` (HEAD `1ef411f`, 아직 커밋 전)
  - `apps/dashboard/components/BacklogList.tsx`
  - `apps/dashboard/app/w/[workspaceId]/backlog/page.tsx`
  - `apps/dashboard/tests/BacklogList.test.tsx`
  - `apps/dashboard/tests/backlog-page-route.test.tsx`
  - `docs/design-systems/v2/nexuswiki-design-system.css`
- 일시: 2026-09-03T10:04:50Z

## 검증 명령 실행 결과

- `pnpm --dir apps/dashboard exec vitest run tests/BacklogList.test.tsx tests/backlog-page-route.test.tsx --reporter=verbose` → **31 passed (31)**
- `pnpm --dir apps/dashboard exec tsc --noEmit -p .` → **No errors found**
- `pnpm --dir apps/dashboard exec eslint components/BacklogList.tsx "app/w/[workspaceId]/backlog/page.tsx"` → **No issues found**
- `openspec validate backlog-redesign --strict` → **valid**

## 시나리오 판정

### MODIFIED — Consistent backlog document hierarchy (7개)

| Scenario | 결과 | 증거 |
| --- | --- | --- |
| Member scans and filters backlog topics | 충족 | 검색은 `display_title`·`target_slug`·`referencing_pages[].title` 세 필드를 모두 훑는다 — `BacklogList.tsx:86-93`. 제목·슬러그 매칭은 `tests/BacklogList.test.tsx:107-153`("filters backlog items based on search input")로 검증됨. ⚠️ **인용 위키 제목으로 검색되는 경로(`matchesPage`, `BacklogList.tsx:90-92`)를 직접 때리는 테스트는 없다** — 다만 이 매칭 로직은 이번 change가 새로 만든 게 아니라 정본 스펙에 이미 있던 동작을 그대로 옮긴 것이라 이번 diff가 만든 회귀는 아니다(아래 「조치가 필요한 항목」 참고). |
| Member operates a backlog row | 충족 | 주제 버튼(`BacklogList.tsx:374-389`)·인용 위키 링크(`402-411`)·소스 추가 링크(`450-458`)가 같은 `role="row"` 안에서 서로 중첩되지 않은 형제 요소로 존재한다 — 인터랙티브 요소가 중첩되지 않으므로 구조적으로 한쪽 클릭이 다른 쪽을 발화시키지 않는다. 상세 패널 오픈은 `tests/BacklogList.test.tsx:457-485`로, 소스 추가 링크의 독립된 href는 `tests/BacklogList.test.tsx:98-104`·`400-408`로 검증됨. 클릭 격리 자체를 명시적으로 때리는 테스트(예: 칩 클릭 시 모달이 열리지 않음을 확인)는 없지만, 비중첩 마크업이라는 구조적 보장으로 충분하다고 판단. |
| Member separates multi-cited gaps from single-cited ones | 충족 | 필터 로직 `BacklogList.tsx:73-80,83-85` (`impact >= 2`/`=== 1`), 탭 이름에 개수 포함. 테스트 `tests/BacklogList.test.tsx:281-309`("다중 인용 필터...", "단일 인용 필터...") 통과 확인. |
| Member combines a filter with a search query | 충족 | `BacklogList.tsx:83-94`에서 필터와 검색이 같은 `filter()` 체인에서 함께 적용됨. 테스트 `tests/BacklogList.test.tsx:311-328` 통과 확인. |
| Member views a topic cited by many wiki pages | 충족 | 칩 2개 상한 + 잔여 표시 `BacklogList.tsx:362-364,401-417`. 행 높이는 `md:h-[68px]`로 고정(`BacklogList.tsx:370`) — 인용 수와 무관. 테스트 `tests/BacklogList.test.tsx:331-354`("인용 위키가 많아도 칩 2개와 잔여 개수만 렌더한다") 통과 확인. jsdom은 실제 computed height를 검증하지 못하므로 "행 높이가 같다"는 부분은 고정 클래스 존재로 코드 검토에 근거함(자동화 한계, 새로 발생한 문제 아님). |
| Assistive technology user reads the citation-frequency column / 표 시맨틱 보존 | 충족(아래 판정1 참고) | `role="table"`(`BacklogList.tsx:337`), 헤더 `role="row"`+`role="columnheader"`(`344-358`), 데이터 `role="row"`+`role="cell"`(`367-459`). 인용 빈도 셀에 `회` 단위 텍스트 병기(`427-434`)로 라벨 없는 숫자만 남기지 않음. |
| Member opens the backlog on a narrow viewport | 충족(코드 검토, 자동화 테스트 없음) | 헤더는 `hidden md:grid`(`BacklogList.tsx:346`), 데이터 행은 `grid-cols-1 md:[grid-template-columns:...]`(`370`)로 좁은 뷰포트에서 1열 스택으로 전환되고, 컬럼 정의가 `minmax(0, …)`(`53-54`)라 콘텐츠가 트랙을 밀어내지 않는다 — 페이지 가로 스크롤을 구조적으로 막는다. jsdom 기반 단위 테스트로는 실제 리플로우를 검증할 수 없고, 이 코드베이스의 자매 change(`sources-redesign`)도 같은 이유로 뷰포트 전용 테스트가 없다(`grep`으로 `SourcesList.test.tsx`에 0건 확인) — 이번 change가 새로 만든 공백이 아니다. |

### ADDED — Backlog prioritization summary (3개)

| Scenario | 결과 | 증거 |
| --- | --- | --- |
| Member opens a backlog holding unresolved topics | 충족 | 네 지표 산출: 미해결 수(`items.length`, `165`), 영향받는 위키(`distinctReferringPages`, `101-103,189`), 최다 인용(`mostCited`, `107-114`), 최장 대기(`longestWaiting`, `118-127`) — 모두 같은 `items` prop에서 파생. 테스트 `tests/BacklogList.test.tsx:193-218` 통과. |
| Several topics tie for most cited | 충족(판정3 참고) | `mostCited` 정렬 `impact` 내림차순 → `target_slug` 오름차순(`109-113`)으로 결정적. 테스트 `tests/BacklogList.test.tsx:220-245` 통과. |
| Backlog is empty | 충족 | `!loadFailed && items.length > 0 && ...` 가드(`145`)로 벤토 자체를 렌더하지 않음. 테스트 `tests/BacklogList.test.tsx:247-253`(벤토 부재) + `tests/BacklogList.test.tsx:17-26`(빈 상태 문구 노출, 같은 `initialItems={[]}` 조건)로 두 단언이 합쳐져 시나리오 전체를 충족. |

### ADDED — Backlog aggregate load failure is distinguishable from an empty backlog (2개)

| Scenario | 결과 | 증거 |
| --- | --- | --- |
| The backlog query fails | 충족 | `page.tsx:67-91`에서 `linksError`/`pagesError`를 검사해 `loadFailed`를 계산하고 `console.error`로 실패를 기록, `linksData ?? []`로 흘려보내지 않음(에러가 있어도 `items`는 `[]`가 되지만 `loadFailed=true`로 구분됨). `BacklogList.tsx:250-261`가 `LOAD_FAILED_HEADING`/`BODY`를 렌더하고 `EMPTY_HEADING`/`EMPTY_BODY`는 렌더 경로에서 배제됨(`loadFailed ? ... : ...` 분기, `250`). 테스트: `tests/backlog-page-route.test.tsx:151-179`(linksError·pagesError 각각), `tests/BacklogList.test.tsx:356-370`(빈 상태 문구 부재까지 확인). |
| The backlog is genuinely empty | 충족 | `loadFailed=false`이고 `items=[]`일 때 `EMPTY_HEADING`/`EMPTY_BODY` 그대로 노출(`BacklogList.tsx:316-328`, 조건 `items.length === 0`). 테스트 `tests/backlog-page-route.test.tsx:139-149`(`loadFailed`가 `false`) + `tests/BacklogList.test.tsx:17-26`(문구 노출) 통과. |

## 확인 요청 사항 회신

**1. `role="table"` 등 수동 ARIA가 실제로 표 구조를 노출하는가, 기존 `getByRole("table")`·`getAllByRole("row")` 단언이 수정 없이 통과하는가**

- 실제로 `pnpm --dir apps/dashboard exec vitest run tests/BacklogList.test.tsx tests/backlog-page-route.test.tsx --reporter=verbose`를 새로 돌려 31개 테스트 전건 통과를 확인했다. `getByRole("table")`(`BacklogList.test.tsx:84,147,287,301,320,349,398,428,605`)·`getAllByRole("row")`(`91`) 모두 수정 없이 통과한다. 이는 `@testing-library/dom`의 role 쿼리가 명시적 `role` 속성을 DOM 트리 전체에서 매칭할 뿐 ARIA "required owned elements" 구조 유효성(부모-자식 관계)을 검사하지 않기 때문이다 — 즉 unit test 통과는 이 판정에서 필요조건이지 충분조건이 아니다.
- 실제 보조기술 노출 여부는 별도로 봐야 한다. 구조는 `div[role=table] > div[role=row](헤더) + div.divide-y(role 없음) > div[role=row](데이터 행) > div[role=cell]`이다(`BacklogList.tsx:336-464`). 데이터 행이 `role="table"`의 **직접 자식이 아니라** `role` 없는 래퍼(`divide-y` div, `360`) 아래 있다는 점이 유일한 구조적 위험이다. WAI-ARIA의 "owned by" 관계는 직접 DOM 자식일 필요는 없고, 명시적으로 다른 구조 role을 가진 요소가 중간에 끼지만 않으면 된다 — 여기 끼어 있는 것은 `role` 속성이 없는 순수 `<div>`(암묵적 role `generic`)이므로 주요 브라우저(Chromium/Firefox 기반 AT 매핑)에서는 이런 "투명한" 컨테이너를 관통해 테이블 구조를 계산하는 것이 일반적인 동작이다. 이 패턴은 `<table>` 없이 CSS Grid에 ARIA table role을 얹는 널리 쓰이는 관용구(WAI-ARIA APG의 grid-as-table 패턴)와 일치한다.
- 다만 이 저장소에는 선례가 없다(`grep -rn 'role="table"'` 결과 `BacklogList.tsx`가 유일). NVDA/VoiceOver 등 실제 스크린리더로 수동 검증하거나 axe 계열 자동 검사를 추가하는 것이 안전하지만, 이 change의 검증 계획(`design.md` Migration Plan)에도 axe 검증은 없고 자매 change들도 마찬가지다. **코드 검토로는 스펙을 충족한다고 판단하되, 실측(스크린리더) 검증은 하지 않았다는 한계를 명시한다.**

**2. `within(table)` 스코프 축소가 커버리지를 실질적으로 줄였는가**

- 아니라고 판단한다. `git diff apps/dashboard/tests/BacklogList.test.tsx`로 diff를 대조한 결과, 스코프를 좁힌 5곳(`84-88`,`147-149`,`398`,`428`,`605-619`) 전부 **기존에 검증하던 조건(제목이 표 안에 존재)을 그대로 유지**하면서 모호성(벤토 카드와 표에 같은 텍스트가 동시에 뜨는 경우)만 제거했다. 오히려 이번 diff는 `backlog-metric-*` `data-testid`로 벤토 4칸 각각을 개별 검증하는 테스트를 5건 신설했고(`193-218`,`220-245`,`247-253`), 필터·칩 상한·조회 실패 테스트도 새로 추가했다(`281-329`,`331-354`,`356-370`). 순감소가 아니라 순증가다.
- 유일하게 짚을 부분은 위 시나리오 표에 적은 대로, "referring wiki titles"로 검색되는 경로(`matchesPage`)에 대한 전용 테스트가 없다는 점인데, 이는 이번 diff가 지운 게 아니라 애초부터(정본 스펙 단계부터) 없었던 공백이다.

**3. 최다 인용/최장 대기 동률 처리가 design.md D-2 규칙대로 결정적인가**

- 그렇다. `BacklogList.tsx:107-114`(`mostCited`)는 `b.impact - a.impact || a.target_slug.localeCompare(b.target_slug, "ko")`로 정렬해 **impact 내림차순 → slug 오름차순**을 따르고, `118-127`(`longestWaiting`)은 `first_detected_at` 오름차순 → `impact` 내림차순 → `target_slug` 오름차순으로 정렬한다. `design.md` D-2("동률 처리: 같은 시각이 여럿이면 impact 내림차순, 그다음 target_slug 오름차순...최다 인용 칸도 같은 방식으로 동률을 깬다")와 `tasks.md` 1.1의 명시적 규칙("최다 인용이면 impact 내림차순 후 target_slug 오름차순, 최장 대기면 first_detected_at 오름차순 후 같은 규칙")과 정확히 일치한다.
- 동률 테스트: `tests/BacklogList.test.tsx:220-245`("최다 인용이 동률이면 target_slug 오름차순으로 결정적으로 고른다")가 impact 동률(2건)일 때 `target_slug` 오름차순("가장-먼저-주제" < "나중-주제")으로 "가장 먼저 주제"를 고르는 것을 확인한다. 최장 대기 쪽 동률 전용 테스트는 없지만(스펙의 ADDED requirement도 "최다 인용 동률" 시나리오만 명시하고 최장 대기 동률 시나리오는 요구하지 않는다), 구현 로직은 코드 검토로 동일 규칙을 따름을 확인했다.
- `localeCompare(..., "ko")`는 Node의 ICU 빌드에 의존하는 정렬이라 극단적으로는 실행 환경마다 미세하게 다를 수 있는 리스크가 있지만, 이번 change의 스펙 범위(동일 데이터 → 동일 렌더)에서 벗어나는 문제는 아니라 판정에 영향을 주지 않는다.

## 판정 근거

MODIFIED 7개, ADDED 5개 시나리오 전부 실제 코드 경로와 통과하는 테스트로 뒷받침된다. `page.tsx` diff는 제안대로 `error` 검사만 추가했고 조회 경로(select 컬럼·필터)는 그대로다. CSS 파일 diff는 사용처 주석만 바뀌었고 규칙 변경이 없음을 `git diff`로 직접 확인했다. `vitest`·`tsc`·`eslint`·`openspec validate --strict`를 모두 새로 실행해 전건 통과를 확인했다.

미충족 시나리오는 없다. 다만 두 가지 한계를 기록해 둔다 — (1) `role="table"` 기반 표 시맨틱의 실제 보조기술 노출은 구조적 근거로 타당성을 판단했을 뿐 실측(NVDA/VoiceOver)하지 않았고, (2) 인용 위키 제목으로 검색되는 경로(`matchesPage`)에 대한 전용 테스트가 없다 — 다만 둘 다 이번 diff가 새로 만든 회귀가 아니라 기존 관용구·기존 스펙 공백을 그대로 물려받은 것이라 `needs_fix`로 내리지 않는다.
