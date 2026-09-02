# Tenant Isolation 리뷰 — knowledge-grid-item-caps + backlog-vocabulary-unification r2

- 판정: needs_fix
- 대상: `git diff origin/main` (working tree, base `b274d46` — HEAD == merge-base라 변경분 전부 미커밋 상태)
- 일시: 2026-09-02T14:08:59Z

이 라운드는 **두 change를 함께** 다룬다. 브랜치 `feat/knowledge-grid-design-polish`에 다음 두 건이 같이 실려 있고, r1 지적 3번의 조치가 둘째 change로 분리됐기 때문에 나눠 볼 수 없다.

- `openspec/changes/archive/2026-09-02-knowledge-grid-item-caps/`
- `openspec/changes/archive/2026-09-02-backlog-vocabulary-unification/`

검사 범위(12파일, +262 −154):

- `apps/dashboard/lib/verification-label.ts` (+17 −0)
- `apps/dashboard/components/KnowledgeGrid.tsx` (+107 −70)
- `apps/dashboard/components/WikiLibrary.tsx` (+1 −9)
- `apps/dashboard/components/PreviewWorkspace.tsx` (+91 −56)
- `apps/dashboard/components/BacklogList.tsx` (+1 −1)
- `apps/dashboard/components/WorkspaceShell.tsx` (+1 −1)
- `apps/dashboard/components/WorkspaceSidebar.tsx` (+2 −2)
- `apps/dashboard/tests/KnowledgeGrid.test.tsx` (+17 −7)
- `apps/dashboard/tests/WorkspaceSidebar.test.tsx` (+6 −3)
- `openspec/specs/dashboard-design-consistency/spec.md` (+9 −1)
- `openspec/specs/workspace-home-dashboard/spec.md` (+6 −2)
- `docs/design-systems/wiki-library-redesign-plan.md` (+4 −2)

`git diff origin/main --name-only -- supabase apps/api apps/worker` = 0행. 마이그레이션 · RLS · API · 워커 변경이 이번에도 없음을 직접 확인했다.

## r1 지적 해소 여부

| r1 # | 지적 | 상태 | 근거 |
| --- | --- | --- | --- |
| 1 | 검증 색상 매핑 복제 (높음) | **해소** | `verificationToneClass`가 `lib/verification-label.ts:105-117` 한 곳에만 존재한다. `WikiLibrary.tsx:27`·`KnowledgeGrid.tsx:17`이 같은 함수를 import하고 각각 `:631`·`:143`에서 호출한다. 저장소 전체에서 `text-[var(--good)]`/`--warning`/`--danger`를 검증 상태 판정과 함께 쓰는 인라인 삼항은 0건 |
| 2 | `/preview` 마크업 드리프트 (보통) | **해소** | `PreviewWorkspace.tsx:246-352`가 홈과 같은 섹션 카드 헤더·행 카드·백로그 앰버 좌측 보더를 쓴다. `:246-249` 주석도 "클래스만 공유하고 마크업이 갈라지면"으로 갱신돼 실제로 지키는 불변식을 주장한다. 미사용이 된 `SectionHead` 헬퍼는 제거됐고 lint가 통과한다 |
| 3 | 백로그 명칭 불일치 (보통) | **부분 해소** | 목적지 명칭은 해소됐다(아래 표). 그러나 r1이 함께 요구한 **탈출구 컨트롤 라벨 비대칭**은 그대로다 (조치 1번) |
| 4 | `page.tsx`의 `?? []` (선재, 판정 외) | **미해소(합의된 이월)** | `page.tsx:160,161,189` 그대로. 이번 diff에 `page.tsx`가 포함되지 않음을 확인했다 |

### 3번 — 목적지 명칭 통일 실측

| 표면 | 파일:줄 | 현재 명칭 |
| --- | --- | --- |
| LNB 보이는 라벨 | `WorkspaceSidebar.tsx:350` | `지식 공백` |
| LNB 접근성 이름 | `WorkspaceSidebar.tsx:343` | `지식 공백` |
| 브레드크럼 | `WorkspaceShell.tsx:31` | `지식 공백` |
| 전용 화면 `h1` | `BacklogList.tsx:72` | `지식 공백` |
| 홈 요약 섹션 제목 | `KnowledgeGrid.tsx:186` | `지식 공백 (작성 대기 백로그)` |
| 미리보기 내비 | `PreviewWorkspace.tsx:55` | `지식 공백` |
| 미리보기 화면 제목 | `PreviewWorkspace.tsx:641` | `지식 공백` |
| 미리보기 요약 섹션 | `PreviewWorkspace.tsx:314` | `지식 공백 (작성 대기 백로그)` |

`apps/dashboard` 전체에서 옛 명칭 `미완성 백로그` 검색 결과 **0건**(소스·테스트 포함). 괄호 보조 설명은 `openspec/specs/dashboard-design-consistency/spec.md:33`이 새로 명문화한 "A surface MAY append a parenthetical gloss after that canonical name, but MUST NOT replace it with a different term"에 정확히 해당한다 — 앞머리가 정본이므로 계약 위반이 아니다.

## ⚠️ 통합 시 판정 결과가 바뀌지 않았는지 — 순서 등가성 증명

요청받은 항목이므로 실제로 따져 봤다. `verificationToneClass`가 쓰는 세 술어를 입력 `(d = Boolean(disputed), s = verification_status, e = isExpired(page, now))`로 전개하면:

| 술어 | 참이 되는 조건 |
| --- | --- |
| `page.disputed` | `d` |
| `isVerified(page)` | `¬d ∧ s = "verified" ∧ ¬e` |
| `isExpiredVerification(page)` | `¬d ∧ s = "verified" ∧ e` |

- `disputed` ↔ 나머지 둘: 나머지 둘이 `¬d`를 요구하므로 배타.
- `isVerified` ↔ `isExpiredVerification`: `¬e` vs `e`로만 갈리므로 배타.

세 술어가 **쌍마다 배타**이므로 어떤 입력에서도 최대 하나만 참이다. 따라서 if-체인의 평가 순서는 결과에 영향을 주지 않는다 — 구 `WikiLibrary`의 `disputed → isVerified → isExpiredVerification → muted`와 구 `KnowledgeGrid` 인라인의 `disputed → expired → verified → muted`는 **모든 입력에서 동일한 값**을 낸다. 통합본은 전자의 순서를 그대로 채택했으므로 두 이전 구현 어느 쪽과도 어긋나지 않는다.

구 `KnowledgeGrid`의 `expired`·`verified`가 raw 비교가 아니라 실제로 `isExpiredVerification`·`isVerified` 바인딩이었는지도 원본에서 직접 확인했다(`git show origin/main:apps/dashboard/components/KnowledgeGrid.tsx` 기준 `const verified = isVerified(page)`, `const expired = isExpiredVerification(page)`). raw `verification_status === "verified"` 비교였다면 배타성이 깨져 순서가 결과를 바꿨을 텐데, 그렇지 않았다.

렌더 결과의 등가성도 확인했다. 두 목적지의 상태 span 마크업이 `inline-flex items-center gap-1 text-[10.5px] font-semibold ${verificationToneClass(...)}` + `{verified && <CheckCircle2 size={10} />}` + 라벨로 문자 단위까지 같다(`WikiLibrary.tsx:630-635` ↔ `KnowledgeGrid.tsx:142-147`). `CheckCircle2` 게이트도 양쪽 다 `isVerified`이므로 충돌·만료 문서에 체크 아이콘이 새지 않는다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 해당 없음 | 이 diff에 데이터 접근 코드 없음. 데이터 공급원 `app/w/[workspaceId]/page.tsx:120`은 `@/lib/supabase/server`의 요청자 세션 `createClient()`를 쓰며 이번에도 diff에 없음. 저장소에 `service_client` 사용 흔적 0건 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음. `supabase/migrations` 무변경 |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | SQL 변경 없음. `/preview` 경로는 DB를 읽지 않고 `lib/preview-data.ts` 정적 픽스처만 쓴다(`PreviewWorkspace.tsx` 신규 import는 `BookOpen`·`Link2` 아이콘뿐) |
| A-4 | service_role 코드의 workspace_id 필터 | 해당 없음 | 워커 변경 없음 |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 쓰기 경로 없음. 두 컴포넌트 모두 읽기 전용 렌더 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 동일 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 잡 핸들러 변경 없음 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 없음 |
| D-10 | hnsw.iterative_scan | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 색인/질의 토크나이저 일치 | 해당 없음 | 검색 경로 변경 없음 |
| D-12 | search_tsv 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음. 홈 행의 `인용 원문 N개` 표기(`KnowledgeGrid.tsx:150`)는 `sources` 배열 길이 표시일 뿐 컨텍스트 조립 경로가 아니다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음 |
| 재확인 4-a | 요청자 세션 유지 | 통과 | `page.tsx:120` `await createClient()` — `@/lib/supabase/server`. 변경 없음 |
| 재확인 4-b | `workspace_id` 범위 유지 | 통과 | `raw_sources`·`wiki_pages`·`wiki_links`·`source_chunks` 네 쿼리 전부 `.eq("workspace_id", workspaceId)`(`page.tsx:129,143,148,157`). 변경 없음 |
| 재확인 4-c | `verification-label.ts` 단일 진실 공급원 | 통과(강화됨) | 라벨·판정에 이어 **색**까지 이 모듈로 들어왔다. `apps/dashboard` 내 `verification_status === "verified"` 직접 비교는 `WikiPageContent.tsx`(이번 diff 밖, 선재)를 빼면 0건 |
| 재확인 4-d | 상한의 클라이언트 `slice` 성격 | 통과 | `MAX_WIKI_PAGES = 5` · `MAX_BACKLOG_ITEMS = 4`는 서버가 이미 워크스페이스 범위로 조회한 배열을 자를 뿐이다. 데이터 경계 무변경 |
| 재확인 5 | 빈 상태 / 오류 상태 구분 | 변화 없음 | 이번 수정이 빈 상태 분기를 건드리지 않았다. 문구도 `KnowledgeGrid.tsx:135-138,205` 그대로. `page.tsx`의 `?? []` 3곳도 그대로(이월) |
| 요청 3 | 접근성 이름 ↔ 보이는 라벨 | 통과 | `WorkspaceSidebar.tsx:343`(`aria-label`) · `:350`(span) 둘 다 `지식 공백`. 테스트가 실제로 불일치를 잡는다 — `WorkspaceSidebar.test.tsx:107`의 `getByRole("link", { name: "지식 공백" })`은 `aria-label`이 접근성 이름을 덮으므로 `aria-label`만 보고, `:109`의 `toHaveTextContent("지식 공백")`이 보이는 텍스트를 따로 본다. 한쪽만 바꾸면 둘 중 하나가 반드시 실패한다 |
| 검증 실행 | 테스트 · 타입 · lint · 스펙 | 통과 | `vitest run` (KnowledgeGrid · verification-label · WorkspaceSidebar · PreviewWorkspace · BacklogList · workspace-home) → **46 pass / 0 fail**. `tsc --noEmit` → 오류 없음. `next lint` → 경고·오류 없음. `openspec validate --specs --strict` → 34 passed / 0 failed |

## 조치가 필요한 항목

1. **홈 두 열의 탈출구 컨트롤이 여전히 다르게 불린다 — r1 지적 3번의 미해소 절반** (심각도: 보통)
   - 위치: `apps/dashboard/components/KnowledgeGrid.tsx:101`(`전체 보기`) ↔ `:197`(`보완하기`), 미리보기 동일 위치 `PreviewWorkspace.tsx:269` ↔ `:324`
   - 깨지는 것: 이번 브랜치가 백로그 열의 탈출구 라벨을 `전체 보기 →`에서 `보완하기 →`로 **바꿨다**(diff에서 `-전체 보기 →` / `+<span>보완하기</span>` 확인). 같은 화면에 나란히 선 두 열이, 구조가 완전히 같은 컨트롤(각 열의 전용 화면으로 가는 유일한 링크)을 서로 다른 말로 부른다. 하필 같은 커밋이 백로그 상한을 8→4로 줄여 그 링크 뒤에 숨는 항목 수를 두 배로 늘렸다.
     `openspec/specs/dashboard-design-consistency/spec.md:33`의 `Shared state and control language`는 "consistent accessible controls ... for filters, inputs, **actions**"를 요구한다. 이 브랜치가 바로 그 요구사항을 확장한 change를 함께 싣고 있으면서 액션 어휘의 비대칭은 남겼다.
     완화 요인은 있다 — 헤더 카운트 칩이 잘린 수가 아니라 전체 수(`backlogItems.length`, `KnowledgeGrid.tsx:188`)를 보여 주므로 "12개인데 4개만 보인다"는 사실 자체는 사용자에게 드러난다. 그래서 이 건은 데이터 은폐가 아니라 어휘 일관성 문제로 본다.
     그리고 어느 테스트도 두 라벨을 단언하지 않는다. `KnowledgeGrid.test.tsx:172-179`는 `data-od-id`의 `href`만 본다 — 라벨이 무엇으로 바뀌든 통과한다. r1이 지적한 그대로이며 이번에도 보강되지 않았다.
   - 조치: 두 열을 같은 규칙으로 통일한다(`전체 보기` 또는 `N개 더 보기`). 실제 홈과 `/preview` 양쪽을 함께 고친다. 통일한 라벨을 `KnowledgeGrid.test.tsx`에서 `href`와 나란히 단언해 다음 리스타일이 조용히 되돌리지 못하게 한다.
   - 참고: 인계 내용에는 이 건이 `backlog-vocabulary-unification`으로 처리됐다고 적혀 있으나, 해당 change의 `proposal.md`·`tasks.md`는 **목적지 명칭만** 다루고 컨트롤 라벨을 언급하지 않는다. 실제로 코드도 바뀌지 않았다.

2. **커밋 전 결정이 필요한 미추적 파일 — `public/`에 인증 없이 서빙되는 HTML 4개** (심각도: 보통)
   - 위치: `apps/dashboard/public/redesign-preview.html` · `backlog-preview.html` · `sources-preview.html` · `wiki-library-preview.html` (전부 untracked, `git check-ignore` 결과 무시 규칙 없음)
   - 깨지는 것: `apps/dashboard/middleware.ts:81`의 matcher는 `["/w/:path*", "/login", "/signup", "/"]`뿐이다. `public/` 아래 정적 파일은 미들웨어 게이트를 **아예 지나지 않는다**. 이 상태로 `git add -A` 후 배포하면 `https://<app>/redesign-preview.html` 등 4개 URL이 인증 없이 열린다.
     내용을 훑어 시크릿·JWT·UUID·실제 워크스페이스 데이터가 없음은 확인했다(전부 목업 문구). 그래서 테넌트 데이터 유출은 아니다. 다만 저장소 관례는 디자인 목업을 `docs/design-systems/`에 두는 것이며(같은 working tree의 `docs/design-systems/dashboard-redesign-preview.html`·`backlog-redesign-plan.md`·`sources-redesign-plan.md`가 그 자리에 있다), `public/`에 놓인 4개만 관례를 벗어나 있다. 두 change 어느 쪽의 Impact에도 없어 아무도 리뷰하지 않은 채 딸려 들어갈 수 있는 위치다.
   - 조치: `docs/design-systems/`로 옮기거나 `.gitignore`에 넣는다. 의도적으로 공개 서빙하려는 것이라면 그 결정을 change의 `design.md`에 근거와 함께 남긴다.

## 관찰 — 판정에 반영하지 않음

3. **새로 세운 목적지 명칭 계약의 테스트 커버리지가 LNB 한 곳뿐이다** (심각도: 낮음)
   - `dashboard-design-consistency`에 추가된 `Member reaches one destination from several surfaces` 시나리오는 내비게이션 · 브레드크럼 · 페이지 제목 · 타 목적지의 요약 섹션 **넷 모두**를 요구하지만, 회귀를 잡는 테스트는 `WorkspaceSidebar.test.tsx:107-109`(내비게이션)뿐이다. `WorkspaceShell`의 브레드크럼 매핑(`:31`)과 홈 요약 섹션 제목(`KnowledgeGrid.tsx:186`)을 단언하는 테스트는 없다.
   - 게다가 `PreviewWorkspace.test.tsx:33`은 `/작성 대기 백로그/`, 즉 **선택적인 괄호 보조 설명 쪽**을 단언한다. 스펙상 gloss는 MAY이므로, 누가 괄호를 떼면(계약상 허용) 이 테스트가 깨지고 반대로 앞머리 정본 명칭이 바뀌어도 통과한다 — 단언 대상이 뒤집혀 있다.
   - 지금은 옛 명칭이 0건이므로 실제 불일치는 없다. 다음 화면이 추가될 때 계약만 남고 강제력이 없는 상태가 되지 않도록 기록해 둔다.

4. **`verificationToneClass`만 `now` 파라미터가 없다** (심각도: 낮음)
   - 위치: `apps/dashboard/lib/verification-label.ts:113`
   - 같은 모듈의 `verificationLabel` · `isVerified` · `isExpiredVerification`은 전부 `now: number = Date.now()`를 받는데 `verificationToneClass`만 받지 않는다. 내부에서 `isVerified(page)`와 `isExpiredVerification(page)`를 각각 호출하므로 `Date.now()`가 렌더 한 번에 최대 세 번(라벨 포함) 따로 읽힌다. `expires_at`가 정확히 그 밀리초 경계에 있는 문서에서만 라벨과 색이 갈릴 수 있고, `Date.now()`가 단조 증가하므로 "둘 다 거짓"이 되는 구멍은 없다. 실무상 무해하지만, 테스트가 시간을 고정해 이 매핑을 검증할 수 없다는 점은 남는다. 실제로 `verification-label.test.tsx`에 `verificationToneClass` 케이스가 0건인 이유이기도 하다.
   - 조치(선택): 시그니처를 `(page, now = Date.now())`로 맞추고 내부 두 호출에 같은 `now`를 넘긴 뒤, 네 상태(충돌·검증·만료·미검증)의 토큰을 단언하는 테스트를 추가한다.

5. **`page.tsx`의 `?? []` (r1 #4 이월)** — `app/w/[workspaceId]/page.tsx:160,161,189`. 목록 세 쿼리의 `error`를 검사하지 않아 조회 실패가 빈 상태로 위장된다. 같은 파일 `:151-155`가 `chunksResult`에 대해서는 정확히 이 위험을 ⚠️ 주석으로 적어 두고 다르게 처리한다. 이번에도 `page.tsx`는 diff에 없으므로 선재 결함으로 이월한다.

## 판정 근거

테넌트 경계는 이번 라운드에서도 어디도 움직이지 않았다. `supabase`·`apps/api`·`apps/worker` 변경이 0행이고, 상한은 여전히 순수 클라이언트 `slice`이며, 데이터를 공급하는 서버 컴포넌트는 손대지 않은 채 요청자 세션 + 네 쿼리 전부에 `workspace_id` 명시 필터를 유지한다. `service_role`은 등장하지 않는다. A·B·C·E 전 항목이 해당 없음이고, D는 이 diff가 닿지 않는다. r1 대비 오히려 나아진 부분도 있다 — 검증 상태의 **색** 판정까지 `lib/verification-label.ts`로 들어와 단일 진실 공급원의 범위가 라벨·술어·색 셋으로 넓어졌고, 순서 등가성을 배타성으로 증명한 결과 통합 과정에서 판정이 바뀐 입력은 존재하지 않는다.

그럼에도 `pass`를 주지 않는 이유는 r1 지적 3번이 **절반만 닫혔는데 닫혔다고 보고됐기** 때문이다. `backlog-vocabulary-unification`은 목적지 명칭을 훌륭하게 통일하고 계약까지 정본에 남겼지만, r1이 같은 항목에서 함께 요구한 탈출구 컨트롤 라벨 비대칭(`전체 보기` vs `보완하기`)은 코드에도 그 change의 어느 문서에도 반영되지 않았다. 이 브랜치가 도입한 변경이고, 하필 그 링크 뒤에 숨는 항목이 두 배가 된 커밋에서 일어났으며, 어떤 테스트도 라벨을 단언하지 않아 조용히 유지된다 — 이 리뷰가 보는 종류의 결함이다. 함께 커밋될 위치에 놓인 인증 없는 정적 HTML 4개(조치 2번)도 아무 change의 Impact에 없어 같은 방식으로 조용히 실린다.

두 건 모두 국소적 수정으로 해결되고 테넌트 경계나 데이터 무결성을 건드리지 않으므로 `blocked`이 아니라 `needs_fix`다. 조치 1·2를 처리하면 r3에서 `pass`가 예상된다.
