## Why

현재 위키 라이브러리(`apps/dashboard/components/WikiLibrary.tsx`)는 제목 `"위키"`와 2칸 통계, 작은 카테고리 칩, 가로로 길게 늘어지는 발췌문으로 구성되어 있어 문서의 건강 상태와 카테고리 분포를 한눈에 읽기 어렵고, 일괄 선택 바가 목록 리듬을 밀어낸다. 라이브러리를 읽기 폭이 제한된 카드형 서재로 바꿔, 검색·필터·검증 상태를 유지한 채 탐색 밀도와 일괄 작업의 방해를 줄인다.

근거: `docs/design-systems/wiki-library-redesign-plan.md` §1.

## What Changes

1. **Phase 1 — Bento Header와 메트릭**
   - 전체 검증률과 카테고리별 문서 수를 계산하고, `위키 라이브러리` 타이틀을 가진 에디토리얼 헤더와 지식 건강 벤토를 구성한다.
2. **Phase 2 — 필터 및 검색 툴바**
   - 카테고리 버튼에 개수 뱃지를 달고 검색 인풋 시각을 정돈한다. `/` 키 검색 포커스 단축키는 신설하지 않는다.
3. **Phase 3 — 문서 행 Card-Row**
   - 각 행을 마이크로 카드로 바꾸고 발췌문을 2줄·가독성 폭으로 제한한다. 카테고리·검증·인용 뱃지를 제목 위 메타 라인으로 모은다.
4. **Phase 4 — 플로팅 일괄 액션 바**
   - 1개 이상 선택 시 목록을 밀어내지 않는 하단 플로팅 바로 일괄 검증·발행·선택 해제를 제공한다. 기존 테스트 셀렉터와 `canVerify`/`isOwner` 게이트는 유지한다.
5. **Phase 5 — 테스트와 접근성**
   - `WikiLibrary`·`WikiBulkActions` 테스트, typecheck, lint를 통과시킨다. `AskHero.test.tsx`와 `workspace-home.test.tsx`의 홈 단언은 이 change의 범위가 아니다.

제품 API·스키마·RLS는 바꾸지 않는다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `wiki-library-navigation`: 라이브러리 헤더·카테고리 카운트·카드형 행·플로팅 일괄 선택 표면의 표시 계약을 갱신한다.

## Impact

- `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx`
- `apps/dashboard/components/WikiLibrary.tsx`
- `apps/dashboard/tests/WikiLibrary.test.tsx`
- `apps/dashboard/tests/WikiBulkActions.test.tsx`
- 검증 라벨 판정은 기존 `apps/dashboard/lib/verification-label.ts`를 재사용하며 이 파일을 고치지 않는다.

API, 워커, 마이그레이션, RLS 정책 변경 없음. 조회는 기존 요청자 세션만 사용한다.
