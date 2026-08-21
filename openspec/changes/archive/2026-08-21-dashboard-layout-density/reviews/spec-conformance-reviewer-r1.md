# Spec Conformance 리뷰 — dashboard-layout-density r1

- 판정: blocked
- 대상: `git diff main` (working tree, `HEAD` = `main` = `747d7de`, 이 change의 작업은 전부 미커밋 상태)
- 일시: 2026-08-20T22:36:44Z

## 시나리오 판정

### Requirement: Consistent workspace page structure

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Consistent workspace page structure / Member moves between workspace destinations | 충족 | 네 목적지 모두 가시 제목 유지 — 홈 `apps/dashboard/app/w/[workspaceId]/page.tsx:103`, 소스 `apps/dashboard/components/SourcesList.tsx:145`, Ask `apps/dashboard/components/AskConversation.tsx:291`, 설정 `apps/dashboard/app/w/[workspaceId]/settings/page.tsx:61`. 셸·포커스 처리 미변경(`apps/dashboard/components/WorkspaceShell.tsx:80`, CSS `:focus-visible` 블록). 테스트 `apps/dashboard/tests/WorkspaceShell.test.tsx` 등 52파일 236케이스 통과 |
| Consistent workspace page structure / Member switches content viewer tabs within Ask | 충족 | 이 change가 손대지 않은 기존 구현 — `apps/dashboard/components/ContentViewer.tsx:99`(제목 `인용 인스펙터`) · `:101`(`role="tablist"`) · `:110-111`(`role="tab"` · `aria-selected`) · `:130`(`role="tabpanel"`). 테스트 `apps/dashboard/tests/ContentViewer.test.tsx` 통과 |
| Consistent workspace page structure / **Member compares destinations on a wide viewport** | **미충족** | `.content` 단일 폭은 성립한다 — `docs/design-systems/v2/nexuswiki-design-system.css:750`(`width: min(1280px, 100%)`)이고 오버라이드 4개에서 `width` 선언이 제거됐다(`:1082` settings · `:1581` sources · `:2479` backlog · `:2733` library). 파일 전체에 `.content` 대상 `width` 선언은 750행 하나뿐임을 확인했다. **그러나 Ask 목적지는 `.content`를 쓰지 않는다** — `apps/dashboard/app/w/[workspaceId]/ask/page.tsx:26`이 `AskLayout`을 렌더하고 `.ask-layout`(CSS `:2130`)은 `grid-template-columns: minmax(420px,1fr) 6px minmax(360px,42%)`로 폭 상한이 없어 뷰포트를 가득 채운다. 위키 문서 상세도 `.reader-layout`(CSS `:1901`) + `.reader { width: min(820px, 100%) }`(CSS `:1908`)다. 1920px에서 홈은 1280px 중앙 정렬, Ask는 약 1656px 전폭 → 좌우 경계가 다르고 홈이 "measurably narrower"다. 원문 소스 상세도 별개다 — `apps/dashboard/app/w/[workspaceId]/sources/[id]/page.tsx:52`가 Tailwind `max-w-4xl`(896px) |
| Consistent workspace page structure / Member scans destinations for repeated decorative context | 부분 충족 | 5곳 제거 확인 — `AskConversation.tsx:289` · `BacklogList.tsx:82` · `SourcesList.tsx:143` · `WikiLibrary.tsx:89` · `settings/page.tsx:60`(전부 제거 사유 주석으로 대체). 브레드크럼은 유지하되 읽기용 클래스로 전환 — `WikiPageContent.tsx:137`(`.breadcrumb-path`), CSS `:494`에 `.breadcrumb-path` 신설(12px, uppercase·자간 없음). **다만 워크스페이스 홈에 `<p className="eyebrow">워크스페이스</p>`가 그대로 남아 있다** — `apps/dashboard/app/w/[workspaceId]/page.tsx:97`. design.md Decision 3의 판정 표는 이 화면을 아예 다루지 않았다 |

⚠️ **요구사항 본문 중 시나리오가 없는 조항 2건**

- *"a single content width shared uniformly by all destinations"* — 위 세 번째 시나리오와 같은 사유로 미충족.
- *"each destination SHALL give visual precedence to its own primary work object rather than repeating an identical title-description-table rhythm"* — **미충족**. 구현 diff에 구조 변경이 하나도 없다. 여섯 화면은 여전히 `h1` + 설명문 + 표/목록의 동일 리듬이다(홈 `page.tsx:93-130`, 소스 `SourcesList.tsx:140-150`, 위키 `WikiLibrary.tsx:86-110`, 백로그 `BacklogList.tsx:79-90`, 설정 `settings/page.tsx:57-62`). design.md Decision 5가 "구조 재배치는 화면별 후속 change의 몫"이라고 명시적으로 연기했는데, 델타 스펙은 이를 `SHALL`로 단정한다.

### Requirement: Shared state and control language

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Shared state and control language / Member encounters a non-default state | 충족 | 이 change가 손대지 않은 기존 구현. 색이 아니라 텍스트로 상태를 말한다 — `apps/dashboard/components/WikiPageContent.tsx:366`(`검증 만료됨 · … 재검증 필요`) · `:374` · `apps/dashboard/components/OperationsPanel.tsx:227,231,237`. 회귀 없음(전체 테스트 통과) |
| Shared state and control language / **Member sees the same underlying status on two destinations** | **충족** | 단일 출처 모듈 신설 `apps/dashboard/lib/verification-label.ts:45`(`verified` → "검증됨"). 홈은 `apps/dashboard/components/KnowledgeGrid.tsx:80`(`isVerified`) · `:100`(`verificationLabel`), 위키 라이브러리는 `apps/dashboard/components/WikiLibrary.tsx:36`(`const stateLabel = verificationLabel`). 테스트 `apps/dashboard/tests/verification-label.test.tsx:32`가 두 컴포넌트를 **실제로 렌더**해 같은 `data-od-id` 항목 텍스트에 같은 라벨이 들어 있는지 확인한다(`KnowledgeGrid.tsx:91` · `WikiLibrary.tsx:154`). 기존 단언도 갱신됨 — `tests/KnowledgeGrid.test.tsx:43` · `tests/workspace-home.test.tsx:102`. 실행 확인: 3파일 8케이스 통과 |

⚠️ **요구사항 본문 중 시나리오 밖 조항 2건**

- *"A given underlying status value SHALL be presented with the same label wherever it appears, so that one state is never named differently on two destinations."* — **미충족**. 위키 문서 상세(`/w/[id]/wiki/[slug]`)는 워크스페이스 목적지인데 자체 문자열을 그대로 들고 있다.
  - `partial` → `apps/dashboard/components/WikiPageContent.tsx:374` `"부분 검증됨 · 재검증이 필요합니다"` vs 모듈 `"부분 검증"`(`lib/verification-label.ts:48`)
  - `disputed` → `WikiPageContent.tsx:16` `"충돌 감지됨 — …"` vs 모듈 `"충돌 감지"`(`lib/verification-label.ts:46`)
  - ⚠️ `WikiPageContent.tsx:12`에 *"UI-SPEC Copywriting Contract — 문구를 한 글자도 바꾸지 않는다"* 주석이 있다. 즉 이 불일치는 코드 실수가 아니라 **다른 계약과의 충돌**이다.
  - (참고: 공개 위키 라우트 `app/p/[slug]/[page]/page.tsx:108`은 `verified`를 `"검증 및 승인됨"`으로 표시한다. anon 공개 경로라 "workspace destination"은 아니므로 판정 대상에서 제외하되 기록해 둔다.)
- *"Status text SHALL be rendered at a size that remains legible rather than shrunk to a decorative marker."* — **부분 충족**. 아래에서 따로 다룬다.

### ⚠️ design.md Decision 4 "표적 상향"의 델타 스펙 적합성 — 사용자 지정 확인 항목

**상향된 부분(확인됨)**: `body` 14→15px(CSS `:73`), `.status` 11→12px(`:494` 부근, 주석 포함), `.badge` 10→12px(`:527`), `.backlog .doc-title:before`("작성 대기") 9→12px(`:967`), `.tag` 10→12px(`:1921`), `.inspect .kicker` 9→12px(`:2325`), `.verified` 9→12px(`:2330` 부근), `.inspect .tag` 9→12px(`:2380` 부근), `.public-badge` 9→12px(`:2655`), `.public-stamp` 10→12px(`:2666`). tasks.md 2.2·2.3이 열거한 대상은 전부 반영됐다.

**그럼에도 미충족으로 판정하는 근거**: 이 change가 스스로 세운 12px 하한 **아래에 실제 사용 중인 상태 텍스트가 남아 있다.**

| 대상 | 크기 | 문구 | 사용처 |
| --- | --- | --- | --- |
| `.metric small` | **9px** (CSS `:1337`) | "대기" · "실행 중" · "실패" | `apps/dashboard/components/OperationsPanel.tsx:227,231,237`. `.metric.dead { color: var(--danger) }`(CSS `:1339`)로 실패 상태에 색까지 붙는, 명백한 상태 텍스트다 |
| `.share-state` | **10px** (CSS `:1405`) | "ON" · "OFF" | `apps/dashboard/components/PublicSharingSettings.tsx:79`. `.share-state.on { color: var(--good) }`(CSS `:1409`) — 공개 공유 킬스위치의 상태 표시 |

두 곳은 tasks.md 2.2의 열거 목록에도, design.md Decision 4의 표에도 없다. 그런데 "실패"(9px, danger)는 이 제품에서 가장 작은 텍스트이면서 파이프라인 장애를 알리는 문구다 — 스펙 문구 *"rather than shrunk to a decorative marker"* 가 정확히 겨냥하는 대상이다. 따라서 **범위 축소 자체는 타당하지만(전면 스케일 조정은 델타 스펙이 요구하지 않는다), 축소한 결과가 요구사항을 다 덮지는 못했다.** 이 항목은 코드만 고치면 되므로 needs_fix 급이다.

### Requirement: Constrained global knowledge actions (ADDED)

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Constrained global knowledge actions / Member views the global action bar | 충족 | `apps/dashboard/components/WorkspaceShell.tsx:80`(`.topbar`) 안의 `.top-actions`는 소스 추가(`:85-92`, `data-od-id="add-source-button"`)와 질문 시작(`:93-99`, `data-od-id="ask-top-button"`) 둘뿐이다. `AccountMenu`(`:100`)와 모바일 내비 버튼(`:101-109`)은 요구사항이 명시적으로 제외한 "account and navigation controls"다. 셸은 모든 워크스페이스 라우트가 공유하므로 "any workspace destination" 조건을 만족한다 |
| Constrained global knowledge actions / A destination needs its own action | 충족 | 목적지 고유 행동이 각자의 content frame 안에 있다 — 소스 업로드는 `.content sources` 안(`SourcesList.tsx:140` 이하 Dropzone), 검증 액션은 리더 안(`WikiPageContent.tsx:182` 이하), 초대는 설정 패널 안(`SettingsMembersPanel` / `InviteForm`). topbar에 추가된 목적지 고유 행동은 없다 |

⚠️ 관찰: 이 ADDED 요구사항은 proposal.md가 스스로 밝힌 대로 "회귀 방지용 명문화"인데, **tasks.md에 대응 task가 하나도 없고 topbar 행동 개수를 고정하는 테스트도 없다**(`tests/WorkspaceShell.test.tsx`에 개수 단언 없음 확인). 현 상태로는 충족이지만 회귀를 막는 장치는 없다.

## 검증 실행 결과 (새로 실행)

- `pnpm exec vitest run` (apps/dashboard): 52 파일 / 236 케이스 통과
- `pnpm exec tsc --noEmit`: 통과(출력 없음)
- `pnpm exec eslint .`: 통과(출력 없음)
- `openspec validate dashboard-layout-density --strict`: `Change 'dashboard-layout-density' is valid`

tasks.md 6.1·6.2의 완료 주장은 재현된다. 6.3·6.4(육안 확인)는 시각 속성이라 이 리뷰에서 재현할 수 없다 — 판정하지 않는다.

## 조치가 필요한 항목

1. **[사람의 결정 필요] 단일 본문 폭이 Ask·위키 리더에 걸리지 않는다** — 델타 스펙은 *"a single content width shared uniformly by all destinations"* 와 *"both content areas begin and end at the same horizontal boundaries, with no destination rendering measurably narrower than another"* 를 요구하는데, design.md Non-Goals가 `.ask-layout` · `.reader-layout`을 명시적으로 제외했다. 두 화면은 각각 UX-05의 3열 리사이즈 계약(`AskLayout.tsx`)과 `restore-standalone-wiki-reader`의 레이아웃을 소유하므로 폭을 1280으로 묶는 것은 코드 수정이 아니라 범위 결정이다. 제안: 둘 중 하나를 사람이 고른다 — (a) 요구사항 문구를 "shared content frame(`.content`)을 쓰는 목적지" 로 한정하고 Ask·리더가 자기 레이아웃을 소유한다는 사실을 스펙에 명문화한다, (b) Ask·리더를 이 change 범위에 넣는다.

2. **[사람의 결정 필요] "목적지별 시각 위계 차별화"가 스펙에는 SHALL, 구현에는 없다** — 델타 스펙의 *"each destination SHALL give visual precedence to its own primary work object rather than repeating an identical title-description-table rhythm"* 에 대응하는 구현이 diff에 없다(eyebrow 제거뿐). design.md Decision 5가 스스로 후속 change로 연기했다. 이대로 archive되면 `openspec/specs/dashboard-design-consistency/spec.md`가 구현되지 않은 동작을 단정하게 된다. 제안: 이 문장을 델타 스펙에서 빼고 후속 change의 델타로 옮기거나, 구조 변경을 이 change 범위에 포함한다.

3. **[사람의 결정 필요] 위키 리더의 상태 문구가 단일 어휘를 벗어난다** — `WikiPageContent.tsx:374` `"부분 검증됨"` ↔ `lib/verification-label.ts:48` `"부분 검증"`, `WikiPageContent.tsx:16` `"충돌 감지됨"` ↔ `:46` `"충돌 감지"`. 근거 Scenario/요구사항: *"one state is never named differently on two destinations."* 다만 `WikiPageContent.tsx:12`의 "UI-SPEC Copywriting Contract — 한 글자도 바꾸지 않는다"와 정면 충돌하므로 어느 계약이 우선인지 사람이 정해야 한다. 제안: 리더 문구를 `{verificationLabel(...)} · {설명}` 형태로 재조립해 라벨 부분만 모듈에서 파생시키고, UI-SPEC 카피 계약 주석을 그에 맞게 갱신한다.

4. **[코드 수정] 12px 하한을 벗어난 상태 텍스트 2곳** — `.metric small` 9px(CSS `:1337`, "대기·실행 중·실패", `OperationsPanel.tsx:227,231,237`)와 `.share-state` 10px(CSS `:1405`, "ON/OFF", `PublicSharingSettings.tsx:79`). 근거 요구사항: *"Status text SHALL be rendered at a size that remains legible rather than shrunk to a decorative marker."* 제안: 두 선택자를 12px로 올리고 tasks.md 2.2의 열거 목록과 design.md Decision 4의 표에 추가한다. `.metric`은 3열 그리드 안이라 상향 후 줄바꿈을 육안 확인한다.

5. **[코드 수정] 홈의 `.eyebrow`가 남아 있고, CSS 주석이 사실과 다르다** — `app/w/[workspaceId]/page.tsx:97`에 `<p className="eyebrow">워크스페이스</p>`가 남았는데 design.md Decision 3의 판정 표는 이 화면을 다루지 않았다. 동시에 CSS `:479` 신설 주석은 *"지금 앱 화면에서는 쓰지 않는다 — 프리뷰(PreviewWorkspace)와 프로토타입 HTML 만 남는다"* 라고 적었지만 **양쪽 다 틀렸다**: 앱 홈이 아직 쓰고 있고, `PreviewWorkspace.tsx`에는 `className="eyebrow"`가 한 곳도 남아 있지 않다(`PreviewHome`의 `WORKSPACE · LOCAL REVIEW` 포함 전부 제거됨). 제안: 홈 eyebrow의 존치/제거를 Decision 3 표에 명시적으로 판정해 넣고, CSS 주석을 실제 사용처와 일치시킨다. 지금 주석은 다음 사람을 잘못 인도한다.

6. **[선택] 전역 행동 2개 제한에 회귀 방지 테스트가 없다** — ADDED 요구사항 전체에 대응 task가 tasks.md에 없다. 제안: `tests/WorkspaceShell.test.tsx`에 `.top-actions` 안의 지식 행동이 정확히 둘임을 단언하는 케이스를 추가한다. 요구사항의 목적이 "회귀 방지"인데 그것을 지키는 장치가 없다.

## 판정 근거

시나리오 7건 중 6건은 증거와 함께 충족되고, 사용자가 지목한 상태 어휘 단일화(`Member sees the same underlying status on two destinations`)는 공유 모듈·양쪽 컴포넌트 배선·두 목적지를 실제 렌더하는 테스트까지 갖춰 가장 튼튼하게 구현됐다. 검증 4종도 새로 실행해 전부 통과했다.

그럼에도 `blocked`인 이유는 **이 change가 스스로 작성한 델타 스펙이 스스로 선언한 범위보다 넓기 때문**이다. 요구사항 본문은 "all destinations"의 단일 폭과 목적지별 시각 위계 차별화를 `SHALL`로 단정하는데, 같은 change의 design.md는 그 둘을 각각 Non-Goal(Decision 1 주변)과 후속 change(Decision 5)로 명시적으로 배제했다. 즉 코드를 고쳐서 좁힐 수 있는 간극이 아니라, **스펙 문구를 좁힐지 구현 범위를 넓힐지 사람이 골라야 하는 간극**이다. 여기에 위키 리더의 상태 문구가 다른 계약(UI-SPEC Copywriting Contract)에 묶여 있어 어느 계약이 우선인지도 사람의 결정을 요한다. 이 상태로 archive하면 `openspec/specs/dashboard-design-consistency/spec.md`가 구현되지 않은 동작을 단정하게 되고, 이후 모든 conformance 리뷰가 같은 지점을 영구히 미충족으로 잡는다.

사용자가 지목한 design.md Decision 4(타이포 표적 상향)에 대해서는 별도로 판정한다 — **범위 축소의 방향 자체는 타당하나 결과가 요구사항을 다 덮지 못했다.** 델타 스펙은 전면 스케일 조정을 요구한 적이 없으므로 "상태 텍스트만 올린다"는 판단은 스펙에 부합하지만, 실제 사용 중인 상태 텍스트 두 곳(`.metric small` 9px · `.share-state` 10px)이 새 하한 아래에 남았다. 이 항목만 놓고 보면 `needs_fix`이며, 위 1~3번이 없었다면 전체 판정도 `needs_fix`였을 것이다.
