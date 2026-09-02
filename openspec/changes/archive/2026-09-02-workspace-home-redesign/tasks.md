## 1. 기반 데이터 연동 및 헤더/통계/Ask 개편

- [x] 1.1 홈 서버 페이지에서 검증률과 인용 빈도 상위 추천 칩을 산출하고, 벤토 2번 카드용 `source_chunks` 카운트를 요청자 세션으로 추가한다. 칩은 `wiki_pages.sources` 배열 길이 기준이며 조회수 컬럼은 쓰지 않는다.
  - Given: 활성 워크스페이스에 원문·위키·미해결 링크가 있다
  - When: 멤버가 홈을 연다
  - Then: 검증률·청크 수·상위 인용 위키 제목이 같은 요청의 워크스페이스 범위 데이터에서만 계산된다
- [x] 1.2 히어로 헤더에 지식 완결도 뱃지와 원문·위키 수를 문장으로 조합한 서브타이틀을 적용하고, 4분할 통계를 벤토 메트릭으로 교체한다. 최종 업데이트는 서버 렌더 스냅샷이며 "라이브" 표현을 쓰지 않는다. 홈 `h1`은 `"홈 대시보드"`를 유지한다. 워크스페이스명은 LNB `WorkspaceSwitcher`가 이미 노출하므로 `h1`에 넣지 않고, `workspaces` 조회도 추가하지 않는다.
  - Given: 멤버가 홈을 본다
  - When: 히어로와 메트릭이 렌더링된다
  - Then: 지식 완결도와 네 메트릭이 보이고, 실시간 구독을 암시하지 않는다
- [x] 1.3 `AskHero`에서 `DEFAULT_CHIPS`를 제거하고 상위에서 주입한 `defaultChips`만 렌더링하며, 포커스 시 앰비언트 글로우와 기존 `⌘ + Enter` 제출을 유지한다. 단축키 힌트 뱃지는 신설하지 않는다.
  - Given: 홈이 워크스페이스 위키 제목으로 칩을 넘기거나, 위키가 없어 빈 배열을 넘긴다
  - When: Ask 히어로가 렌더링된다
  - Then: 하드코딩된 엔지니어링 도메인 칩이 없고, 칩이 있으면 클릭 시 입력창을 채운다

## 2. 6:4 듀얼 지식 그리드 리팩토링

- [x] 2.1 `docs/design-systems/v2/nexuswiki-design-system.css`의 `:root`에 `--warning` 토큰을 추가한다. 레거시 `--color-warning-text`를 재사용하지 않는다. 토큰 선언에는 자명하지 않은 선택에 "안 그러면 뭐가 깨지는지" 주석을 단다 — `--good`/`--danger`만 있으면 경고·주의 상태가 하드코딩 앰버나 레거시 토큰으로 흩어져 표준이 깨진다.
  - Given: v2 `:root`에 `--good`과 `--danger`만 있고 경고 토큰이 없다
  - When: `--warning`을 `:root`에 추가한다
  - Then: 백로그 앰버 보더와 이후 경고·주의 상태가 같은 v2 토큰을 쓸 수 있고, 선언 옆에 재사용하지 않으면 깨지는 이유가 주석으로 남아 있다
- [x] 2.2 `KnowledgeGrid` 데스크톱 레이아웃을 위키 쪽이 더 넓은 비대칭(`grid-cols-[1.4fr_1fr]`)으로 바꾸고, 좌측 위키 행에 카테고리·검증·인용 뱃지를 통합한다. 카테고리 라벨은 기존 `CATEGORY_LABELS`를 유지한다.
  - Given: 워크스페이스에 컴파일된 위키와 미해결 링크가 있다
  - When: 홈 지식 그리드가 렌더링된다
  - Then: 위키는 최대 10행, 백로그는 최대 8행이며 카테고리·검증·인용 정보가 위키 행에 보인다
- [x] 2.3 우측 백로그 행에 기존 프리필 경로(`/sources?prefillTitle=...&tab=text`)로 가는 인라인 소스 연결 CTA를 둔다. 버튼 라벨은 `소스 추가`를 유지하고, 앰버 보더는 v2 `:root`의 `--warning` 토큰을 쓴다.
  - Given: 홈 백로그 행이 있다
  - When: 멤버가 행의 소스 연결 액션을 활성화한다
  - Then: 해당 제목이 프리필된 텍스트 탭 원문 수집 경로로 이동한다

## 3. 테스트 스위트

- [x] 3.1 `apps/dashboard/tests/AskHero.test.tsx:37`의 하드코딩 칩 문자열 `"PostgreSQL RLS 격리 규칙 요약"` 단언을 `DEFAULT_CHIPS` 제거와 맞게 수정한다. 같은 문자열은 이 파일의 렌더 단언과 클릭 대상에도 있다.
  - Given: `AskHero`가 기본 칩 상수 없이 렌더링된다
  - When: 해당 테스트를 실행한다
  - Then: 하드코딩 엔지니어링 칩 문자열을 전제로 하지 않고도 칩 클릭·입력 채움 계약이 검증된다
- [x] 3.2 `tests/AskHero.test.tsx`, `tests/KnowledgeGrid.test.tsx`, `tests/workspace-home.test.tsx`의 나머지 단언을 벤토 메트릭·동적 칩·비대칭 그리드·소스 연결 CTA에 맞게 고친 뒤 실행한다.
  - Given: Phase 1·2 구현이 반영되어 있다
  - When: 세 테스트 파일을 실행한다
  - Then: 빈 상태, 카테고리 필터, 10/8 상한, 칩 제출 계약이 통과한다

## 4. 검증 및 스펙 아카이브

- [x] 4.1 `pnpm test`, `pnpm typecheck`, `pnpm lint`와 `openspec validate workspace-home-redesign --strict`를 새로 실행한다.
  - Given: 구현 task가 완료되었다
  - When: 필수 검증을 실행한다
  - Then: skip이나 실패를 성공으로 오인하지 않는다
- [x] 4.2 delta spec을 정본에 동기화하고 strict specs validation 후 change를 아카이브한다.
  - Given: 구현과 검증이 완료되었다
  - When: OpenSpec 동기화·아카이브 절차를 실행한다
  - Then: `workspace-home-dashboard` 정본이 이 change의 히어로·칩·그리드 계약을 보존한다

## 5. 레이아웃 파급 정합

- [x] 5.1 `apps/dashboard/app/w/[workspaceId]/loading.tsx` 스켈레톤을 홈 본문의 벤토 메트릭 4칸과 비대칭 6:4 `.sections` 그리드에 맞춘다. 옛 `.stats` 뼈대를 쓰지 않는다. 스켈레톤이 실제 콘텐츠와 같은 골격이어야 로딩→렌더 전환에서 레이아웃이 튀지 않는다는 이유를 주석으로 남긴다.
  - Given: 홈 본문이 벤토 메트릭과 비대칭 지식 그리드로 렌더링된다
  - When: 워크스페이스 홈 로딩 스켈레톤이 표시된다
  - Then: 스켈레톤이 벤토 4칸과 `.sections` 6:4 그리드 골격을 쓰고, 옛 `.stats` 줄을 쓰지 않는다
- [x] 5.2 `PreviewWorkspace`가 홈과 같은 `.sections` 클래스를 계속 쓰는지 확인하고, 미리보기가 새 비율에서 깨지지 않으면 공유가 의도된 것임을 주석으로 남긴다. 클래스를 포크하지 않는다.
  - Given: 홈 지식 그리드의 `.sections` 비율이 `1.4fr / 1fr`이다
  - When: 로컬 제품 미리보기 홈이 렌더링된다
  - Then: 미리보기도 같은 `.sections` 클래스를 쓰며, 공유를 유지한 이유가 주석으로 남아 있다
