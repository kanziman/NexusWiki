# Spec Conformance 리뷰 — backlog-vocabulary-unification r3

- 판정: **pass**
- 대상: `git diff origin/main` (작업 트리 미커밋 변경분, base `b274d46`)
- 일시: 2026-09-02T14:43:31Z
- 검토 범위: 이 브랜치의 change 두 건을 함께 다룬다.
  1. `2026-09-02-backlog-vocabulary-unification` — r2 `needs_fix` 재판정 (delta 시나리오 4개)
  2. `2026-09-02-knowledge-grid-item-caps` — r1 `pass` 이후 라벨 통일이 들어와 회귀 확인 (delta 시나리오 4개)
- 이번 라운드는 판정을 문장이 아니라 **변이 실험(mutation test)** 으로 세웠다. 각 표면의
  문자열을 옛 명칭으로 되돌린 뒤 테스트가 실제로 깨지는지 확인하고 원본을 복원했다.
  복원 후 전체 파일 체크섬이 실험 전과 **바이트 단위로 동일**함을 확인했다.

## 1. backlog-vocabulary-unification

### 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Shared state and control language / Member encounters a non-default state | 충족 | 위키 열 빈 상태(카테고리 필터 분기) `apps/dashboard/components/KnowledgeGrid.tsx:107-112`, 백로그 열 빈 상태 `:203-206`, 소스 연결 콜아웃 `:255` 부근. 백로그 전용 화면 빈 상태 `apps/dashboard/components/BacklogList.tsx:32`(`EMPTY_HEADING`) → 테스트 `apps/dashboard/tests/BacklogList.test.tsx`, 홈 빈 상태 테스트 `apps/dashboard/tests/KnowledgeGrid.test.tsx:124-135`. 색이 아니라 텍스트로 상태를 말한다 |
| Shared state and control language / Member sees the same underlying status on two destinations | 충족 | 라벨·색 단일 출처 `apps/dashboard/lib/verification-label.ts:61`(`verificationLabel`) · `:115`(`verificationToneClass`). 소비처가 전부 이 모듈을 import 한다 — `KnowledgeGrid.tsx:18`, `WikiLibrary.tsx:28`, `WikiPageContent.tsx:27`, `PreviewWorkspace.tsx:30`, `app/w/[workspaceId]/page.tsx:7`. 로컬 사본 없음. 테스트 `apps/dashboard/tests/verification-label.test.tsx` |
| Shared state and control language / Member reaches one destination from several surfaces | **충족 (r2 조치 3 해소)** | 네 표면 모두 `지식 공백` — 내비 `WorkspaceSidebar.tsx:350`, 브레드크럼 `WorkspaceShell.tsx:31`→렌더 `:108-121`, 목적지 heading `BacklogList.tsx:72`, 홈 요약 섹션 `KnowledgeGrid.tsx:186`(`지식 공백 (작성 대기 백로그)` — 정본 명칭 뒤에 붙은 괄호 gloss라 요구사항 본문의 `MAY append` 조항 안에 있다). 네 표면 **전부** 회귀 테스트로 고정됐다(아래 변이 실험표) |
| Shared state and control language / Assistive technology user hears a destination name | **충족 (r2 미충족 해소)** | r2가 지적한 `loading.tsx:100`이 `aria-label="지식 공백 로딩 중"`으로 수정됐다 — 같은 파일 `:74`(`위키 문서 로딩 중`)의 "정본 명칭 + 로딩 중" 패턴과 일치한다. LNB `WorkspaceSidebar.tsx:343` `aria-label="지식 공백"` ↔ 보이는 라벨 `:350` 일치, 테스트 `apps/dashboard/tests/WorkspaceSidebar.test.tsx:107-109`가 둘의 일치를 잡는다(변이 실험으로 확인) |

### 요구사항 본문 대조

| 본문 조항 | 결과 | 증거 |
| --- | --- | --- |
| 목적지가 내비·브레드크럼·heading·타 목적지 요약에서 하나의 정본 명칭 | 충족 | 위 표 3행 |
| **including the accessible name exposed to assistive technology** | **충족** | `apps/dashboard` 전체에서 백로그 목적지를 가리키는 `aria-label`은 6곳이며 전부 `지식 공백`으로 시작한다 — `loading.tsx:100`, `BacklogList.tsx:81,95,120`, `WorkspaceSidebar.tsx:343`. 옛 명칭(`미완성 백로그`)이나 gloss 단독(`작성 대기 백로그`, `백로그 …`) `aria-label`은 소스에 하나도 남지 않았다 |
| `MAY append a parenthetical gloss after ... MUST NOT replace it` | 충족 | 정본 명칭을 **대체**하는 표면이 없다. `KnowledgeGrid.tsx:186`과 `PreviewWorkspace.tsx:314`만 gloss를 쓰며 둘 다 `지식 공백`이 앞머리다 |
| 정본 스펙 동기화 | 충족 | `openspec/specs/dashboard-design-consistency/spec.md`의 Requirement 본문·신규 시나리오 2개가 delta와 문자 단위 일치. `openspec validate --specs --strict` = 34 passed |

### 변이 실험 — 회귀 방지력 실측

r2 조치 3번("표면 4개 중 하나만 테스트가 지킨다")의 해소 여부를 실측했다.
각 행은 해당 문자열을 옛 명칭으로 되돌린 뒤 테스트를 돌린 결과다.

| 되돌린 표면 | 주입한 변이 | 테스트 결과 | 판정 |
| --- | --- | --- | --- |
| 브레드크럼 `WorkspaceShell.tsx:31` | `지식 공백` → `미완성 백로그` | **FAIL** `WorkspaceShell.test.tsx > 백로그 목적지의 브레드크럼은 정본 명칭 지식 공백을 쓴다` | 잡는다 |
| 목적지 heading `BacklogList.tsx:72` | `<h1>지식 공백</h1>` → `<h1>미완성 백로그</h1>` | **FAIL** `BacklogList.test.tsx > 화면 제목은 정본 명칭 지식 공백을 쓴다` | 잡는다 |
| LNB 접근성 이름 `WorkspaceSidebar.tsx:343` | `aria-label="지식 공백"` → `"미완성 백로그"` | **FAIL** `WorkspaceSidebar.test.tsx > renders main navigation items…` | 잡는다 |
| 홈 요약 섹션 제목 `KnowledgeGrid.tsx:186` | `지식 공백 (작성 대기 백로그)` → `미완성 백로그` | **FAIL** `KnowledgeGrid.test.tsx > … 최대 5개 … 최대 4개 …` | 잡는다 |
| 백로그 화면 요약 영역 `BacklogList.tsx:81` | `aria-label="지식 공백 요약"` → `"백로그 요약"` | **FAIL** `BacklogList.test.tsx > renders backlog items, top stats…` | 잡는다 |
| 홈 로딩 스켈레톤 `loading.tsx:100` | `aria-label="지식 공백 로딩 중"` → `"작성 대기 백로그 로딩 중"` | **PASS**(6 passed) | **잡지 못한다** (관찰 1) |
| 백로그 화면 필터 nav `BacklogList.tsx:95` | `aria-label="지식 공백 필터"` → `"백로그 필터"` | **PASS**(12 passed) | **잡지 못한다** (관찰 1) |

Scenario 3의 네 표면은 이제 **전부** 고정됐다. 나머지 두 건은 코드가 이미 옳고
테스트만 없는 상태라 시나리오 미충족이 아니다 — 관찰로 남긴다.

### tasks.md 완료 주장 대조

| Task | 결과 | 비고 |
| --- | --- | --- |
| 1.1 `h1` → `지식 공백` | 충족 | `BacklogList.tsx:72` + 신규 테스트(변이로 확인) |
| 1.2 브레드크럼 · LNB 라벨 · `aria-label` | **충족** | r2에서 부분이던 항목이 해소됐다. `WorkspaceShell.tsx:31`, `WorkspaceSidebar.tsx:343,350`, `loading.tsx:100` |
| 1.3 `PreviewWorkspace` 명칭 정렬 | 충족 | `:55`(내비 라벨) · `:314`(홈 요약) · `:641`(화면 제목) 모두 `지식 공백` |
| 1.4 홈 섹션 gloss 유지 | 충족 | `KnowledgeGrid.tsx:186` |
| 2.1 사이드바 테스트 갱신 + 접근성 이름 검증 | 충족 | `WorkspaceSidebar.test.tsx:107-109`. `getByRole(name:"지식 공백")`(접근성 이름) + `toHaveTextContent("지식 공백")`(보이는 라벨) 두 축을 모두 단언한다 |
| 2.2 옛 명칭 `미완성 백로그` 잔존 없음 | **충족** | `apps/dashboard`의 `.ts`/`.tsx` 소스에 없다. 테스트 2곳(`WorkspaceShell.test.tsx:57`, `KnowledgeGrid.test.tsx:201`)은 `not.toHaveTextContent` 음성 단언이라 잔존이 아니다. r2 관찰 1이던 `apps/dashboard/public/*-preview.html`은 `.gitignore:51`로 제외됐고 `git ls-files apps/dashboard/public/`에 없다 — 커밋되지 않는다 |
| 3.1 검증 재실행 | 충족 | 이번 라운드에서 새로 실행(아래 「검증 실행 기록」) |
| 3.2 동기화·아카이브 | 충족 | 정본 반영 확인, `openspec list` = 활성 change 없음(둘 다 `changes/archive/` 아래) |

## 2. knowledge-grid-item-caps (r1 `pass` 회귀 확인)

r1 이후 백로그 열 링크 라벨이 `보완하기` → `전체 보기`로 바뀌었으므로 네 시나리오를 재확인했다. **모두 여전히 충족**한다.

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Populated wiki and backlog display | 충족 | `MAX_WIKI_PAGES = 5` `KnowledgeGrid.tsx:60`, `MAX_BACKLOG_ITEMS = 4` `:61`, 적용 `:76-77`. 카테고리·검증·인용 뱃지와 백로그 인용 수·CTA 구성 변화 없음. 테스트 `KnowledgeGrid.test.tsx:42-59`, 상한 `:137-`(제목도 "최대 5개 · 최대 4개") |
| Empty state display | 충족 | `:107-112`, `:203-206`, 콜아웃 `:255` 부근. 테스트 `:124-135` |
| Member follows a backlog source-connection CTA | 충족 | `?prefillTitle=…&tab=text` 링크 유지. 테스트 `:52-55` |
| **Workspace has more items than the home grid shows** | 충족 | 위키 열 `href={`${base}/wiki`}` + `data-od-id="view-all-documents"` `:99`, 백로그 열 `href={`${base}/backlog`}` + `data-od-id="view-all-backlog"` `:195`. 라벨 통일(`전체 보기` `:101`, `:197`)은 링크의 **존재·목적지**를 바꾸지 않았고, 시나리오가 요구하는 것은 "전용 경로로 가는 링크를 노출한다"이지 특정 라벨이 아니다. 전용 화면에는 상한이 없어 나머지 항목에 실제로 도달한다 |
| 카테고리 라벨 매핑 · 비대칭 그리드 | 충족 | `CATEGORY_LABELS` `:54-59`, 루트 `className="sections"` `:80` 유지 |

라벨 통일에 대한 변이 실험:

| 주입한 변이 | 테스트 결과 |
| --- | --- |
| 백로그 열 링크 라벨 `전체 보기` → `보완하기` | **FAIL** `KnowledgeGrid.test.tsx` (두 링크가 같은 라벨을 쓰는지 단언 `:187-194`) |
| `data-od-id="view-all-backlog"` 제거(리네임) | **FAIL** `KnowledgeGrid.test.tsx` (`href` 단언 `:178-186`) |

즉 상한만 낮추고 탈출구 링크를 조용히 잃는 회귀는 테스트가 막는다. **회귀 없음.** r1의 `pass`를 유지한다.

## 검증 실행 기록 (이번 라운드 신규 실행)

| 명령 | 결과 |
| --- | --- |
| `pnpm --dir apps/dashboard test` | **73 files / 383 passed, 0 failed** (변이 복원 후 재실행) |
| `pnpm --dir apps/dashboard typecheck` (`tsc --noEmit`) | 무출력 성공(exit 0) |
| `pnpm --dir apps/dashboard lint` (`eslint .`) | 무출력 성공(exit 0) |
| `openspec validate --specs --strict` | 34 passed, 0 failed |
| `openspec list` | 활성 change 없음(둘 다 아카이브됨) |
| 변이 실험 후 체크섬 대조 | 변경 파일 12개 전부 실험 전과 동일 |

## 조치가 필요한 항목

**없다.** delta spec 두 건의 시나리오 8개가 모두 코드 증거로 충족되며, r2가 미충족으로 잡은
`Assistive technology user hears a destination name`과 조치 2·3번이 전부 해소됐다.
아래 관찰은 **이 브랜치를 막는 사유가 아니다** — 어느 것도 명세된 동작을 어기지 않는다.

## 관찰 (판정에 영향 없음)

1. **접근성 이름 2곳이 코드는 옳으나 테스트가 없다** — `loading.tsx:100`(`지식 공백 로딩 중`)과 `BacklogList.tsx:95`(`지식 공백 필터`)는 옛 명칭으로 되돌려도 테스트가 통과한다(위 변이 실험표). 시나리오는 **동작**을 요구하고 동작은 존재하므로 미충족이 아니다. 다만 r2가 실제로 잡아낸 회귀 지점이 바로 `loading.tsx:100`이었다는 점에서, `LoadingSkeletons.test.tsx`에 `getByRole("region", { name: "지식 공백 로딩 중" })` 한 줄을 넣어 두면 같은 회귀가 세 번째로 돌아오지 못한다. 후속 change 범위로 충분하다.
2. **홈 섹션 제목 단언이 "앞머리"가 아니라 "포함"을 본다** — `KnowledgeGrid.test.tsx:200`은 `toHaveTextContent("지식 공백")`(부분 문자열)이라 `작성 대기 백로그 (지식 공백)`처럼 gloss가 앞으로 오는 형태도 통과한다. 요구사항 본문은 gloss가 정본 명칭 **뒤**에 오도록 규정한다(`MAY append a parenthetical gloss after that canonical name`). 현재 코드는 올바르고, 이 느슨함이 지금 무엇을 놓치고 있지는 않다.
3. **`PreviewWorkspace.test.tsx:33`의 느슨한 정규식** — `getByText(/작성 대기 백로그/)`는 `지식 공백 (작성 대기 백로그)`의 부분 문자열로 통과하므로 정본 명칭 자체를 검사하지 않는다. r2 관찰 4가 그대로 남았다. 미리보기는 개발용 화면이라 우선순위가 낮다.
4. **홈 메트릭 카드 `작성 대기 지식 공백`** — `app/w/[workspaceId]/page.tsx:351`. r2 관찰 2와 같은 판단을 유지한다. `MetricCard`는 링크가 아닌 지표 카드이고 같은 열의 `연결된 원문 소스` · `컴파일된 위키 문서`와 동일한 "수식어 + 명사" 패턴이라 목적지 참조가 아니라 지표 이름으로 읽는 것이 타당하다. 정본 명칭을 **대체**하지 않고 포함하므로 `MUST NOT replace` 조항에도 걸리지 않는다.
5. **항목 어휘는 여전히 `백로그`** — 빈 상태 `작성 대기 중인 백로그가 없습니다`(`KnowledgeGrid.tsx:205`, `BacklogList.tsx:32`), 테이블 헤더 `백로그 주제`. 이 change는 **목적지 명칭**만 통일했고 항목을 부르는 말은 범위 밖이다. delta spec도 destination에 한정한다.
6. **설계 문서·프로토타입의 옛 명칭** — `docs/design-systems/v2/backlog-management-prd.md` 등에 `작성 대기 백로그`가 남아 있고, `apps/dashboard/public/*-preview.html`에는 `미완성 백로그`·`보완하기`가 남아 있다. 후자는 이번에 `.gitignore:51`(`apps/dashboard/public/*-preview.html`)로 제외돼 커밋되지 않으며, 그 주석이 `public/`이 미들웨어 밖이라는 이유까지 적어 두었다. 전자는 사용자가 인지하고 열어 둔 항목이므로 미충족으로 세지 않는다.
7. **⚠️ 리뷰 중 작업 트리가 동시 변경됐다** — 첫 전체 테스트 실행(23:39:31)에서 `KnowledgeGrid.test.tsx`가 1건 실패했고, 실패 출력의 렌더 결과는 홈 백로그 섹션 제목이 `미완성 백로그`였다. 같은 시각 `KnowledgeGrid.tsx`(23:39:39) · `WorkspaceShell.tsx`(23:39:43) · `BacklogList.tsx`(23:39:47) · `WorkspaceSidebar.tsx`(23:39:49)의 mtime이 갱신됐다 — 다른 세션이 같은 워크트리에서 변이 실험을 하고 복원하는 중이었던 것으로 보인다. 직후 단독 실행과 이후 두 번의 전체 실행은 383건 전부 통과했고, 최종 파일 체크섬도 정상이다. **판정은 최종 상태 기준이다.** 다만 이 브랜치는 아직 미커밋이므로, 커밋 직전에 전체 테스트를 한 번 더 돌려 최종 스냅샷을 확정하는 편이 안전하다.

## 판정 근거

`pass`다. r2가 유일한 미충족으로 지목한 `Assistive technology user hears a destination name`은
`loading.tsx:100`의 `aria-label`이 `지식 공백 로딩 중`으로 고쳐지면서 해소됐고, 백로그 목적지를
가리키는 `aria-label` 6곳을 직접 훑은 결과 정본 명칭을 **대체**하는 표면은 하나도 남지 않았다.
r2 조치 2번(`백로그 요약`·`백로그 필터`·`백로그 검색`)도 세 곳 모두 `지식 공백 …`으로 정렬됐다.

r2가 가장 무겁게 본 조치 3번 — "명칭 고정 장치가 네 표면 중 하나뿐" — 은 변이 실험으로 해소를
확인했다. 브레드크럼 · 목적지 heading · LNB 접근성 이름 · 홈 요약 섹션 제목을 각각 옛 명칭으로
되돌리면 **네 번 모두 서로 다른 테스트가 실패한다.** 즉 이 change의 목적인 "다음 화면이 새 이름을
붙이지 못하게 한다"가 이제 실제 방지력을 갖췄다. 이 방지력이 이미 한 번 작동한 증거도 있다 —
동시 실행 중이던 다른 세션이 주입한 `미완성 백로그` 변이를 첫 전체 실행이 그대로 잡아냈다(관찰 7).

함께 검토한 `knowledge-grid-item-caps`는 백로그 열 링크 라벨이 `보완하기` → `전체 보기`로 바뀌었지만,
`Workspace has more items than the home grid shows`가 요구하는 것은 전용 경로로 가는 링크의 **존재**이지
라벨이 아니다. 링크의 `href`와 `data-od-id`가 그대로이고 두 링크의 `href`·라벨을 단언하는 테스트가
변이에 반응하므로 회귀가 없다. r1의 `pass`를 유지한다.

남은 지적은 전부 테스트 커버리지 여유분과 문서 잔존 명칭이며, 명세된 동작을 어기는 것이 없어
`needs_fix`로 라운드를 한 번 더 도는 근거가 되지 않는다. 스펙 모호나 범위 이탈도 없으므로
`blocked` 사유도 아니다.
