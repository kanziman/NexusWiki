## Why

현재 워크스페이스 홈(`apps/dashboard/app/w/[workspaceId]/page.tsx`)은 기능적으로 안정적이지만, 진입 시 워크스페이스의 정체성을 잡아 주는 시각 앵커가 없고 Ask 추천 칩과 플레이스홀더가 특정 엔지니어링 용어로 하드코딩되어 있으며, 4분할 통계와 대칭 목록이 지식의 건강 상태와 다음 행동을 읽기 어렵게 만든다. 홈을 워크스페이스 데이터에 적응하는 조용한 지식 커맨드 센터로 바꿔, 질문·위키 탐색·원문 수집이 같은 화면에서 맥락을 잃지 않게 한다.

근거: `docs/design-systems/dashboard-redesign-plan.md` §1.

## What Changes

1. **Phase 1 — 기반 데이터 연동 및 헤더/통계/Ask 개편**
   - 홈 서버 페이지에서 검증률과 인용 빈도 상위 추천 칩을 산출한다. 인용 빈도는 `wiki_pages.sources` 배열 길이다.
   - 히어로 헤더에 지식 완결도 뱃지를 두고, 4분할 통계를 벤토 메트릭으로 바꾼다. 원문 카드의 청크 수는 홈에 `source_chunks` 카운트 조회를 추가해 채운다.
   - `AskHero`의 하드코딩 `DEFAULT_CHIPS`를 제거하고, 상위에서 주입한 동적 칩과 앰비언트 글로우 입력을 쓴다.
2. **Phase 2 — 6:4 듀얼 지식 그리드**
   - `KnowledgeGrid`를 데스크톱에서 위키 쪽이 더 넓은 비대칭 그리드로 재구성한다.
   - 좌측 위키 행에 카테고리·검증·인용 뱃지를 통합하고, 우측 백로그 행에 원문 수집 동선(`/sources?prefillTitle=...&tab=text`)을 연결한다.
3. **Phase 3 — 테스트 스위트**
   - `AskHero.test.tsx`의 하드코딩 칩 단언을 새 계약에 맞게 고친다. 계획대로면 이 단언은 실패가 확정이다.

**BREAKING** (테스트 계약): `AskHero`의 기본 칩 문자열은 더 이상 고정값이 아니다. 제품 API·스키마·RLS는 바꾸지 않는다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `workspace-home-dashboard`: 홈 히어로·지식 건강 메트릭·Ask 추천 칩·비대칭 지식 그리드의 표시 계약을 워크스페이스 실데이터 기준으로 갱신한다.

## Impact

- `apps/dashboard/app/w/[workspaceId]/page.tsx`
- `apps/dashboard/components/AskHero.tsx`
- `apps/dashboard/components/KnowledgeGrid.tsx`
- `apps/dashboard/tests/AskHero.test.tsx`
- `apps/dashboard/tests/workspace-home.test.tsx`
- `apps/dashboard/tests/KnowledgeGrid.test.tsx`
- 청크 수 조회 패턴의 참고 구현: `apps/dashboard/app/w/[workspaceId]/sources/page.tsx` (이 파일을 고치지 않고 홈에서 같은 조회 형태를 재사용한다)
- `docs/design-systems/v2/nexuswiki-design-system.css` (`:root`에 `--warning` 토큰 추가)

API, 워커, 마이그레이션, RLS 정책 변경 없음. 조회는 기존 요청자 세션(`createClient()`)만 사용한다.
