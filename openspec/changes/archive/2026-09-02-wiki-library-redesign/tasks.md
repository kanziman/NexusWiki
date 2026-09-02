## 1. Bento Header와 메트릭 개편

- [x] 1.1 위키 인덱스 조회에 `sources`를 포함해 행별 인용 수를 계산할 수 있게 하고, 로드된 페이지에서 검증률과 카테고리별 문서 수를 산출한다. 조회는 요청자 세션만 사용한다.
  - Given: 워크스페이스에 여러 카테고리의 위키 문서가 있다
  - When: 멤버가 위키 라이브러리를 연다
  - Then: 전체 수·검증률·카테고리별 수가 로드된 워크스페이스 페이지와 일치한다
- [x] 1.2 `위키 라이브러리` 타이틀과 총 문서 수, 지식 건강 벤토(검증률과 카테고리 퀵 탭)를 구성한다. `data-od-id="wiki-library-header"`는 유지한다.
  - Given: 라이브러리에 문서가 있다
  - When: 헤더가 렌더링된다
  - Then: 타이틀이 위키 라이브러리이고 벤토에서 카테고리를 고르면 해당 필터가 활성화된다

## 2. 필터 및 검색 툴바

- [x] 2.1 카테고리 칩에 문서 수 카운트를 붙이고, `entities` 라벨을 홈 `CATEGORY_LABELS`의 `엔티티`와 같게 맞춘다. `/` 키 검색 포커스는 추가하지 않는다.
  - Given: 개념·엔티티·가이드·맵 문서가 섞여 있다
  - When: 멤버가 카테고리 칩 또는 검색어를 사용한다
  - Then: 칩에 개수가 보이고 필터·검색 결과가 로드된 워크스페이스 페이지만 남는다

## 3. 문서 행 Card-Row

- [x] 3.1 각 문서 행을 카드 표면으로 바꾸고, 카테고리·검증·인용 메타를 제목 위에 두며, 정제된 발췌문에 2줄 말줄임과 가독성 폭 제한을 적용한다. `data-od-id="wiki-library-list"`와 행 링크·삭제 게이트(`isOwner`)는 유지한다.
  - Given: 마크다운과 WikiLink가 있는 문서가 와이드 뷰포트에 렌더링된다
  - When: 멤버가 목록을 본다
  - Then: 발췌는 정제된 평문이고 두 줄을 넘기지 않으며 상세 라우트 링크가 유지된다

## 4. 플로팅 일괄 액션 바

- [x] 4.1 현재 페이지 전체 선택은 리스트 위 서브 컨트롤 바에 남기고, 1개 이상 선택 시 일괄 검증·발행·선택 해제를 하단 플로팅 바로 옮긴다. `select-all-checkbox`, `bulk-verify-btn`, `bulk-publish-btn`과 `canVerify` 게이트를 유지한다.
  - Given: `canVerify=true`인 멤버가 문서를 선택한다
  - When: 플로팅 바가 나타난다
  - Then: 목록 높이가 밀리지 않고 기존 일괄 검증·발행 동작과 선택 해제가 그대로 동작한다

## 5. 테스트 및 접근성

- [x] 5.1 `apps/dashboard/tests/WikiLibrary.test.tsx:60`의 `h1` `"위키"` 단언을 새 타이틀과 맞게 수정하고, 검색·카테고리·빈 상태·정제 발췌 단언이 카드 행·카운트 칩과 충돌하지 않는지 고친다.
  - Given: 라이브러리 타이틀과 카테고리 라벨이 갱신되었다
  - When: `WikiLibrary.test.tsx`를 실행한다
  - Then: 빈 상태 프레임, 검색, 카테고리 필터, 정제 발췌 계약이 통과한다
- [x] 5.2 `apps/dashboard/tests/WikiBulkActions.test.tsx`가 플로팅 바 이후에도 선택·일괄 검증·일괄 발행·권한 게이트를 통과하도록 맞춘다.
  - Given: 일괄 액션이 플로팅 바로 옮겨졌다
  - When: `WikiBulkActions.test.tsx`를 실행한다
  - Then: `canVerify=false`에서는 선택 UI가 없고, 선택 시 기존 testid로 일괄 동작이 검증된다

## 6. 검증 및 스펙 아카이브

- [x] 6.1 `pnpm test`, `pnpm typecheck`, `pnpm lint`와 `openspec validate wiki-library-redesign --strict`를 새로 실행한다.
  - Given: 구현 task가 완료되었다
  - When: 필수 검증을 실행한다
  - Then: skip이나 실패를 성공으로 오인하지 않는다
- [x] 6.2 delta spec을 정본에 동기화하고 strict specs validation 후 change를 아카이브한다.
  - Given: 구현과 검증이 완료되었다
  - When: OpenSpec 동기화·아카이브 절차를 실행한다
  - Then: `wiki-library-navigation` 정본이 이 change의 라이브러리 헤더·카드 행·플로팅 일괄 바 계약을 보존한다
