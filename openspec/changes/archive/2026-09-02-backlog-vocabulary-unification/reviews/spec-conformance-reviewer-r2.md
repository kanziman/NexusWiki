# Spec Conformance 리뷰 — backlog-vocabulary-unification r2

- 판정: needs_fix
- 대상: `git diff origin/main` (작업 트리 미커밋 변경분, base `b274d46`)
- 일시: 2026-09-02T14:09:45Z
- 검토 범위: 이 브랜치의 change 두 건을 함께 다룬다.
  1. `2026-09-02-knowledge-grid-item-caps` — r1 `pass` 이후 구현 파일이 재수정되어 **회귀만** 확인
  2. `2026-09-02-backlog-vocabulary-unification` — **신규 판정 대상** (delta spec 시나리오 4개, 그중 2개 신규)

## 1. backlog-vocabulary-unification (신규 판정)

### 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Shared state and control language / Member encounters a non-default state | 충족 | 위키 열 빈 상태(카테고리 필터 분기 포함) `apps/dashboard/components/KnowledgeGrid.tsx:108-112`, 백로그 열 빈 상태 `:205-207`, 소스 연결 콜아웃 `:255`. 백로그 전용 화면 빈 상태 `apps/dashboard/components/BacklogList.tsx` → 테스트 `apps/dashboard/tests/BacklogList.test.tsx:203`, 홈 그리드 빈 상태 테스트 `apps/dashboard/tests/KnowledgeGrid.test.tsx:124-135`. 색이 아닌 텍스트로 상태를 말한다 |
| Shared state and control language / Member sees the same underlying status on two destinations | 충족 | 라벨·색 매핑이 `apps/dashboard/lib/verification-label.ts` 단일 출처로 이동(`verificationToneClass` `apps/dashboard/lib/verification-label.ts:106-118` 신설(주석 포함)). 홈 소비 `KnowledgeGrid.tsx:143,146`, 위키 라이브러리 소비 `WikiLibrary.tsx:310-312,915`. 라이브러리 로컬 `verificationToneClass` 사본은 제거됨(diff `WikiLibrary.tsx -9`). 테스트 `apps/dashboard/tests/verification-label.test.tsx:32`(verified 동일 라벨) · `:62`(disputed) · `:127`(만료가 홈에서 무표시로 지나가지 않음) |
| Shared state and control language / Member reaches one destination from several surfaces | 충족(테스트 부분 미비) | 내비게이션 `apps/dashboard/components/WorkspaceSidebar.tsx:350`, 브레드크럼 `apps/dashboard/components/WorkspaceShell.tsx:31` → 렌더 `:55,120`, 목적지 heading `apps/dashboard/components/BacklogList.tsx:72`, 홈 요약 섹션 `apps/dashboard/components/KnowledgeGrid.tsx:186`(`지식 공백 (작성 대기 백로그)` — 앞머리가 정본, 괄호는 뒤에 붙은 gloss라 요구사항 본문의 `MAY append a parenthetical gloss after that canonical name` 조항을 만족한다), 미리보기 내비 `PreviewWorkspace.tsx:55` · 미리보기 홈 요약 `:314` · 미리보기 화면 제목 `:641`. 네 표면이 모두 `지식 공백`이다. 다만 단언이 있는 표면은 내비게이션뿐이다(아래 조치 3번) |
| Shared state and control language / Assistive technology user hears a destination name | **미충족** | LNB는 충족 — `aria-label="지식 공백"` `WorkspaceSidebar.tsx:343`, 보이는 라벨 `:350`, 둘의 일치를 잡는 테스트 `apps/dashboard/tests/WorkspaceSidebar.test.tsx:107-109`(`getByRole(name: "지식 공백")` + `toHaveTextContent("지식 공백")`). **그러나** 홈의 백로그 요약 영역 로딩 스켈레톤이 `aria-label="작성 대기 백로그 로딩 중"`을 그대로 들고 있다 — `apps/dashboard/app/w/[workspaceId]/loading.tsx:100` |

### 요구사항 본문 대조

| 본문 조항 | 결과 | 증거 |
| --- | --- | --- |
| 목적지가 내비·브레드크럼·heading·타 목적지 요약에서 하나의 정본 명칭 | 충족 | 위 표 3행 |
| **including the accessible name exposed to assistive technology** | **미충족** | `loading.tsx:100` |
| `MAY append a parenthetical gloss after ... MUST NOT replace it` | 충족(홈 섹션) / 위반(로딩 스켈레톤) | 홈 섹션 `KnowledgeGrid.tsx:186`은 `지식 공백` + 괄호 gloss. 로딩 스켈레톤은 gloss `작성 대기 백로그`만 남기고 정본 명칭을 **대체**했다 |
| 정본 스펙 동기화 | 충족 | `openspec/specs/dashboard-design-consistency/spec.md:33,43-49`이 delta와 문자 단위 일치. `openspec validate --specs --strict` = 34 passed |

### tasks.md 완료 주장 대조

| Task | 결과 | 비고 |
| --- | --- | --- |
| 1.1 `h1` → `지식 공백` | 충족 | `BacklogList.tsx:72` |
| 1.2 브레드크럼 · LNB 라벨 · `aria-label` | 부분 | 셸 내부는 충족(`WorkspaceShell.tsx:31`, `WorkspaceSidebar.tsx:343,350`). 그러나 task가 경고한 바로 그 함정(“보이는 이름만 고치면 스크린리더 사용자에게는 옛 명칭이 남는다”)이 홈 로딩 스켈레톤에 그대로 남았다 |
| 1.3 `PreviewWorkspace` 명칭 정렬 | 충족 | `:55,314,641` |
| 1.4 홈 섹션 gloss 유지 | 충족 | `KnowledgeGrid.tsx:186` |
| 2.1 사이드바 테스트 갱신 + 접근성 이름 검증 | 충족 | `WorkspaceSidebar.test.tsx:107-109` |
| 2.2 `apps/dashboard`에 옛 명칭 `미완성 백로그` 잔존 없음 | 부분 | `.tsx`/`.ts` 소스·테스트에는 없다. 다만 `apps/dashboard/public/backlog-preview.html:753,768,783`과 `apps/dashboard/public/sources-preview.html:817`에 `미완성 백로그`가 남아 있다(아래 관찰 1) |
| 3.1 검증 재실행 | 충족 | 이번 라운드에서 새로 실행: `pnpm test` 73 files / 381 passed, `pnpm typecheck` 무출력 성공, `pnpm lint` `No issues found`, `openspec validate --specs --strict` 34 passed |
| 3.2 동기화·아카이브 | 충족 | 정본 반영 확인, change는 `changes/archive/` 아래에 있다 |

## 2. knowledge-grid-item-caps (r1 `pass` 회귀 확인)

r1 이후 `KnowledgeGrid.tsx`가 다시 수정됐으므로 네 시나리오를 재확인했다. **모두 여전히 충족**한다.

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Populated wiki and backlog display | 충족 | 상한 `MAX_WIKI_PAGES = 5` · `MAX_BACKLOG_ITEMS = 4` `KnowledgeGrid.tsx:60-61`, 적용 `:76-77`. 카테고리 뱃지 `:116`, 검증 뱃지 `:143-146`, 인용 수 `:153`, 백로그 인용 수 `:236`. 테스트 `KnowledgeGrid.test.tsx:42-59` |
| Empty state display | 충족 | `:108-112`, `:205-207`, 콜아웃 `:255`. 테스트 `KnowledgeGrid.test.tsx:124-135` |
| Member follows a backlog source-connection CTA | 충족 | `href={`${base}/sources?prefillTitle=…&tab=text`}` `KnowledgeGrid.tsx:240`. 테스트 `KnowledgeGrid.test.tsx:52-55` |
| Workspace has more items than the home grid shows | 충족 | 전용 화면 링크 `data-od-id="view-all-documents"` `:99`, `data-od-id="view-all-backlog"` `:195`. 15/12건 시나리오에서 `href`를 직접 단언 `KnowledgeGrid.test.tsx:178-183` |
| 카테고리 라벨 매핑 · 비대칭 그리드 | 충족 | `CATEGORY_LABELS` `:54-59`, 루트 `className="sections"` `:80` 유지 |

라벨 중앙화(`verificationToneClass` → `lib/verification-label.ts`)는 홈이 렌더링하는 문자열을 바꾸지 않았고, 상한·CTA·전용 화면 링크·뱃지 구성 어느 것도 잃지 않았다. **회귀 없음.**

## 조치가 필요한 항목

1. **홈 로딩 스켈레톤의 접근성 이름이 옛 gloss에 머물러 있다** — `apps/dashboard/app/w/[workspaceId]/loading.tsx:100`의 `aria-label="작성 대기 백로그 로딩 중"`. 이 영역은 로드 후 `지식 공백 (작성 대기 백로그)`(`KnowledgeGrid.tsx:186`)가 되는 홈의 백로그 요약 섹션이다. 스크린리더 사용자는 로딩 중 `작성 대기 백로그`, 로딩 후 `지식 공백 …`을 들어 같은 영역이 두 이름을 갖는다. 근거 Scenario: *“Assistive technology user hears a destination name … the announced accessible name matches the visible canonical name rather than an older or alternate term”* 및 요구사항 본문 *“MUST NOT replace it with a different term.”* 같은 파일 `:74`의 좌측 열이 `aria-label="위키 문서 로딩 중"`으로 **목적지 정본 명칭 + 로딩 중** 패턴을 쓰고 있어, 이 한 곳만 규칙을 벗어난 것이 분명하다. 제안: `aria-label="지식 공백 로딩 중"`으로 바꾸고, `apps/dashboard/tests/LoadingSkeletons.test.tsx`(현재 `aria-label`을 전혀 단언하지 않는다)에 `getByRole("region", { name: "지식 공백 로딩 중" })` 단언을 추가해 다음 리스타일이 조용히 되돌리지 못하게 한다.

2. **백로그 전용 화면의 영역·컨트롤 접근성 이름이 gloss 단독이다** — `apps/dashboard/components/BacklogList.tsx:81`(`aria-label="백로그 요약"`), `:95`(`aria-label="백로그 필터"`), `:120`(`aria-label="백로그 검색"`). 화면 heading은 `지식 공백`(`:72`)인데 그 안의 세 영역은 정본 명칭 없이 `백로그`만 쓴다. 1번보다 약한 사례다 — 이들은 보이는 라벨이 없는 화면 내부 컨트롤이라 Scenario의 WHEN(“whose visible label is that destination's canonical name”)에 정면으로 걸리지는 않는다. 다만 요구사항 본문의 “including the accessible name exposed to assistive technology”를 문자 그대로 읽으면 같은 결함군이다. 제안: `지식 공백 요약` · `지식 공백 필터` · `지식 공백 검색`으로 맞추고 `BacklogList.test.tsx:252,314`의 단언을 함께 갱신하거나, 화면 내부 컨트롤은 이 조항의 대상이 아니라는 판단을 change 노트에 남긴다. 어느 쪽이든 코드 범위 안에서 끝난다.

3. **Scenario 3의 표면 네 개 중 하나만 테스트가 지킨다** — 단언이 있는 곳은 내비게이션(`WorkspaceSidebar.test.tsx:107-109`)뿐이다. 브레드크럼(`WorkspaceShell.tsx:31`), 목적지 heading(`BacklogList.tsx:72`), 홈 요약 섹션 제목(`KnowledgeGrid.tsx:186`)은 어느 테스트도 문자열을 검사하지 않아, 셋 중 하나가 옛 이름으로 되돌아가도 381개 테스트가 전부 통과한다. 이 change의 전부가 “명칭이 갈라지지 않게 고정한다”이므로 고정 장치가 한 곳뿐인 것은 계약의 4분의 1만 지키는 것이다. 제안: `WorkspaceShell.test.tsx`에 `/w/ws-1/backlog` 경로 브레드크럼 단언, `BacklogList.test.tsx`에 `getByRole("heading", { name: "지식 공백" })`, `KnowledgeGrid.test.tsx`에 섹션 제목이 `지식 공백`으로 **시작**하는지(gloss 허용) 단언을 추가한다.

## 관찰 (판정에 영향 없음)

1. **`apps/dashboard/public/*.html` 프로토타입에 옛 명칭 잔존** — `backlog-preview.html:753,768,783`, `sources-preview.html:817`에 `미완성 백로그`가 있다. 이 파일들은 이 브랜치에서 새로 생긴 **미추적(untracked) 파일**이라 `git diff origin/main`에 들어오지 않고, 성격상 `docs/design-systems/`의 프로토타입과 같은 부류다(사용자가 인지하고 열어 둔 항목). 미충족으로 판정하지 않는다. 다만 `apps/dashboard/public/`은 Next.js가 `/backlog-preview.html`로 정적 서빙하는 경로이므로, **이 파일들을 커밋에 포함시킬 계획이라면** task 2.2(“`apps/dashboard` 소스와 테스트 어디에도 없다”)의 주장은 그때 문자 그대로 깨진다. 커밋 대상에서 빼거나 명칭을 함께 맞추는 편이 좋다.
2. **홈 메트릭 카드 라벨 `작성 대기 지식 공백`** — `apps/dashboard/app/w/[workspaceId]/page.tsx:351`, 테스트 `apps/dashboard/tests/workspace-home.test.tsx:134`. 정본 명칭 `지식 공백`을 포함하되 앞에 수식어가 붙은 형태다. 요구사항이 허용한 것은 “뒤에 붙는 괄호 gloss”뿐이라 문자적으로는 어긋나 보이지만, `MetricCard`는 링크가 아니라 통계 카드이며(`page.tsx:62-111`, 앵커 없음) 같은 열의 `연결된 원문 소스` · `컴파일된 위키 문서`와 동일한 “수식어 + 명사” 패턴을 따른다. 목적지 참조가 아니라 지표 이름으로 읽는 것이 타당해 미충족으로 세지 않는다. 다르게 읽을 여지가 있으니 판단을 어딘가에 남겨 두면 다음 사람이 다시 묻지 않는다.
3. **항목 어휘는 여전히 `백로그`** — 빈 상태 문구 `작성 대기 중인 백로그가 없습니다`(`KnowledgeGrid.tsx:205`, `BacklogList.tsx`), 테이블 헤더 `백로그 주제`. 이 change는 **목적지 명칭**만 통일했고 항목을 부르는 말은 건드리지 않았다. delta spec도 목적지에 한정하므로 위반이 아니다.
4. **`PreviewWorkspace.test.tsx:33`의 단언이 느슨해졌다** — `getByText(/작성 대기 백로그/)`는 `지식 공백 (작성 대기 백로그)`의 부분 문자열로 여전히 통과한다. 즉 이 테스트는 정본 명칭이 앞머리에 있는지를 검사하지 않는다. 조치 3번과 함께 다루면 좋다.
5. **열 링크 라벨 비대칭** — 위키 열은 `전체 보기`(`KnowledgeGrid.tsx:96-102`, 라벨 `:101`), 백로그 열은 `보완하기`(`:192-198`, 라벨 `:197`). knowledge-grid-item-caps의 tenant-isolation r1이 지적한 항목이며 이 change의 delta 시나리오(목적지 **명칭**)에는 걸리지 않는다. 컨트롤 어휘 문제로 별도 판단이 필요하다.

## 판정 근거

`needs_fix`다. delta spec이 이번에 새로 추가한 두 시나리오 중 `Member reaches one destination from several surfaces`는 네 표면 모두 코드 증거로 충족하지만, `Assistive technology user hears a destination name`은 충족하지 않는다. 홈의 백로그 요약 영역은 로딩 상태에서 `aria-label="작성 대기 백로그 로딩 중"`(`loading.tsx:100`)을 노출해, 정본 명칭을 gloss로 **대체**한다 — 요구사항 본문이 `MUST NOT`으로 금지한 형태이자, tasks.md 1.2가 스스로 경고한 “보이는 이름만 고치면 스크린리더 사용자에게는 옛 명칭이 남는다”의 실제 사례다. 같은 파일 `:74`가 `위키 문서 로딩 중`으로 올바른 패턴을 보여 주므로 스펙이 모호한 것이 아니라 한 곳이 누락된 것이고, 문자열 한 줄과 단언 하나로 스펙 범위 안에서 해결된다 — 그래서 `blocked`가 아니라 `needs_fix`다. 여기에 명칭 고정 장치(테스트)가 네 표면 중 하나에만 걸려 있어, 이 change의 목적인 “다음 화면이 새 이름을 붙이지 못하게 한다”가 아직 회귀 방지력을 갖추지 못했다.

함께 검토한 `knowledge-grid-item-caps`는 r1 이후의 재수정(라벨·색 매핑 중앙화, 미리보기 마크업 정렬)에도 네 시나리오와 요구사항 본문이 모두 그대로 충족되어 **회귀가 없다**. 이 change 쪽 판정은 r1의 `pass`를 유지한다.
