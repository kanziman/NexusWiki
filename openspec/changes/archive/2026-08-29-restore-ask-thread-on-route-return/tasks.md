## 1. 첫 Ask 제출을 즉시 식별 가능한 진행 중 턴으로 만든다

- [x] 1.1 요청자 JWT와 RLS를 유지한 채 첫 제출·후속 제출에서 `streaming` 턴을 멱등 생성하고 같은 행을 최종 상태로 확정한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/95)
  - Given: 워크스페이스 멤버가 새 또는 기존 Ask 스레드에서 `client_turn_id`를 포함한 질문을 제출할 수 있다.
  - When: Ask API가 스트리밍을 시작하고 답변·인용 또는 근거 없음·오류 최종 상태를 결정한다.
  - Then: 초기 `meta`가 스레드 ID를 반환하고, 해당 질문은 진행 중 한 행으로 즉시 조회되며, 최종화 뒤에도 같은 `(thread_id, client_turn_id)` 행 하나만 존재하고 `done`은 그 확정 뒤에만 발행된다. 작성자·멤버십이 아닌 요청은 RLS와 HTTP 403으로 막힌다.
  - Verification: `uv run pytest apps/api/tests/test_ask_thread_history.py apps/api/tests/test_ask_thread_history_isolation.py -q`, `ruff check apps/api/src apps/api/tests`

## 2. 워크스페이스 라우트 왕복에서 원래 Ask 대화를 복원한다

- [x] 2.1 Ask의 초기 스레드 ID와 세션별 활성 스레드를 연결해 홈 대시보드 등을 거친 뒤에도 진행 중·완료 대화를 열고, 명시적 새 대화는 빈 상태로 유지한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/96)
  - Given: 슬라이스 1이 통과했고, 멤버가 Ask에서 첫 질문을 제출했거나 이미 진행 중·완료 스레드가 있다.
  - When: 멤버가 같은 워크스페이스의 홈 대시보드로 이동했다가 일반 Ask 진입점으로 돌아오거나, 명시적으로 새 대화를 시작한다.
  - Then: 일반 Ask 진입은 마지막 활성 스레드를 열어 진행 중 상태 또는 최종 답변·클릭 가능한 이중 인용을 보여 주고, 새 대화는 이전 스레드를 열지 않는다. 삭제되었거나 권한 없는 스레드 ID는 세션에서 제거된다.
  - Verification: `cd apps/dashboard && pnpm exec vitest run tests/AskConversation.test.tsx tests/AskThreadHistoryRestore.test.tsx tests/AskThreadSwitch.test.tsx tests/WorkspaceSidebar.test.tsx tests/WorkspaceShell.test.tsx`, `cd apps/dashboard && pnpm typecheck && pnpm lint`
