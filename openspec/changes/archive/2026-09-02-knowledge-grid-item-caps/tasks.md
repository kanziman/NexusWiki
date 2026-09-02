## 1. 노출 상한 조정

- [x] 1.1 `apps/dashboard/components/KnowledgeGrid.tsx`의 `MAX_WIKI_PAGES`를 5로, `MAX_BACKLOG_ITEMS`를 4로 낮춘다. 정렬 기준과 필터 동작, 각 행이 보여 주는 정보는 바꾸지 않는다.
  - Given: 워크스페이스에 상한을 넘는 위키 문서와 백로그 항목이 있다
  - When: 멤버가 홈을 연다
  - Then: 좌측은 최대 5행, 우측은 최대 4행만 렌더링된다
- [x] 1.2 두 섹션이 각각 전용 화면(`/wiki`, `/backlog`)으로 가는 링크를 계속 노출하는지 확인한다. 상한을 넘는 항목이 도달 불가능해지면 안 된다.
  - Given: 상한을 넘는 항목이 있다
  - When: 멤버가 섹션 헤더의 링크를 누른다
  - Then: 해당 전용 화면으로 이동해 나머지 항목에 도달할 수 있다

## 2. 테스트

- [x] 2.1 `apps/dashboard/tests/KnowledgeGrid.test.tsx`의 상한 단언을 5/4로 맞추고, **테스트 제목의 "최대 10개 · 최대 8개" 문구도 함께 고친다**. 제목과 단언이 어긋나면 다음 사람이 무엇이 계약인지 알 수 없다.
  - Given: 상한이 5/4로 바뀌었다
  - When: 해당 테스트를 실행한다
  - Then: 제목과 단언이 같은 수를 말하며 통과한다

## 3. 검증 및 스펙 아카이브

- [x] 3.1 `pnpm --dir apps/dashboard test`, `typecheck`, `lint`와 `openspec validate knowledge-grid-item-caps --strict`를 새로 실행한다.
  - Given: 구현 task가 완료되었다
  - When: 필수 검증을 실행한다
  - Then: skip이나 실패를 성공으로 오인하지 않는다
- [x] 3.2 delta spec을 정본에 동기화하고 strict specs validation 후 change를 아카이브한다.
  - Given: 구현과 검증이 완료되었다
  - When: OpenSpec 동기화·아카이브 절차를 실행한다
  - Then: `workspace-home-dashboard` 정본의 상한이 5/4로 갱신된다
