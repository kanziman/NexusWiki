# Spec Conformance 리뷰 — dashboard-layout-density r3 (최종)

- 판정: **pass**
- 대상: `git diff` 워킹 트리 + untracked (`apps/dashboard/lib/verification-label.ts` · `apps/dashboard/tests/verification-label.test.tsx`). 브랜치 `feat/dashboard-layout-density`, `HEAD` = `747d7de` (이 change 작업은 전부 미커밋)
- 일시: 2026-08-20T23:10:24Z

## r2 지적 5건 — 종결 확인

| # | r2 지적 | 상태 | 증거 |
| --- | --- | --- | --- |
| 1 | 리더의 `disputed` 라벨이 단일 어휘 밖 | **닫힘** | `WikiPageContent.tsx:21` — `DISPUTED_CALLOUT = ${verificationLabel({ disputed: true })} — 상충하는 정보가 있습니다…`. 상태명이 모듈에서 파생된다. 세 목적지 대조: 홈 `KnowledgeGrid.tsx:123`(`verificationLabel(page)`) · 라이브러리 `WikiLibrary.tsx:38`(`const stateLabel = verificationLabel`) · 리더 `:21` → 전부 `"충돌 감지"`. 리더의 표시 우선순위도 모듈과 같다 — `WikiPageContent.tsx:169`가 `disputed`를 검증 콜아웃보다 먼저 분기하고, `lib/verification-label.ts:68`이 같은 순서다. 근거였던 "UI-SPEC Copywriting Contract"는 리포지토리에 없음을 재확인했다(`docs/` 전체 0건, 출현은 이 change의 tasks·리뷰 문서뿐) |
| 2 | proposal.md의 리듬 약속 잔존 | **닫힘** | `proposal.md:19`가 "그 이상 … **이 change의 스펙 요구사항이 아니다**"로 재작성됨. Spec Impact(`:36`)에도 `precedence`·`리듬` 잔여 문구 없음 |
| 3 | design.md가 r1 대응 이후를 미반영 | **닫힘(부수 1건 잔존)** | Decision 3 제목이 "7개 중 1개"로, 표에 앱 홈 추가(`design.md:56,70`). Decision 4 표에 `.metric small`·`.share-state` 편입(`:85,87`). Decision 5가 "이번 change의 스펙 요구사항이 아니다"로 재작성(`:97-105`). ⚠️ `design.md:8`의 "`.content`는 **6개** 목적지가 공유"는 여전히 5개다(실사용: 홈 · 소스 · 라이브러리 · 백로그 · 설정) |
| 4 | topbar 테스트가 `<a>`만 커버 | **닫힘** | `tests/WorkspaceShell.test.tsx:163-170`이 `.top-actions a, .top-actions > button`을 쿼리하고 계정 메뉴·`aria-label` 보유 요소(모바일 내비, `WorkspaceShell.tsx:101-109`)를 걸러낸 뒤 `["소스 추가","질문 시작"]` 정확 일치를 단언한다 |
| 5 | 예외 열거가 닫힌 목록(`specifically`) | **닫힘** | 델타 `specs/dashboard-design-consistency/spec.md:4` — `"… is exempt from that shared width … — for example the Ask workspace … and the document reader"`. 열거가 예시로 완화돼 원문 소스 상세(`sources/[id]/page.tsx:52`, Tailwind `max-w-4xl`)가 사실과 어긋나지 않는다 |

## 시나리오 판정

### Requirement: Consistent workspace page structure

| Scenario | 결과 | 증거 |
| --- | --- | --- |
| Member moves between workspace destinations | 충족 | 네 목적지 모두 제목·콘텐츠 프레임 유지 — 홈 `app/w/[workspaceId]/page.tsx:103-110`, 소스 `SourcesList.tsx:140-148`, Ask `AskConversation.tsx:290-296`, 설정 `settings/page.tsx:57-63`. 포커스 처리 미변경. 테스트 241건 통과 |
| Member switches content viewer tabs within Ask | 충족 | 이 change가 손대지 않은 기존 구현 — `ContentViewer.tsx:99-130`(`role="tablist"`·`tab`·`aria-selected`·`tabpanel`) |
| Member compares shared-canvas destinations on a wide viewport | 충족 | `.content` 폭 선언이 CSS 전체에서 하나다 — `nexuswiki-design-system.css:750`(`width: min(1280px, 100%)`). `.content.*` 규칙에 남은 `width`는 없다(`:1080` settings · `:1584` sources · `:2482` backlog · `:2736` library 모두 `padding`만; 전수 grep에서 잔여 폭 선언 0건). 공유 캔버스 사용처는 정확히 5곳(`page.tsx:103` · `SourcesList.tsx:140` · `WikiLibrary.tsx:87` · `BacklogList.tsx:79` · `settings/page.tsx:57`) |
| Member opens a destination that owns its layout | 충족 | Ask `.ask-layout`(3열 그리드, 사용자가 리사이즈 바로 경계 조절 — UX-05) · 리더 `.reader { width: min(820px,100%) }`. 이 change가 건드리지 않았고 스펙이 예외로 명시 |
| Member scans destinations for repeated decorative context | 충족 | `className="eyebrow"` 사용처가 앱 전체 0건(남은 `eyebrow` 문자열은 전부 제거 사유 주석). 프리뷰도 0건 — `PreviewWorkspace.tsx:675`의 `PageHero`가 `eyebrow` prop 자체를 잃었다. 유일한 맥락 라벨인 브레드크럼은 내부 리더(`WikiPageContent.tsx:143`)와 공개 리더(`app/p/[slug]/[page]/page.tsx:99`)가 같은 `.breadcrumb-path`(CSS `:496`)를 쓴다 |

### Requirement: Shared state and control language

| Scenario | 결과 | 증거 |
| --- | --- | --- |
| Member encounters a non-default state | 충족 | 색이 아니라 텍스트로 상태를 말한다 — `WikiPageContent.tsx:359`(`검증됨 · 날짜`) · `:371`(`검증 만료됨 · … 재검증 필요`) · `:384`(`부분 검증 · 재검증이 필요합니다`), `OperationsPanel.tsx:225-238`. 홈의 충돌·만료 배지도 색 없는 `.badge` + 텍스트(`KnowledgeGrid.tsx:122`) |
| Member sees the same underlying status on two destinations | 충족 | 단일 출처 `lib/verification-label.ts:64-74`. 홈 `KnowledgeGrid.tsx:91,103,123`, 라이브러리 `WikiLibrary.tsx:38,165`. 테스트가 두 컴포넌트를 **실제로 렌더**해 같은 `data-od-id` 항목 텍스트를 비교한다 — `tests/verification-label.test.tsx:32`(verified) · `:62`(disputed) · `:127`(만료) |

**요구사항 본문 조항**

- *"A given underlying status value SHALL be presented with the same label wherever it appears…"* — **충족**. 상태값별 목적지 대조:

  | 상태 | 홈 | 라이브러리 | 리더 |
  | --- | --- | --- | --- |
  | verified(유효) | "검증됨" (`KnowledgeGrid.tsx:123`) | "검증됨" (`WikiLibrary.tsx:165`) | "검증됨 · 날짜" (`WikiPageContent.tsx:359`) |
  | verified+만료 | "검증 만료됨" (`:123`, `.verified` 클래스 없음) | "검증 만료됨" (`:165`) | "검증 만료됨 · … 재검증 필요" (`:371`) |
  | disputed(boolean) | "충돌 감지" | "충돌 감지" | "충돌 감지 — …" (`:21`) |
  | partial | 배지 없음 | "부분 검증" | "부분 검증 · 재검증이 필요합니다" (`:384`) |

  r2까지 남아 있던 마지막 두 간극(리더 `disputed`, 목록의 만료 미인지)이 모두 닫혔다. 프리뷰도 같은 어휘를 파생한다(`PreviewWorkspace.tsx:555,557`).
  (공개 위키 `/p/`의 `"검증 및 승인됨"`(`app/p/[slug]/[page]/page.tsx:108`)은 `wiki_page_publications`의 **발행 승인** 상태이지 `verification_status` 표시가 아니고, anon 표면이라 workspace destination도 아니다 — r1·r2와 같이 판정 대상에서 제외한다.)
- *"Status text SHALL be rendered at a size that remains legible…"* — **충족**. r2에서 상향된 `.metric small` 12px(CSS `:1338`) · `.share-state` 12px(`:1411`)가 그대로이고, r3 변경분은 CSS를 건드리지 않았다(diff에 새 폰트 크기 선언 없음)

### Requirement: Constrained global knowledge actions (ADDED)

| Scenario | 결과 | 증거 |
| --- | --- | --- |
| Member views the global action bar | 충족 | `WorkspaceShell.tsx:80-110` — `.top-actions`의 지식 행동은 소스 추가(`:85-92`)·질문 시작(`:93-99`) 둘뿐. 회귀 테스트가 `<a>`와 `<button>`을 함께 센다(`tests/WorkspaceShell.test.tsx:163-172`) |
| A destination needs its own action | 충족 | 목적지 고유 행동은 각자의 콘텐츠 프레임 안(소스 Dropzone · 리더 검증 액션 `WikiPageContent.tsx:187` 이하 · 설정 초대). topbar에 추가된 것 없음 |

## r3 신규 변경 판정 — 아직 리뷰된 적 없는 항목

### 6. `expires_at` 편입 (8.1)

**범위 안이며, 없으면 요구사항이 실제로 깨졌다.** 편입 전 상태는 이랬다: 리더는 `expires_at`을 읽어 `"검증 만료됨"`을 띄우는데(`WikiPageContent.tsx:124-125,364-373`, 이 change 이전부터), 홈·라이브러리는 `verification_status === "verified"`만 보고 같은 문서를 `"검증됨"`이라 불렀다. 이는 *"one state is never named differently on two destinations"* 의 정면 위반이며, `0007_search_and_queue_extensions.sql:260`이 *"검증의 유효 기한. 지나면 verification_status를 그대로 신뢰하지 않는다"* 로 이미 금지해 둔 상태이기도 하다.

- 모듈: `lib/verification-label.ts:69-71`(verified ∧ 만료 → `"검증 만료됨"`) · `:83-92`(`isVerified`가 만료 제외) · `:98-107`(`isExpiredVerification` 신설). 파싱 불가 값을 만료로 단정하지 않는 가드(`:49-55`)까지 명시적이다
- 조회·타입: 홈 `app/w/[workspaceId]/page.tsx:53,72` · 라이브러리 `app/w/[workspaceId]/wiki/page.tsx:34` · `KnowledgeGrid.tsx:20` · `WikiLibrary.tsx:16`
- 리더와의 판정 일치: 리더의 `isExpired`(`WikiPageContent.tsx:124-125`, `expires_at < Date.now()`)와 모듈의 `isExpired`(`:49-55`)는 같은 규칙이고 파싱 불가 입력에서도 결과가 같다
- 테스트: `tests/verification-label.test.tsx:105-125`(만료는 검증으로 세지 않는다) · `:127-146`(홈에서 무표시로 지나가지 않고, `.badge.verified`는 붙지 않는다) · `tests/workspace-home.test.tsx:118-131`(select 컬럼 3종 가드 — 모의가 이제 `select()` 인자를 기록한다)

`Shared state and control language`의 *"same label wherever it appears"* 에 부합한다. 리더가 이전부터 쓰던 `"검증 만료됨"` 상태명을 목록이 그대로 채택했으므로 상태명이 갈리지 않는다.

### 7. 홈의 배지 게이트와 `workspace-home-prd.md` §3.3 (8.2)

**충돌로 판정하지 않는다. 다만 사용자의 해석은 두 절 중 한 절만 덮는다.**

PRD `docs/design-systems/v2/workspace-home-prd.md:109`은 두 절이다.
- **절 A** — "검증 뱃지는 `verification_status='verified'` 일 때만 `.badge.verified` 로 표기한다": 구현은 `verified = isVerified(page)` 일 때만 `.verified`를 붙인다(`KnowledgeGrid.tsx:91,122`). `isVerified`는 `verified ∧ ¬disputed ∧ ¬만료`라 PRD 조건의 **진부분집합**이다 → 위반 없음. 사용자의 해석("그 문장이 관장하는 건 `.badge.verified`")은 이 절에 대해 정확하다.
- **절 B** — "나머지 3종(`partial`·`unverified`·`disputed`)은 뱃지를 달지 않는다": 열거가 enum 값이라는 지적은 맞다(`PRODUCT-INVARIANTS.md:82` — *"`disputed` 는 같은 이름의 boolean 컬럼 `wiki_pages.disputed` 와 별개다"*, `0001_core_schema.sql:148-149`). 그러나 **enum 값과 boolean은 배타가 아니다.** `verification_status='unverified'` ∧ `disputed=true` 인 행은 절 B가 열거한 `unverified`에 해당하면서 새 게이트(`KnowledgeGrid.tsx:118`)에 걸려 중립 `.badge`("충돌 감지")를 얻는다. 그리고 `0001_core_schema.sql:143`이 *"disputed: 시스템이 세팅하고 사람이 해소합니다"* 라고 못박았으므로 이 조합은 예외가 아니라 **가장 흔한 조합**이다.

그럼에도 위반으로 세지 않는 이유:
1. PRD 문장의 주어는 행 구성(`:108`)이 정의한 **"검증 뱃지"** 이고, 새 배지는 검증 단계가 아니라 충돌·만료라는 다른 신호를 이름 붙인다. `.badge.verified`(검증 뱃지)는 절 A대로 좁혀져 있다
2. PRD는 OpenSpec 스펙이 아니며, 상위 문서인 `PRODUCT-INVARIANTS.md`(§7 뱃지 색 규칙 포함)는 이 조합을 다루지 않는다. 델타 스펙은 반대로 목적지 간 상태 표기 일관성을 `SHALL`로 요구한다
3. 배지가 색이 아니라 텍스트로 상태를 말하므로 `Member encounters a non-default state`와도 어긋나지 않는다

⚠️ 다만 `KnowledgeGrid.tsx:97-101`의 주석은 "열거된 3종은 enum 값이라 boolean과 별개"까지만 적고 **"그래서 unverified 문서도 배지를 얻을 수 있다"** 는 결과를 적지 않았다. PRD `:223`의 검증 계획("검증 뱃지가 `verification_status='verified'` 에서만 표시")을 문자 그대로 실행하는 다음 사람은 이 게이트를 회귀로 오인한다. 아래 권고 2번.

### 8. `WikiLibrary` 통계 라벨·술어 (8.3)

**충족.** `WikiLibrary.tsx:109`가 `pages.filter((p) => isVerified(p)).length`, `:110`이 `<span>검증됨</span>`이다. 두 결함이 함께 닫혔다 — ① 한 화면 안에서 목록은 "검증됨", 통계는 "검증 완료"로 갈리던 이중 어휘, ② `verification_status === "verified"` 직접 비교가 바로 아래 목록이 "충돌 감지"·"검증 만료됨"으로 그린 행을 검증으로 세던 숫자-행 모순. `.doc-meta` 라벨(`:165`)과 통계 술어가 이제 같은 모듈을 통과한다.

## 검증 실행 결과 (새로 실행)

- `pnpm exec vitest run` (apps/dashboard): **241 통과 / 0 실패** (r2 시점 238 → 신규 3건)
- `pnpm exec tsc --noEmit`: 통과
- `pnpm exec eslint .`: 통과
- `openspec validate dashboard-layout-density --strict`: `Change 'dashboard-layout-density' is valid`

tasks.md 6.3·6.4(육안 확인)는 시각 속성이라 이 리뷰에서 재현하지 않는다. r3 변경분은 CSS를 건드리지 않아 r2 시점 실측치(캔버스 5개 = 1280 · Ask 1656 · 리더 820)가 그대로 유효하다.

## 조치가 필요한 항목

미충족 시나리오는 없다. 아래는 **판정을 바꾸지 않는 권고**이며, archive 전에 처리하면 다음 사람이 잘못 인도되는 것을 막는다.

1. **design.md Decision 2가 r3 결정을 담지 못한다** — Decision 2(`design.md:44-54`)는 여전히 *"`verification_status` 값 → 라벨 매핑"* 으로만 서술한다. 실제 모듈 계약은 그보다 넓다: `disputed` 우선순위, `expires_at` 만료 판정, `isVerified`/`isExpiredVerification` 술어, 그리고 **홈이 충돌·만료 문서에도 배지를 띄운다는 사용자 관찰 가능한 결정**. 이 결정들은 지금 tasks.md 8.1·8.2와 코드 주석에만 산다. 프로젝트 규약(`CLAUDE.md` — "하나의 change 안에서만 유효한 결정은 그 change의 design.md를 인용한다")대로 Decision 2에 한 문단을 덧붙인다.
2. **`KnowledgeGrid.tsx:97-101` 주석과 PRD §3.3의 접점을 끝까지 적는다** — 위 7번 절 B. 주석에 "`verification_status`가 `unverified`·`partial`이어도 boolean `disputed`가 참이면 중립 배지를 띄운다. PRD `:109`의 '나머지 3종은 뱃지를 달지 않는다'는 검증 뱃지에 대한 규칙이고, `:223`의 검증 계획도 같은 범위로 읽는다"를 한 줄 추가하거나, PRD 쪽에 예외를 명시한다.
3. **리더의 `verified`·`expired` 문구는 아직 모듈에서 파생되지 않는다** — `WikiPageContent.tsx:359`(`검증됨`) · `:371`(`검증 만료됨`)은 리터럴이다. 현재 문자열이 모듈과 **우연히 일치**할 뿐이고, 이 일치를 지키는 테스트가 없다(리더를 렌더해 모듈 라벨과 대조하는 케이스는 `verification-label.test.tsx`에 없다 — 홈·라이브러리만 있다). 8.1의 목적이 정확히 "리더만 만료를 알고 목록은 검증됨" 상태의 재발 방지였으므로, `disputed`·`partial`과 같은 모양으로 두 분기도 `verificationLabel`에서 파생시키고 리더를 세 번째 목적지로 회귀 테스트에 넣는 편이 낫다.
4. **(부수) `design.md:8`의 "`.content`는 6개 목적지가 공유"는 5개다** — r2에서도 적었고 8.8에서 누락됐다. 같은 문서의 Decision 1 표(`:32-36`)는 5개로 정확하다.
5. **(부수) CSS `:745-746`이 스펙에 없는 문장을 인용한다** — 주석이 *"single content width shared uniformly by all destinations"* 를 델타 요구사항으로 인용하는데, 7.1 이후 그 문장은 존재하지 않는다(현재 문구: *"Destinations that render on the shared content canvas SHALL all use one and the same maximum content width"*). 지금 주석은 Ask·리더까지 1280에 묶어야 한다고 읽힌다 — r1이 blocked를 걸었던 바로 그 오독이다.

## 판정 근거

델타 스펙의 시나리오 9건이 전부 파일·줄 단위 증거와 함께 충족되고, 요구사항 본문의 두 조항(목적지 간 동일 라벨 · 상태 텍스트 가독 크기)도 충족된다. r2가 유일한 미충족으로 지목한 리더의 `disputed` 라벨은 홈·라이브러리와 같은 모듈에서 파생되어 세 목적지가 `"충돌 감지"` 하나로 수렴했고, 남겨졌던 근거("UI-SPEC Copywriting Contract")가 리포지토리에 없다는 사실도 재확인했다. 나머지 네 건(proposal 정합 · design.md 갱신 · topbar 테스트 태그 커버리지 · 예외 열거 완화)도 각각 확인했다.

r3에서 새로 들어온 `expires_at` 편입은 범위 이탈이 아니라 **요구사항을 지키기 위해 필요했던 배선**이다. 편입 전에는 같은 문서를 리더가 "검증 만료됨", 목록이 "검증됨"으로 불렀고 이는 요구사항 본문이 금지한 바로 그 상태다. 홈의 배지 게이트 확장은 `workspace-home-prd.md` §3.3의 `.badge.verified` 규칙을 진부분집합으로 지키므로 충돌하지 않는다 — 다만 사용자의 해석은 그 문장의 첫 절만 덮으며, `unverified ∧ disputed` 조합에서는 두 번째 절("나머지 3종은 뱃지를 달지 않는다")과 문자 그대로는 부딪힌다. PRD가 스펙이 아니고 그 문장의 대상이 "검증 뱃지"라는 점, 상위 문서인 `PRODUCT-INVARIANTS.md`가 이를 다루지 않는다는 점, 델타 스펙이 반대 방향을 `SHALL`로 요구한다는 점에서 위반으로 세지 않되, 주석에 결과까지 적어 두라는 권고로 남긴다.

검증 4종을 새로 실행해 전부 통과했다(테스트 241건, r2 대비 +3). 남은 권고 5건은 전부 문서·주석 정합과 회귀 방지 강화이며, 어느 것도 명세된 동작의 미구현이 아니다 — 따라서 `pass`다.
