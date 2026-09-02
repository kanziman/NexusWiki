# Tenant Isolation 리뷰 — knowledge-grid-item-caps + backlog-vocabulary-unification r3

- 판정: pass
- 대상: `git diff origin/main` (working tree, base `b274d46` — HEAD == merge-base라 변경분 전부 미커밋 상태)
- 일시: 2026-09-02T14:40:32Z

r2와 동일하게 **두 change를 함께** 다룬다. 브랜치 `feat/knowledge-grid-design-polish`에 다음 두 건이 같이 실려 있다.

- `openspec/changes/archive/2026-09-02-knowledge-grid-item-caps/`
- `openspec/changes/archive/2026-09-02-backlog-vocabulary-unification/`

검사 범위(16파일, +323 −161). r2 대비 늘어난 4파일이 이번 라운드의 조치분이다.

| 파일 | 증감 | r2 이후 성격 |
| --- | --- | --- |
| `.gitignore` | +7 −0 | **신규** — r2 조치 2번 |
| `apps/dashboard/components/KnowledgeGrid.tsx` | +107 −70 | 탈출구 라벨 `보완하기` → `전체 보기` |
| `apps/dashboard/components/PreviewWorkspace.tsx` | +91 −56 | 동일 |
| `apps/dashboard/app/w/[workspaceId]/loading.tsx` | +1 −1 | **신규** — `aria-label` 정본 명칭 |
| `apps/dashboard/components/BacklogList.tsx` | +4 −4 | 내부 접근성 이름 3곳 정렬 |
| `apps/dashboard/tests/KnowledgeGrid.test.tsx` | +35 −7 | 라벨·섹션 제목 단언 추가 |
| `apps/dashboard/tests/WorkspaceShell.test.tsx` | +20 −1 | **신규** — 브레드크럼 회귀 테스트 |
| `apps/dashboard/tests/BacklogList.test.tsx` | +12 −2 | **신규** — `h1` 회귀 테스트 |
| `apps/dashboard/tests/WorkspaceSidebar.test.tsx` | +6 −3 | r2에서 확인됨 |
| 나머지 7파일 (`WikiLibrary.tsx` · `WorkspaceShell.tsx` · `WorkspaceSidebar.tsx` · `verification-label.ts` · 스펙 2건 · 디자인 문서 1건) | | r2 검사분에서 무변경 |

`git diff origin/main --name-only -- supabase apps/api apps/worker` = **0행**. 마이그레이션 · RLS · API · 워커 변경이 이번에도 없음을 직접 확인했다.

## r2 지적 해소 여부

| r2 # | 지적 | 상태 | 근거 |
| --- | --- | --- | --- |
| 1 | 탈출구 라벨 비대칭 (보통) | **해소** | 아래 §1 |
| 2 | `public/*-preview.html` 미추적·미무시 (보통) | **해소** | 아래 §2 |
| 3 | 목적지 명칭 계약의 테스트 커버리지 (낮음, 관찰) | **대부분 해소** | 아래 §3. 브레드크럼·`h1`·홈 요약 섹션이 커버됐다. `/preview` 표면만 남았다 |
| 4 | `verificationToneClass`에 `now` 없음 (낮음, 관찰) | 미해소 | `lib/verification-label.ts:113` — 시그니처 그대로. 판정에 반영하지 않는다(§관찰 2) |
| 5 | `page.tsx`의 `?? []` (선재, 이월) | **미해소(합의된 이월)** | §이월 기록 |

### §1 — 탈출구 라벨 통일 실측

`apps/dashboard` 전체(`*.ts` · `*.tsx`, 소스·테스트 포함)에서 `보완하기` 검색 결과 **0건**.

| 표면 | 파일:줄 | 라벨 | 접근성 이름 |
| --- | --- | --- | --- |
| 홈 · 위키 열 | `KnowledgeGrid.tsx:101` | `전체 보기` | `전체 보기` |
| 홈 · 지식 공백 열 | `KnowledgeGrid.tsx:197` | `전체 보기` | `전체 보기` |
| 미리보기 · 위키 열 | `PreviewWorkspace.tsx:269` | `전체 보기` | `전체 보기` |
| 미리보기 · 지식 공백 열 | `PreviewWorkspace.tsx:324` | `전체 보기` | `전체 보기` |

네 곳 모두 화살표를 `<span aria-hidden="true">→</span>`로 분리했으므로 접근성 이름이 `전체 보기`로 깔끔하게 떨어진다. 장식 문자가 접근성 이름에 섞이지 않는다.

⚠️ 이 통일로 홈 한 화면에 접근성 이름이 같은 링크가 둘 생긴다. 다만 이것은 **`origin/main`의 원래 상태로 되돌아간 것**이다 — `git diff`에서 두 섹션 모두 `- 전체 보기 →`가 제거된 것을 확인했으므로, 이번 브랜치가 새로 만든 상태가 아니다. §관찰 1에 기록만 남긴다.

### §2 — `.gitignore` 규칙이 4개 파일을 전부 잡는지 직접 확인

규칙: `.gitignore:51` `apps/dashboard/public/*-preview.html` (앞에 5줄 ⚠️ 주석 — 미들웨어 matcher가 `public/`를 지나지 않는다는 사유와 대안 위치 `docs/design-systems/` 명시).

`git check-ignore -v`로 `apps/dashboard/public/` 아래 전 파일을 하나씩 돌린 결과:

| 파일 | 결과 |
| --- | --- |
| `backlog-preview.html` | `.gitignore:51`에 걸림 ✓ |
| `redesign-preview.html` | `.gitignore:51`에 걸림 ✓ |
| `sources-preview.html` | `.gitignore:51`에 걸림 ✓ |
| `wiki-library-preview.html` | `.gitignore:51`에 걸림 ✓ |
| `nexuswiki-login-knowledge-landscape-bright.png` | 무시 안 됨 (의도대로 — 실제 사용 에셋) |
| `nexuswiki-mark.png` | 무시 안 됨 (의도대로) |

r2가 지목한 4개가 **전부** 잡히고, 실제로 필요한 에셋 2개는 영향받지 않는다. `git status --porcelain --untracked-files=all`에서도 4개 HTML이 사라졌다(r2 시점에는 `??`로 떴다).

또한 **이미 추적 중인 파일은 `.gitignore`가 무력하다**는 함정이 걸리지 않는지도 확인했다 — `git ls-files apps/dashboard/public/`와 `git ls-tree -r origin/main -- apps/dashboard/public/` 둘 다 PNG 2개만 반환한다. 4개 HTML은 인덱스에도 `main`에도 없으므로 무시 규칙만으로 충분하다.

규칙의 앵커링도 맞다. 패턴에 `/`가 포함되면 gitignore 파일 위치 기준으로 앵커되고, 이 규칙은 저장소 루트 `.gitignore`에 있으므로 `apps/dashboard/public/`에만 적용된다 — 다른 워크스페이스의 동명 파일을 잘못 잡지 않는다.

### §3 — 추가된 테스트가 실제로 회귀를 잡는지 (변이 검증)

"통과만 시키는 형태"가 아닌지 확인하려고, 단언 대상 5곳을 하나씩 옛 상태로 되돌려(변이) 해당 테스트가 실제로 **깨지는지** 실측했다. 각 변이 후 백업본에서 복원했고, 마지막에 `shasum`으로 4개 파일이 변이 전과 **바이트 단위로 동일**함을 확인했다(작업 트리에 잔여 변경 없음).

| 변이 | 되돌린 내용 | 결과 |
| --- | --- | --- |
| M1 | `KnowledgeGrid.tsx:197` `전체 보기` → `보완하기` | `KnowledgeGrid.test.tsx` 1 failed ✓ |
| M2 | `KnowledgeGrid.tsx:186` 섹션 제목 → `미완성 백로그` | `KnowledgeGrid.test.tsx` 1 failed ✓ |
| M3 | `WorkspaceShell.tsx:31` 브레드크럼 → `미완성 백로그` | `WorkspaceShell.test.tsx` 1 failed ✓ |
| M4 | `BacklogList.tsx:72` `h1` → `미완성 백로그` | `BacklogList.test.tsx` 1 failed ✓ |
| M5 | `WorkspaceSidebar.tsx:350` **보이는 라벨만** → `미완성 백로그` (`aria-label`은 `지식 공백` 유지) | `WorkspaceSidebar.test.tsx` 1 failed ✓ |

다섯 변이 전부 잡힌다. 특히 M5는 r2가 근거로 든 "`aria-label`이 접근성 이름을 덮으므로 `getByRole`만으로는 보이는 라벨 회귀를 못 잡는다"를 실제로 검증한 것이다 — `toHaveTextContent`가 따로 있기 때문에 한쪽만 되돌려도 반드시 실패한다.

새 테스트의 구조도 확인했다. `WorkspaceShell.test.tsx`는 `vi.hoisted`로 `pathnameRef`를 만들어 `usePathname` 모킹을 테스트마다 바꾸고, `beforeEach`(`:38-42`)에서 `/w/ws-1`로 되돌린다 — 새 테스트가 다른 테스트의 pathname 가정을 오염시키지 않는다. 실제로 기존 7개 테스트가 그대로 통과한다.

`KnowledgeGrid.test.tsx:196-201`의 `not.toHaveTextContent("미완성 백로그")` 음성 단언도 유효하다. 현재 섹션 제목 `지식 공백 (작성 대기 백로그)`는 `미완성 백로그`를 부분 문자열로 포함하지 않으므로 항상 참인 단언이 아니고, M2에서 실제로 깨졌다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 해당 없음 | 이 diff에 데이터 접근 코드가 없다. 데이터 공급원 `app/w/[workspaceId]/page.tsx:120`은 `@/lib/supabase/server`의 요청자 세션 `createClient()`를 쓰며 이번 diff에 **포함되지 않는다**(`git diff --name-only`에 `page.tsx` 0건). `apps/dashboard` 전체에서 `service_client`·`SERVICE_ROLE` 사용 0건 — 유일한 매치는 `app/bookmark-actions.ts:8`의 "service_client는 쓰지 않는다"는 주석이다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음. `supabase/migrations` 무변경 |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | SQL 변경 0행. `/preview` 경로는 DB를 읽지 않고 `lib/preview-data.ts` 정적 픽스처만 쓴다. 오히려 이번 라운드는 anon 노출면을 **줄였다** — `.gitignore` 규칙이 미들웨어 게이트 밖(`public/`)으로 나갈 뻔한 정적 HTML 4개를 막았다(§2) |
| A-4 | service_role 코드의 workspace_id 필터 | 해당 없음 | 워커 변경 0행 |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 쓰기 경로 없음. 변경된 컴포넌트 전부 읽기 전용 렌더 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 동일 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 잡 핸들러 변경 없음 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 없음 |
| D-10 | hnsw.iterative_scan | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 색인/질의 토크나이저 일치 | 해당 없음 | 검색 경로 변경 없음 |
| D-12 | search_tsv 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음. `KnowledgeGrid.tsx:150`의 `인용 원문 N개`는 `citation_count` 표시일 뿐 컨텍스트 조립 경로가 아니다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음 |
| 확인 1 | r2 지적 2건 해소 | **통과** | §1 · §2. `.gitignore` 규칙이 4개 파일 전부를 잡는 것을 `git check-ignore -v`로 파일별 실측 |
| 확인 2 | 새 불일치 없음 (`aria-label` ↔ 보이는 라벨) | **통과** | 아래 별도 표 |
| 확인 3 | 새 테스트의 회귀 포착력 | **통과** | §3 — 변이 5건 전부 포착. 파일 복원 후 `shasum` 일치 확인 |
| 확인 4-a | 요청자 세션 유지 | **통과** | `page.tsx:6` import + `:120` `await createClient()` — `@/lib/supabase/server`. 이번 diff에 없음 |
| 확인 4-b | `workspace_id` 범위 유지 | **통과** | 네 쿼리 전부 `.eq("workspace_id", workspaceId)`(`page.tsx:130,143,148,158`). 이번 diff에 없음 |
| 확인 4-c | `verification-label.ts` 단일 진실 공급원 | **통과** | `verificationToneClass`가 `lib/verification-label.ts:112-118` 한 곳에만 존재하고 `WikiLibrary.tsx`·`KnowledgeGrid.tsx`가 같은 함수를 import한다. r2 이후 이 파일들은 변경되지 않았다 |
| 확인 4-d | 색 판정 중앙화 | **통과** | 위와 동일. 인라인 삼항 색 판정 0건 |
| 확인 4-e | 상한의 클라이언트 `slice` 성격 | **통과** | `MAX_WIKI_PAGES = 5` · `MAX_BACKLOG_ITEMS = 4`(`KnowledgeGrid.tsx:60-61`)는 서버가 이미 워크스페이스 범위로 조회한 배열을 자를 뿐이다. 데이터 경계 무변경 |
| 검증 실행 | 테스트 | **통과** | `vitest run` (KnowledgeGrid · BacklogList · WorkspaceShell · WorkspaceSidebar · PreviewWorkspace · workspace-home · verification-label) → **55 pass / 0 fail** (r2의 46 → 회귀 테스트 추가분 반영) |
| 검증 실행 | 타입 | **통과** | `tsc --noEmit` → `No errors found` |
| 검증 실행 | lint | **통과** | `next lint` → Errors 0 / Warnings 0 |
| 검증 실행 | 스펙 | **통과** | `openspec validate --specs --strict` → 34 passed / 0 failed |

### 확인 2 상세 — `aria-label` ↔ 보이는 라벨 대조

이번 라운드가 접근성 이름을 4곳 건드렸으므로 전부 대조했다.

| 위치 | `aria-label` | 같은 요소의 보이는 텍스트 | 판정 |
| --- | --- | --- | --- |
| `WorkspaceSidebar.tsx:343` / `:350` | `지식 공백` | `지식 공백` | 일치 ✓ (M5가 회귀를 잡는다) |
| `loading.tsx:100` | `지식 공백 로딩 중` | (스켈레톤 — 보이는 텍스트 없음) | 충돌 불가 ✓. 정본 명칭으로 시작하므로 계약 부합. 같은 파일 `:74`의 좌열 `위키 문서 로딩 중`과 형태도 대칭 |
| `BacklogList.tsx:81` | `지식 공백 요약` | `2` / `미해결 백로그`, `3` / `영향받는 위키` | §관찰 3 (낮음) |
| `BacklogList.tsx:95` | `지식 공백 필터` | 탭 버튼 텍스트 | 충돌 없음 ✓ |
| `BacklogList.tsx:120` | `지식 공백 검색` | (input — placeholder만) | 충돌 없음 ✓ |

`aria-label`은 보이는 텍스트를 **덮는다**. 따라서 위험한 조합은 "같은 요소에 서로 다른 두 이름"인데, 그런 조합은 `WorkspaceSidebar` 한 곳뿐이고 거기서는 둘이 정확히 같다. 나머지는 컨테이너 이름이라 덮는 대상이 없다.

옛 명칭 잔존 여부도 다시 훑었다 — `apps/dashboard` 전체에서 `미완성 백로그` 매치는 **테스트의 음성 단언 2건뿐**(`WorkspaceShell.test.tsx:57`, `KnowledgeGrid.test.tsx:201`)이고 소스에는 0건이다.

## 조치가 필요한 항목

없다.

## 관찰 — 판정에 반영하지 않음

1. **홈 한 화면에 접근성 이름이 같은 링크가 둘** (심각도: 낮음, **선재**)
   - 위치: `KnowledgeGrid.tsx:98-103`(→ `/wiki`) · `:194-199`(→ `/backlog`), 미리보기 `PreviewWorkspace.tsx:266-271` · `:321-326`
   - 상황: 통일 결과 네 링크의 접근성 이름이 모두 `전체 보기`가 됐다. 목적지는 서로 다르다. 스크린리더의 링크 목록 모드에서는 `전체 보기`가 둘 나란히 들리고 어느 쪽이 위키인지 구분되지 않는다. 시각적으로는 각 섹션 헤더 옆에 있어 맥락이 분명하다.
   - 왜 지적이 아닌가: 두 가지다. (a) `origin/main`에서도 **양쪽 다** `전체 보기 →`였다 — `git diff`에서 두 섹션 모두 `- 전체 보기 →`가 제거된 것을 확인했다. 이번 브랜치는 중간에 한쪽을 `보완하기`로 갈랐다가 원상 복구한 것이며 새 회귀가 아니다. (b) 사용자가 명시적으로 `전체 보기` 통일을 결정했다.
   - 다만 맥락을 제공할 수 있었던 장치가 비어 있다는 점은 기록해 둔다. `KnowledgeGrid.tsx`의 두 `<section>`에는 `aria-label`도 `aria-labelledby`도 **없다**(이 파일의 `aria-label` 매치 0건). 접근성 이름 없는 `<section>`은 landmark region으로 노출되지 않으므로 AT가 참조할 맥락이 실제로 없다. 반면 같은 화면의 스켈레톤(`loading.tsx:74`·`:100`)은 두 열에 `aria-label`을 달고 있어 로딩 중이 실제 콘텐츠보다 구조가 풍부한 역전 상태다.
   - 조치(선택, 다음 change): 두 `<section>`의 `<h2>`에 `id`를 주고 `aria-labelledby`로 묶는다. 링크 이름은 그대로 두어도 region 안에서 구분된다. `dashboard-design-consistency`에 새로 들어온 `Assistive technology user hears a destination name` 시나리오에 실질적 강제력이 생긴다.

2. **`verificationToneClass`만 `now` 파라미터가 없다** (심각도: 낮음, r2 #4 유지)
   - 위치: `apps/dashboard/lib/verification-label.ts:112`
   - r2 판단 그대로다 — 세 술어가 쌍마다 배타이고 `Date.now()`가 단조 증가하므로 실무상 무해하지만, 시간을 고정한 테스트로 색 매핑을 검증할 수 없다. `verification-label.test.tsx`에 `verificationToneClass` 케이스가 0건인 이유다.
   - 조치(선택): 시그니처를 `(page, now = Date.now())`로 맞추고 내부 두 호출에 같은 `now`를 넘긴 뒤 네 상태의 토큰을 단언한다.

3. **`지식 공백 요약` region 안에서 지표 이름이 `미해결 백로그`다** (심각도: 낮음, 선재)
   - 위치: `BacklogList.tsx:81`(region 이름) ↔ `:84`(지표 라벨)
   - 스크린리더 사용자는 `지식 공백 요약` 영역에 들어가 `2 미해결 백로그`를 듣는다. 어휘가 한 영역 안에서 섞인다.
   - 왜 지적이 아닌가: `미해결 백로그`는 목적지 이름이 아니라 **지표 이름**이다. 새 계약이 열거하는 표면(내비게이션 · 브레드크럼 · 페이지 heading · 타 목적지의 요약 섹션) 어디에도 해당하지 않고, 이번 diff는 이 문자열을 건드리지 않았다(`main`과 동일). 같은 성격으로 `app/w/[workspaceId]/page.tsx:351`의 MetricCard 라벨 `작성 대기 지식 공백`도 `main`과 동일하며 정본 명칭을 포함한다.

4. **`/preview` 표면의 목적지 명칭은 여전히 테스트가 없고, 있는 단언은 방향이 뒤집혀 있다** (심각도: 낮음, r2 #3의 남은 부분)
   - `PreviewWorkspace.test.tsx:33`이 `/작성 대기 백로그/`, 즉 스펙상 **MAY인 괄호 보조 설명** 쪽을 단언한다. 누가 계약상 허용된 방식으로 괄호를 떼면 이 테스트가 깨지고, 반대로 앞머리 정본 명칭이 바뀌어도 통과한다.
   - 이번 라운드가 실제 화면 쪽(브레드크럼 · `h1` · 홈 요약 섹션 · LNB) 네 표면을 전부 커버했으므로 계약의 강제력은 확보됐다. `/preview`는 정적 픽스처 데모 화면이라 우선순위가 낮다.
   - 조치(선택): 단언을 `지식 공백`으로 바꾼다. 한 줄 수정이다.

5. **`.gitignore` 규칙이 `*-preview.html` 접미사에만 걸린다** (심각도: 낮음)
   - `apps/dashboard/public/mockup.html`이나 `preview.html`처럼 이름을 조금만 달리하면 같은 함정에 다시 빠진다. 지금 있는 4개는 전부 잡히므로(§2) 현재 위험은 없고, 주석이 "커밋할 프로토타입은 `docs/design-systems/` 에 둔다"고 대안을 명시해 규칙보다 의도가 잘 전달된다.
   - 조치(선택): `apps/dashboard/public/*.html`로 넓힌다. `public/`에 정당하게 필요한 HTML은 현재 0개다.

## 이월 기록 — `page.tsx`의 `?? []` (r1 #4 → r2 #5 → r3)

- 위치: `apps/dashboard/app/w/[workspaceId]/page.tsx:161,162,190`
- 깨지는 것: `sourcesResult` · `pagesResult` · `linksResult` 세 목록 쿼리의 `error`를 검사하지 않고 `data ?? []`로 흡수한다. RLS 거부·네트워크 오류·쿼리 실패가 전부 **빈 배열**이 되어, 사용자에게는 "이 워크스페이스에 아무것도 없습니다"라는 정상 빈 상태로 보인다. 예외도 로그도 없다.
- 같은 파일 `:150-155`가 `chunksResult`에 대해서는 정확히 이 위험을 ⚠️ 주석과 함께 다르게 처리한다(오류 시 `null` → `인덱싱된 청크 —` 표시). 즉 저장소가 이미 옳은 패턴을 알고 있고, 세 곳만 그 패턴 밖에 있다.
- **이번 라운드에도 `page.tsx`는 diff에 없다**(`git diff --name-only`에 0건). 사용자와 합의한 대로 선재 결함으로 이월한다. 이 브랜치를 막는 사유가 아니다.
- 다음 담당자를 위한 메모: 세 곳을 `chunksResult`와 같은 형태로 맞추는 것은 독립적인 작은 change로 떼기 좋다. 이 브랜치가 홈 상한을 10/8 → 5/4로 낮춰 "적게 보이는 것"이 정상 상태가 됐으므로, 조회 실패를 빈 상태로 위장하는 결함의 발각 가능성은 오히려 조금 더 낮아졌다.

## 판정 근거

테넌트 경계는 세 라운드 내내 한 번도 움직이지 않았다. `supabase` · `apps/api` · `apps/worker` 변경이 0행이고, 상한은 여전히 서버가 이미 워크스페이스 범위로 조회한 배열에 대한 순수 클라이언트 `slice`이며, 데이터를 공급하는 서버 컴포넌트는 손대지 않은 채 요청자 세션과 네 쿼리 전부의 `workspace_id` 명시 필터를 유지한다. `service_role`은 등장하지 않는다. A · B · C · E 전 항목이 해당 없음이고 D는 이 diff가 닿지 않는다.

r2가 `pass`를 보류한 두 사유는 **둘 다 실측으로 닫혔다.** 탈출구 라벨은 `보완하기`가 저장소에서 0건이 됐고 네 표면 모두 `전체 보기`로 수렴했으며, 장식 화살표를 `aria-hidden`으로 분리해 접근성 이름까지 깨끗하다. 인증 게이트 밖 정적 HTML 4개는 `git check-ignore -v` 파일별 확인으로 전부 무시되고, 인덱스에도 `main`에도 없어 무시 규칙만으로 충분함을 함께 확인했다 — 규칙에 붙은 ⚠️ 주석이 "미들웨어 matcher가 `public/`를 지나지 않는다"는 사유를 남겨 다음 사람이 같은 실수를 반복하지 않게 한다.

r2가 `needs_fix`의 결정적 근거로 들었던 것은 위반 자체보다 **"어떤 테스트도 라벨을 단언하지 않아 조용히 유지된다"**는 점이었다. 이번 라운드는 그 구멍을 정확히 메웠고, 나는 그것을 믿지 않고 변이 5건으로 확인했다 — 라벨·섹션 제목·브레드크럼·`h1`·(보이는 라벨만 되돌린) LNB를 각각 옛 상태로 돌렸을 때 다섯 모두 해당 테스트가 실패했다. 통과만 시키는 단언이 아니다. 검증 4종(테스트 55 pass / typecheck / lint / `openspec validate --strict`)도 새로 돌려 전부 통과했다.

남은 관찰 5건은 전부 낮음이며, 그중 3건(1 · 3 · 이월)은 `origin/main`과 동일한 선재 상태다. 어느 것도 테넌트 경계나 데이터 무결성을 건드리지 않고, 이 브랜치가 새로 만든 것도 아니다. 막을 사유가 없다 — `pass`.
