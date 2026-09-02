## Context

동기는 [`proposal.md`](proposal.md)의 Why를, 표시 계약은 [`specs/workspace-home-dashboard/spec.md`](specs/workspace-home-dashboard/spec.md)를 따른다. 근거 계획서는 `docs/design-systems/dashboard-redesign-plan.md`다.

현재 홈 서버 페이지는 `raw_sources`, `wiki_pages`, `wiki_links`만 요청자 세션으로 읽고 `workspaces`와 `source_chunks`는 읽지 않는다. `h1`은 `"홈 대시보드"`로 고정되어 있고, `AskHero`는 `DEFAULT_CHIPS`에 `"PostgreSQL RLS 격리 규칙 요약"` 등을 하드코딩한다. `⌘ + Enter` 제출은 `AskHero.tsx`의 `handleKeyDown`에 이미 있다. 백로그 행은 모달을 열고, 실제 원문 수집 동선은 `BacklogList.tsx`와 `BacklogDetailModal.tsx`가 쓰는 `/sources?prefillTitle=...&tab=text`다. LNB `WorkspaceSwitcher`는 이미 워크스페이스명을 보여 준다.

조회수 컬럼은 스키마에 없다. 홈 테스트 모의는 `.single()`에 `{ name: "내 워크스페이스" }`를 이미 돌려주지만, 페이지는 그 조회를 호출하지 않는다.

## Goals / Non-Goals

**Goals:**

- 홈의 히어로·메트릭·추천 칩·지식 그리드를 활성 워크스페이스의 실데이터로 채운다.
- 기존 요청자 JWT 조회와 `lib/verification-label.ts`의 검증 판정을 재사용한다.
- 백로그 CTA의 목적지를 이미 있는 원문 수집 프리필 경로로 유지한다.

**Non-Goals:**

- 단축키를 새로 만들지 않는다. `⌘ + Enter` 힌트 뱃지도 신설하지 않는다.
- realtime 구독과 "라이브" 류 표현을 쓰지 않는다.
- 조회수·초안 생성·위키 직접 작성 UI를 추가하지 않는다.
- API, 워커, 마이그레이션, RLS를 바꾸지 않는다.
- 다크 모드, `prefers-color-scheme`, Tailwind `dark:` 변형을 도입하지 않는다.

## Decisions

### D-1. 이 앱은 단일 테마다

`docs/design-systems/v2/nexuswiki-design-system.css`의 `:root`가 유일한 팔레트다. `prefers-color-scheme` 규칙과 `apps/dashboard`의 Tailwind `dark:` 변형은 쓰지 않는다. 색은 그 `:root`에 있는 토큰만 쓰고 hex를 새로 도입하지 않는다.

### D-2. 추천 칩은 서버에서 인용 빈도로 고른다

홈 `page.tsx`가 `wiki_pages.sources` 배열 길이로 상위 3~4개 제목을 고르고 `AskHero`에 `defaultChips`로 넘긴다. `AskHero` 안의 `DEFAULT_CHIPS`는 제거한다. 조회수 컬럼은 없으므로 쓰지 않는다. 클라이언트에서 위키 목록을 다시 가져와 칩을 만드는 안은 첫 페인트가 어긋나고 요청자 조회가 한 번 더 늘어나므로 채택하지 않는다.

### D-3. 청크 수는 소스 목록과 같은 조회 형태를 홈에 추가한다

벤토 2번 카드의 인덱싱된 청크 수는 `apps/dashboard/app/w/[workspaceId]/sources/page.tsx`가 `source_chunks`를 `workspace_id`로 읽는 패턴을 홈에서 재사용한다. 새 RPC나 집계 컬럼을 만들지 않는다. 사용자 경로이므로 `service_role`을 쓰지 않는다.

### D-4. 제출 단축키는 기존 `handleKeyDown`만 쓴다

`⌘ + Enter`는 이미 동작한다. 단축키 힌트 뱃지나 새 키 바인딩을 추가하지 않는다.

### D-5. 최종 업데이트는 서버 렌더 스냅샷이다

`formatTimeAgo(latestUpdated)`는 요청 시점 값이다. realtime 구독이 없으므로 펄스 뱃지나 "라이브" 카피를 붙이지 않는다.

### D-6. 백로그 CTA 목적지는 기존 프리필 경로다

초안 생성 기능은 코드베이스에 없다. 홈 백로그 행의 인라인 액션은 `/sources?prefillTitle=...&tab=text`로 보낸다. 버튼 라벨은 기존 제품 카피와 같이 `소스 추가`를 유지한다.

## Risks / Trade-offs

- [Risk] `AskHero.test.tsx`가 하드코딩 칩 문자열을 단언해 `DEFAULT_CHIPS` 제거와 충돌한다. → Phase 3에서 해당 단언을 새 계약에 맞게 고친 뒤에만 완료로 본다. 홈 `h1` `"홈 대시보드"` 단언은 유지하므로 `workspace-home.test.tsx:76`은 이 리스크에 넣지 않는다.
- [Risk] 백로그 앰버 보더에 대응하는 v2 토큰이 아직 `:root`에 없다. → `--warning`을 v2 `:root`에 추가한 뒤에만 보더를 그 토큰으로 연결한다. 레거시 `--color-warning-text`를 재사용하지 않는다.
- [Risk] 홈만 라벨을 바꾸면 백로그 목록·모달과 카피가 갈라진다. → 라벨을 기존 `소스 추가`로 유지해 화면 사이 카피가 갈라지지 않게 한다.
- [Risk] `source_chunks` 카운트가 큰 워크스페이스에서 홈 조회를 늘린다. → 기존 소스 목록과 같은 `workspace_id` 필터를 유지하고, 병목이 측정되면 별도 change에서 집계를 설계한다.

## Migration Plan

1. 대시보드 홈 컴포넌트와 테스트를 함께 배포한다. 데이터베이스 마이그레이션은 없다.
2. `pnpm test`, `pnpm typecheck`, `pnpm lint`, `openspec validate workspace-home-redesign --strict`로 회귀를 확인한다.
3. 문제가 있으면 이 change의 UI 커밋만 되돌린다. 데이터 롤백은 필요 없다.

## Resolved Questions

계획서가 미결로 남겼던 항목이다. 아래와 같이 확정한다.

1. **백로그 앰버 보더 토큰** (`dashboard-redesign-plan.md` §5)
   **결정:** 레거시 `--color-warning-text`를 재사용하지 않고, `docs/design-systems/v2/nexuswiki-design-system.css`의 `:root`에 `--warning` 토큰을 새로 추가한다.
   **이유:** 백로그 보더 한 곳이 아니라 앞으로의 경고·주의 상태 전반에서 표준으로 재사용하기 위해서다.
2. **백로그 버튼 라벨** (`dashboard-redesign-plan.md` §3.4)
   **결정:** 현행 라벨 `소스 추가`를 유지한다. 계획서가 제안한 `[원문 수집]`은 채택하지 않는다.
   **이유:** 기존 제품 전반의 카피 계약과 일관되어야 한다.
3. **워크스페이스명 `h1`과 LNB 중복** (`dashboard-redesign-plan.md` §3.1)
   **결정:** 홈 `h1`은 `"홈 대시보드"`를 유지한다. 워크스페이스명을 `h1`에 넣지 않는다.
   **이유:** `workspaces` 조회 쿼리를 새로 추가할 필요가 없고, LNB `WorkspaceSwitcher`가 이미 워크스페이스명을 노출하므로 화면 내 명칭이 중복된다.
