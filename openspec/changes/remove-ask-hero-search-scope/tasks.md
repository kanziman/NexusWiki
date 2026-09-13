## 1. 홈 Ask 히어로에서 검색 범위 제거

- [x] 1.1 `AskHero`에서 검색 범위 메뉴·상태·`scope` 쿼리를 제거하고, 제출은 `q`만 `/ask`로 넘긴다. 홈 스켈레톤의 범위 자리도 없앤다.
  - Given: 멤버가 홈 Ask 히어로를 본다
  - When: 질문을 입력하고 제출한다
  - Then: 범위 선택 컨트롤이 없고, 이동 URL에 `scope`가 없으며 질문은 워크스페이스 전체 검색으로 시작된다
  - GitHub: https://github.com/kanziman/NexusWiki/issues/153

## 2. 프로토타입과 문서 동기화

- [x] 2.1 홈 프로토타입과 디자인 시스템 CSS에서 범위 컨트롤을 제거하고, `PRODUCT-INVARIANTS.md`·`workspace-home-prd.md`의 스코프 셀렉터 서술을 실제 동작에 맞춘다. 지식 그래프 이웃 표시 서술은 유지한다.
  - Given: 홈 프로토타입과 불변식 문서를 연다
  - When: Ask 히어로와 스코프 서술을 확인한다
  - Then: 검색 범위 선택기가 없고, 그래프 hop 시각화 설명은 남아 있다
  - GitHub: https://github.com/kanziman/NexusWiki/issues/154

## 3. 테스트와 검증

- [x] 3.1 `AskHero` 테스트에서 범위 메뉴 단언을 제거하고, 제출이 `q`만 넘기며 범위 컨트롤이 없음을 검증한다. `pnpm --dir apps/dashboard test` · `typecheck` · `lint`와 `openspec validate remove-ask-hero-search-scope --strict`를 새로 실행한다.
  - Given: 범위 UI를 제거했다
  - When: 관련 테스트와 strict validation을 실행한다
  - Then: 범위 컨트롤이 없다는 단언이 통과하고 skip이나 실패를 성공으로 오인하지 않는다
  - GitHub: https://github.com/kanziman/NexusWiki/issues/155
