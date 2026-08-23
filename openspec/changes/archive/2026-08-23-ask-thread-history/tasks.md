## 1. 완료된 내 대화를 다시 열면 이중 인용이 살아 있다

- [x] 1.1 첫 질문 완료 후 새로고침해도 작성자 소유 스레드가 남고, 저장된 위키·원문 마커가 클릭 가능하게 복원된다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/77)
  - Given: 워크스페이스 멤버가 Ask에서 질문을 제출할 수 있고, 발급 가능한 위키·원문 근거가 있다.
  - When: `/ask`에 `client_turn_id`를 실어 제출하고 서버가 citations를 조립한 뒤 영속화에 성공하며 SSE `done`을 보낸다. 작성자가 페이지를 새로고침하거나 대화 목록에서 그 스레드를 다시 연다.
  - Then: `0018_ask_history.sql`의 `ask_threads`/`ask_messages`에 작성자∩멤버십 RLS로 한 논리 턴이 남고, `done`은 그 커밋 이후에만 오며, 복원 경로는 `splitTextWithAnchors(text, resolved)`로 위키·원문 마커를 클릭 가능하게 렌더한다. 같은 워크스페이스의 다른 멤버와 `anon`에게는 목록·상세가 보이지 않고, USING 0행 쓰기는 HTTP 403이다. 동일 `(thread_id, client_turn_id)` 재전송은 행을 늘리지 않는다. `no-evidence`/`error` 턴은 placeholder 없이 해당 카드로 복원된다.
  - Verification: `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres -c "\d public.ask_threads"` 로 0018을 확인하고, `cd apps/api && uv run pytest tests/test_ask_thread_history.py tests/test_ask_thread_history_isolation.py -q`, `cd apps/dashboard && pnpm test -- --run tests/AskThreadHistoryRestore.test.tsx`, `openspec validate ask-thread-history --strict`.

## 2. 새 대화와 스레드 전환 중에도 진행 중 답변은 저장된다

- [x] 2.1 새 대화·목록 전환이 동작하고, 스트리밍 중 이동해도 기존 `/ask`는 취소되지 않으며 완료 후 원래 스레드에서 복원된다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/78)
  - Given: 슬라이스 1이 통과해 작성자가 하나 이상의 저장 스레드를 갖고, Ask 화면에서 답을 스트리밍 중이다.
  - When: `[새 대화]`를 누르거나 목록에서 다른 스레드를 선택한 뒤, 원래 스레드로 돌아온다. 같은 질문의 재시도 버튼을 누르면 새 `client_turn_id`로 제출한다.
  - Then: 새 대화는 빈 상태(`EMPTY_HEADING`/`EMPTY_BODY` 불변)와 입력 포커스를 보이고 첫 제출에서 스레드를 만든다. 진행 중 fetch는 abort되지 않아 서버가 citations 후 persist·`done`을 마친다. 복귀 시 살아있는 스트림이 있으면 그것을, 없으면 GET(필요 시 짧은 재시도)으로 서버 최종 상태를 보여 준다. 재시도는 별도 논리 턴으로 저장된다. 이전 턴은 LLM 문맥에 재주입되지 않는다.
  - Verification: `cd apps/dashboard && pnpm test -- --run tests/AskThreadSwitch.test.tsx`, `cd apps/api && uv run pytest tests/test_ask_thread_history.py -q -k "retry or switch or client_turn_id"`.

## 3. 내 대화의 이름을 바꾸고 삭제할 수 있다

- [x] 3.1 작성자가 제목을 바꾸고 확인 후 삭제하면 스레드와 턴이 함께 사라지며, 남의 스레드·멤버십 상실·빈 제목은 거부된다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/79)
  - Given: 작성자에게 저장된 스레드가 하나 이상 있고, 같은 워크스페이스에 다른 멤버가 있다.
  - When: 목록에서 비어 있지 않은 제목으로 이름을 바꾸거나, 삭제 확인 모달에서 삭제를 확정한다. 다른 멤버가 같은 id로 PATCH/DELETE 하거나, 작성자가 멤버십을 잃은 뒤 접근한다. 삭제된 `?thread=` 딥링크를 연다.
  - Then: 목록에 새 제목이 반영된다. 삭제는 cascade로 메시지를 제거하고 다음 스레드 또는 빈 목록으로 보낸다. 빈 제목은 저장되지 않는다. 타인·비멤버 쓰기는 0행→HTTP 403이고 목록에 노출되지 않는다. 삭제된 딥링크는 notice 카드와 `[새 대화]`를 보여 준다.
  - Verification: `cd apps/api && uv run pytest tests/test_ask_thread_history.py tests/test_ask_thread_history_isolation.py -q -k "rename or delete or forbidden"`, `cd apps/dashboard && pnpm test -- --run tests/AskThreadLifecycle.test.tsx`.
