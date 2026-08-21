# Spec Conformance 리뷰 — dashboard-layout-density r2

- 판정: needs_fix
- 대상: `git diff` 워킹 트리 + untracked (`apps/dashboard/lib/verification-label.ts` · `apps/dashboard/tests/verification-label.test.tsx`). 브랜치 `feat/dashboard-layout-density`, `HEAD` = `747d7de` (이 change 작업은 전부 미커밋)
- 일시: 2026-08-20T22:55:38Z

## 시나리오 판정

### Requirement: Consistent workspace page structure

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Member moves between workspace destinations | 충족 | 네 목적지 모두 가시 제목·콘텐츠 프레임 유지. 홈 `apps/dashboard/app/w/[workspaceId]/page.tsx:101-110`, 소스 `apps/dashboard/components/SourcesList.tsx:140-148`, Ask `apps/dashboard/components/AskConversation.tsx:294-297`, 설정 `apps/dashboard/app/w/[workspaceId]/settings/page.tsx:57-62`. 포커스 처리 미변경. 테스트 238케이스 통과 |
| Member switches content viewer tabs within Ask | 충족 | 이 change가 손대지 않은 기존 구현 — `apps/dashboard/components/ContentViewer.tsx:99-130`(`role="tablist"`·`role="tab"`·`aria-selected`·`role="tabpanel"`). `tests/ContentViewer.test.tsx` 통과 |
| **Member compares shared-canvas destinations on a wide viewport** | **충족** | 공유 캔버스 폭 선언이 `docs/design-systems/v2/nexuswiki-design-system.css:751`(`width: min(1280px, 100%)`) 하나뿐이다. 오버라이드 4개에서 `width`만 제거됨 — `:1083` settings · `:1587` sources · `:2485` backlog · `:2739` library. `.content`를 쓰는 목적지는 정확히 5개다(홈 · 소스 목록 `SourcesList.tsx:139` · 위키 라이브러리 `WikiLibrary.tsx:86` · 백로그 `BacklogList.tsx:79` · 설정). 사용자 실측(left=452 · right=1732 · w=1280, 5개 동일)과 CSS가 일치한다 |
| **Member opens a destination that owns its layout** | **충족** | Ask는 `.ask-layout`(CSS `:2136`, 3열 그리드, 사용자가 리사이즈 바로 경계를 직접 옮긴다 — UX-05), 리더는 `.reader { width: min(820px, 100%) }`(CSS `:1914`). 둘 다 이 change가 건드리지 않았고 델타가 예외로 명시한 그대로다. 실측 Ask 1656 · 리더 820과 일치 |
| Member scans destinations for repeated decorative context | 충족 | `className="eyebrow"` 사용처가 앱 전체에 **0건**이다(`apps/` 대상 grep exit=1). r1이 지적한 홈의 `워크스페이스`도 제거됨(`app/w/[workspaceId]/page.tsx:104` 제거 사유 주석으로 대체). 유일한 맥락 라벨인 위키 리더 브레드크럼은 유지하되 읽기용 `.breadcrumb-path`로 전환(`WikiPageContent.tsx:139`, CSS `:497`), 공개 리더도 같은 클래스로 통일(`app/p/[slug]/[page]/page.tsx:99`) |

**폭 요구사항 문구가 빠져나갈 구멍인가 — 판정**: 아니다, 다만 목적지 집합을 다 덮지는 못한다.
예외 조항은 `"A destination that owns a purpose-built layout is exempt … — specifically the Ask workspace … and the document reader"`로, 서술 기준(purpose-built) 뒤에 **열거(specifically 2개)** 를 붙여 범위를 닫았다. 공유 캔버스 5개 중 어느 하나가 "내 레이아웃은 purpose-built다"라고 주장해 빠져나갈 여지는 열거가 막는다. 사유도 검증 가능하다 — Ask는 사용자가 폭을 직접 조절하고(`AskLayout` 리사이즈), 리더는 820px 읽기 measure다.
⚠️ 그러나 실제 워크스페이스 목적지 중 **원문 소스 상세**(`app/w/[workspaceId]/sources/[id]/page.tsx:52`, Tailwind `max-w-4xl` = 896px)는 공유 캔버스도 아니고 열거된 예외도 아니다. `SourcesList.tsx:324` · `ContentViewer.tsx:437`에서 도달 가능한 실사용 경로다. SHALL이 "공유 캔버스를 쓰는 목적지"로 한정됐으므로 **위반은 아니지만**, "specifically 두 개"라는 문장은 캔버스 밖 목적지가 둘뿐이라고 읽히고 실제로는 셋이다.

### Requirement: Shared state and control language

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Member encounters a non-default state | 충족 | 상태를 색이 아니라 텍스트로 말한다 — `WikiPageContent.tsx:355`(`검증됨 · 날짜`) · `:367`(`검증 만료됨 · … 재검증 필요`) · `:379-383`(`부분 검증 · 재검증이 필요합니다`), `OperationsPanel.tsx:225-238`. 홈의 충돌 배지도 색 없는 `.badge` + 텍스트다(`KnowledgeGrid.tsx:110-111`) |
| Member sees the same underlying status on two destinations | 충족 | 단일 출처 `lib/verification-label.ts:45-58`. 홈 `KnowledgeGrid.tsx:86,91,110-111`, 라이브러리 `WikiLibrary.tsx:38`. 테스트가 두 컴포넌트를 **실제로 렌더**해 같은 `data-od-id` 항목 텍스트를 비교한다 — `tests/verification-label.test.tsx:32`(verified) · `:62`(disputed). 기존 단언도 갱신(`tests/KnowledgeGrid.test.tsx:43` · `tests/workspace-home.test.tsx:102`) |

**요구사항 본문 조항 판정**

- *"A given underlying status value SHALL be presented with the same label wherever it appears…"* — **미충족(1건 잔존)**. 아래 「조치가 필요한 항목」 1번.
- *"Status text SHALL be rendered at a size that remains legible rather than shrunk to a decorative marker."* — **충족**. r1이 지적한 두 곳이 닫혔다: `.metric small` 9→12px(CSS `:1341`, "대기·실행 중·실패", `OperationsPanel.tsx:225-238`) · `.share-state` 10→12px(CSS `:1406-1411`, "ON/OFF", `PublicSharingSettings.tsx:78`). 둘 다 상향 사유 주석 동반.
  하한 아래 잔존 여부를 CSS 전수(9·10·11px 선언 전부)로 다시 훑고 앱 사용처를 대조했다 — 남은 12px 미만은 전부 **탐색 라벨·표 헤더·유형 칩·메타**이지 상태 텍스트가 아니다: `.nav-label`(:177) · `.count`(:219) · `.member-table th`(:1175) · `.role`(:1222, RBAC 역할 속성) · `.pipeline-head`(:1330) · `.table th`(:1624) · `.file span`(:1635) · `.format`(:1648, PDF/MD 유형 칩) · `.public-route`(:1497) · `.backlog-panel-refs h3`(:2552) · `.thread-meta`(:2176) · `.inspect .meta span`(:2356). **새로 발견된 미충족은 없다.**

### Requirement: Constrained global knowledge actions (ADDED)

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Member views the global action bar | 충족 | `WorkspaceShell.tsx:80`(`.topbar`, `data-od-id="workspace-topbar"`) 안 `.top-actions`(`:84`)의 지식 행동은 소스 추가(`:85-92`)·질문 시작(`:93-99`) 둘뿐. `AccountMenu`(`:100`)·모바일 내비(`:101-109`)는 요구사항이 제외한 항목. **회귀 방지 테스트 신설** — `tests/WorkspaceShell.test.tsx:148`이 `.top-actions a` 라벨 배열이 정확히 `["소스 추가","질문 시작"]`임을 단언한다 |
| A destination needs its own action | 충족 | 목적지 고유 행동은 각자의 콘텐츠 프레임 안 — 소스 업로드 `SourcesList.tsx`의 Dropzone, 검증 액션 `WikiPageContent.tsx:182` 이하, 초대 `InviteForm`. topbar에 추가된 것 없음 |

r1의 ⚠️(대응 task·테스트 부재)는 tasks.md 7.9와 위 테스트로 닫혔다. 남은 한계는 「조치가 필요한 항목」 4번.

### 신규 동작 — 홈의 충돌 배지(7.8)가 범위 이탈인가

**범위 안이다.** 이 배선이 없으면 요구사항이 **깨진다**: 홈은 `disputed` 컬럼을 조회하지도(`app/w/[workspaceId]/page.tsx:51`가 이번에 추가) 타입에 갖지도(`KnowledgeGrid.tsx:15-17`) 않았으므로, `verification_status='verified'` + `disputed=true` 문서를 홈은 "검증 완료", 라이브러리는 "충돌 감지"로 불렀다 — 요구사항이 금지하는 바로 그 상태다. 우선순위는 모듈이 소유하고(`lib/verification-label.ts:46`), 홈은 판정을 `isVerified`/`verificationLabel`에 위임한다.
배지 노출 자체(이전엔 verified만 배지)는 사용자 관찰 가능한 확장이지만, ① 요구사항 본문 *"wherever it appears"* 의 직접 결과이고 ② 색 없는 `.badge` + 텍스트라 「Member encounters a non-default state」와도 어긋나지 않으며 ③ tasks.md 7.8에 근거가 기록되고 회귀 테스트(`verification-label.test.tsx:62`)가 붙었다. 조용한 스펙 밖 동작이 아니다.

## 검증 실행 결과 (새로 실행)

- `pnpm exec vitest run` (apps/dashboard): **238 통과 / 0 실패** (r1 시점 236 → 신규 2건)
- `pnpm exec tsc --noEmit`: 통과
- `pnpm exec eslint .`: 통과
- `openspec validate dashboard-layout-density --strict`: `Change 'dashboard-layout-density' is valid`

tasks.md 6.3·6.4(육안 확인)는 시각 속성이라 이 리뷰에서 재현하지 않는다 — 다만 사용자 실측치(캔버스 5개 1280 동일 · Ask 1656 · 리더 820)는 CSS 선언과 모순 없이 일치한다.

## 조치가 필요한 항목

1. **[코드 수정] 위키 리더의 `disputed` 문구가 여전히 단일 어휘 밖이다** — 홈·라이브러리는 `"충돌 감지"`(`lib/verification-label.ts:46`), 리더는 `"충돌 감지됨 — 상충하는 정보가 있습니다. 원문을 확인하세요."`(`WikiPageContent.tsx:16-17`). 근거 요구사항: *"one state is never named differently on two destinations."*
   - 이 문자열은 `partial`과 **같은 자리·같은 마크업**에서 렌더된다 — `WikiPageContent.tsx:165-168`의 `<span className="badge">`는 `:378-383`의 partial 배지와 동일 슬롯이다. 즉 "콜아웃이라 라벨이 아니다"라는 구분은 성립하지 않는다.
   - ⚠️ tasks.md 7.7이 근거로 든 *"UI-SPEC 계약이 보호하는 충돌 콜아웃"* 은 **리포지토리에서 추적되지 않는다**. `docs/design-systems/dashboard-ui-spec.md`는 30줄이며 `충돌`·`disputed`·`검증` 어느 것도 포함하지 않고, 이 문자열은 `openspec/`·`docs/` 어디에도 없다(`WikiPageContent.tsx:17`이 유일한 출현). 보호 계약이 문서로 존재하지 않으므로 partial만 고치고 disputed를 남긴 비대칭에 근거가 없다.
   - 제안: 7.7과 **똑같은 모양**으로 고친다 — `{verificationLabel({ disputed: true })} — 상충하는 정보가 있습니다. 원문을 확인하세요.` 로 재조립해 상태 이름만 모듈에서 파생하고, 뒤 안내 문장은 이 화면 고유 확장으로 유지한다. `WikiPageContent.tsx:13`의 계약 주석도 실제 출처를 가리키도록 고치거나, 출처가 없다면 그 주장을 걷어낸다. 스펙 수정 불필요 → 코드만으로 닫힌다.

2. **[문서 정합] proposal.md가 델타에서 제거된 요구사항을 여전히 약속한다** — 7.2로 "각 목적지가 주 작업 대상에 시각적 비중을 준다"를 델타에서 뺐고, 델타 spec.md·tasks.md에는 잔여 문구가 없음을 확인했다(`precedence`·`rhythm` grep 0건). 그러나 `proposal.md:19`("목적지별 리듬을 차별화한다" — What Changes 항목)과 `:36`("… 목적지별 리듬 차별화를 **추가한다**" — Spec Impact)는 그대로다. 지금 상태로 archive하면 제안서가 약속한 스펙 변경과 실제 baseline이 갈린다. 제안: 두 줄을 후속 change로 이관한다고 명시하거나 삭제한다.

3. **[문서 정합] design.md가 r1 대응 이후를 반영하지 않는다** — CLAUDE.md "계획에서 벗어나면 파일 주석과 원장을 함께 갱신한다" 위반이다.
   - Decision 3 제목 "eyebrow는 6개 중 1개만 남긴다"와 판정표가 여전히 **홈 라우트를 누락**한다(7.4로 제거됨). 실제 결과는 "7곳 전부 제거, 유일 생존자는 `.eyebrow`가 아니라 `.breadcrumb-path`"다.
   - Decision 4의 표적 표에 7.3이 올린 `.metric small` · `.share-state`가 없다.
   - Decision 5는 "스펙은 각 목적지가 자기 주 작업 대상에 시각적 비중을 줄 것을 요구한다"로 시작하는데, 그 요구사항은 7.2로 삭제돼 더 이상 존재하지 않는다.
   - (부수) `design.md:8`의 "`.content`는 6개 목적지가 공유"는 실제 5개다.

4. **[선택] 전역 행동 제한 테스트가 앵커만 본다** — `tests/WorkspaceShell.test.tsx:157`이 `.top-actions a`를 쿼리하므로, 다음 사람이 지식 행동을 `<button>`(예: 모달을 여는 "위키 컴파일")으로 얹으면 잡히지 않는다. 요구사항은 행동의 **개수**를 제한하지 렌더 태그를 제한하지 않는다. 제안: 계정 메뉴·모바일 버튼을 `data-od-id`로 배제한 뒤 `.top-actions` 하위 상호작용 요소 전체를 세는 형태로 바꾼다.

5. **[선택] 좁은 뷰포트에서 라이브러리 상태 텍스트가 10px로 내려간다** — 위키 라이브러리는 상태 라벨을 `.doc-meta` 안 평문으로 둔다(`WikiLibrary.tsx:158-161`). `.doc-meta`는 기본 11px(CSS `:948`)이고 ≤640px 미디어 쿼리에서 10px가 된다(CSS `:1062`). 홈은 같은 라벨을 `.badge`(12px)에 담아 영향이 없다. 이 change가 의도적으로 보존한 11px 본문·메타 대역(tasks.md 2.5)의 파생 효과이고 델타 스펙이 수치 하한을 정하지 않았으므로 **미충족으로 판정하지 않는다.** 다만 같은 상태가 목적지에 따라 12px 배지와 10px 평문으로 갈리므로 기록해 둔다.

## 판정 근거

r1이 `blocked`의 근거로 든 세 항목은 모두 닫혔다. 폭 요구사항은 사용자 결정으로 좁혀졌고, 좁힌 문구가 실측과 정확히 일치하며(캔버스 5개 = 1280 단일, Ask·리더는 자기 레이아웃), 예외 조항은 서술 기준 뒤에 열거를 붙여 자기 선언식 탈출을 막았다. "visual precedence" 조항은 델타·tasks에서 잔여 문구 없이 제거됐다. 상태 텍스트 하한은 지적된 두 곳이 상향됐고, CSS 전수 재점검에서 하한 아래 실사용 상태 텍스트를 더 찾지 못했다. 홈 eyebrow는 제거돼 앱 전체 사용처가 0이며 `.eyebrow` 주석도 그 사실과 일치한다. topbar ADDED 요구사항에는 대응 task와 회귀 테스트가 생겼고, 홈 충돌 배지는 범위 이탈이 아니라 요구사항을 지키기 위해 필요했던 배선이다.

그럼에도 `pass`가 아닌 이유는 **요구사항 본문 한 조항이 아직 열려 있고, 그것이 사람의 결정이 아니라 코드 한 곳의 문제이기 때문이다.** 리더의 `disputed` 라벨은 `partial`과 동일한 배지 슬롯에서 `"충돌 감지됨"`으로 렌더돼 다른 두 목적지의 `"충돌 감지"`와 갈린다. 이를 남긴 근거였던 UI-SPEC 카피 계약은 이 리포지토리에서 확인되지 않는다 — `docs/design-systems/dashboard-ui-spec.md`에 해당 문구가 없고 다른 어떤 스펙·문서에도 없다. 따라서 계약 충돌(= 사람의 결정 = `blocked`)이 아니라 7.7과 같은 모양의 코드 수정으로 닫히는 간극이며, 등급은 `needs_fix`다. 함께 적은 문서 정합 2건(proposal.md·design.md)은 archive 시 baseline과 근거 문서가 갈리는 것을 막기 위한 것으로, 코드 판정과 독립적으로 처리 가능하다.
