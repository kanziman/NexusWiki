# Spec Conformance 리뷰 — ask-thread-history r1

- 판정: needs_fix
- 대상: `git diff main...HEAD` (`757701df60386ce980f019d1b98c2c65f2145663`)
- 일시: 2026-08-23T04:54:35Z

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 사용자 소유 Ask 스레드 생명주기 / 새 대화 시작 | 충족 | 초안은 `thread_id`를 보내지 않음 `apps/dashboard/components/AskConversation.tsx:241-243,285-291`. `persist_ask_turn`이 스레드를 insert하고 제목을 첫 질문 80자로 자름 `supabase/migrations/0018_ask_history.sql:176-184`. 테스트 `apps/dashboard/tests/AskThreadSwitch.test.tsx:68-93`(빈 상태·첫 제출 `client_turn_id`) |
| 사용자 소유 Ask 스레드 생명주기 / 자신의 대화 목록 조회와 전환 | 충족 | 목록 `updated_at.desc` `apps/api/src/api/routers/ask.py:128-136`. 서랍 선택 → `openThread` `AskConversation.tsx:214-225,422-424` · `ThreadDrawer.tsx:82-90`. 테스트 `AskThreadHistoryRestore.test.tsx:98-112` · 소유 목록 `test_ask_thread_history_isolation.py:48-54` |
| 사용자 소유 Ask 스레드 생명주기 / 대화 이름 변경 | 충족 | PATCH `min_length=1` `ask.py:107-110,163-176`. 클라이언트 공백 제목은 저장 호출을 생략 `ThreadDrawer.tsx:107-110`. 테스트 `AskThreadLifecycle.test.tsx:118-129` · `test_ask_thread_history.py:197-217`(200·빈 제목 422) |
| 사용자 소유 Ask 스레드 생명주기 / 대화 삭제 확인 | 충족 | 확인 모달 후 DELETE `AskConversation.tsx:624-665` · `ask.py:179-190`. 메시지 cascade `0018_ask_history.sql:88-90`. 활성 스레드 삭제는 새 대화 상태 `AskConversation.tsx:657-659,378-386`. 테스트 `AskThreadLifecycle.test.tsx:131-145` · 삭제 딥링크 notice `108-113` |
| 완료된 턴의 내구성과 멱등성 / 정상 완료 후 done 발행 | 충족 | persist 성공 뒤에만 `done` `apps/api/src/api/services/ask.py:394-418,583-594`. 클라이언트는 `done.thread_id`로 초안 키만 옮기고 인용 본문을 `done`에서 저장하지 않음 `AskConversation.tsx:337-351`. 테스트 `test_ask_thread_history.py:49-84` |
| 완료된 턴의 내구성과 멱등성 / 동일 완료 턴 재전달 | 미충족 | UNIQUE `(thread_id, client_turn_id)`와 `on conflict do nothing` 경로는 있음 `0018_ask_history.sql:87,215-224`. 같은 키를 두 번 영속화해도 행이 늘지 않음을 단언하는 테스트는 없음 |
| 완료된 턴의 내구성과 멱등성 / 사용자가 명시적으로 답변 재시도 | 충족 | 매 제출마다 `newClientTurnId()` `AskConversation.tsx:60-62,240`. 재시도 버튼이 같은 질문으로 `submitQuestion`을 다시 호출해 턴을 append `534-536`. 테스트 `test_ask_thread_history.py:223-259`(서로 다른 `client_turn_id`가 persist로 전달) |
| 완료된 턴의 내구성과 멱등성 / 영속화 실패 | 충족 | persist 예외·빈 결과는 `done`을 yield하지 않음 `ask.py:385-391,416-417`. 테스트 `test_ask_thread_history.py:88-116`(`done` 없음) |
| 복원된 턴의 이중 Citation 재수화 / 위키와 원문 인용이 있는 답변 복원 | 충족 | `turnsFromMessages`가 `splitTextWithAnchors(text, resolved)` `AskConversation.tsx:107-116`. 마커 클릭은 기존 위키·원문 경로 `388-407`. 테스트 `AskThreadHistoryRestore.test.tsx:98-112`(wiki+source resolved, placeholder 없음) · 클릭 경로 `AskConversation.test.tsx:245-306` |
| 복원된 턴의 이중 Citation 재수화 / 발급되지 않은 앵커가 포함된 저장 텍스트 | 충족 | resolved에 없는 별칭은 part를 emit하지 않음 `apps/dashboard/lib/citation-anchors.ts:71-76`. 복원 경로가 같은 함수를 resolved와 함께 호출 `AskConversation.tsx:109-112`. 테스트 `citation-anchors.test.ts:28-41` |
| 복원된 턴의 이중 Citation 재수화 / 근거 없음 또는 오류 턴 복원 | 미충족 | `turnsFromMessages`가 `no-evidence`/`error`를 카드 상태로 매핑하고 빈 인용 placeholder를 만들지 않음 `AskConversation.tsx:85-102,514-538`. 저장된 스레드를 다시 여는 복원 테스트는 resolved 이중 인용만 있고(`AskThreadHistoryRestore.test.tsx`), 두 최종 상태 복원은 검증되지 않음. task 1.1 Then은 이 복원을 완료로 주장함 |
| 복원된 턴의 이중 Citation 재수화 / 연결 끊김 상태 | 충족 | `dropped`는 스트림이 `streaming`으로 끝난 로컬 finally만 설정 `AskConversation.tsx:354-362,539-554`. persist 상태는 SQL이 `resolved`/`no-evidence`/`error`만 허용 `0018_ask_history.sql:85`. 테스트 `AskConversation.test.tsx:175-193`(드롭 카드·재시도, persist 호출 없음) |
| 작성자와 워크스페이스를 함께 강제하는 RLS / 작성자인 현재 멤버의 접근 | 충족 | SELECT/INSERT/UPDATE/DELETE가 `user_id = auth.uid()` ∩ `is_workspace_member` `0018_ask_history.sql:36-70,98-124`. 테스트 `test_ask_thread_history_isolation.py:39-54` |
| 작성자와 워크스페이스를 함께 강제하는 RLS / 같은 워크스페이스의 다른 작성자 | 충족 | 동일 정책. 테스트 목록 공백·쓰기 0행 `test_ask_thread_history_isolation.py:56-83` · API 403 `87-116` |
| 작성자와 워크스페이스를 함께 강제하는 RLS / 멤버십을 잃은 작성자 | 미충족 | SELECT `using`에 `is_workspace_member`가 있어 작성자만으로는 통과하지 않음 `0018_ask_history.sql:34-42`. 작성자가 멤버십을 잃은 뒤 자기 스레드에 접근하는 테스트는 없음. 동료 멤버 거부는 이 WHEN을 대체하지 못함(저자는 맞고 멤버십만 빠진 경우와 구분됨). task 3.1이 이 경로를 완료로 주장함 |
| 작성자와 워크스페이스를 함께 강제하는 RLS / 익명 접근 | 충족 | 정책·GRANT가 `authenticated`만 `0018_ask_history.sql:38-72,100-127,235`. `anon` 정책 없음. 테스트 `test_ask_thread_history_isolation.py:120-129` |
| 작성자와 워크스페이스를 함께 강제하는 RLS / USING 정책이 쓰기를 0행으로 만든 경우 | 충족 | `update_one`/`delete_one`이 1행이 아니면 `WorkspaceForbidden` `apps/api/src/api/db/user.py:146-153` → HTTP 403 `apps/api/src/api/errors.py:197`. 테스트 `test_ask_thread_history_isolation.py:107-116` · 빈 GET도 403 `test_ask_thread_history.py:194-216` |
| 사용자 요청의 JWT 데이터 경로 / 스레드 사용자 요청 처리 | 충족 | 스레드 CRUD·`/ask` persist 모두 bearer JWT `UserDb` `ask.py:46-54,100,128,144,171,186` · `AskService._persist_completed_turn` `ask.py:376-384`. 테스트 `test_ask_thread_history.py:120-219` |
| 사용자 요청의 JWT 데이터 경로 / 우회 자격 증명 방지 | 충족 | `persist_ask_turn`은 `security invoker`이고 `authenticated`에만 execute `0018_ask_history.sql:174-175,234-235`. ask 라우터·서비스에 `service_role`/`service_client` 없음. 시나리오 WHEN이 경로 검사이므로 이 리뷰가 증거 |
| 스레드 전환 중인 Ask 요청의 지속 / 스트리밍 중 다른 스레드로 이동 | 충족 | `submitQuestion`에 `AbortController`가 없고 새 대화·선택은 fetch를 취소하지 않음 `AskConversation.tsx:277-293,378-386,422-424`. 테스트 `AskThreadSwitch.test.tsx:68-85`(빈 상태 전환). 다만 테스트의 `abortSpy`는 fetch에 연결되지 않아 abort 부재를 실제로 단언하지 못함 |
| 스레드 전환 중인 Ask 요청의 지속 / 완료 후 원래 스레드로 복귀 | 충족 | `done` 이후 복귀는 `openThread` GET + `turnsFromMessages` `AskConversation.tsx:214-219,83-116`. `done`은 persist 커밋 뒤에만 오므로 GET이 최종 턴을 읽는다. 이중 인용 복원 테스트 `AskThreadHistoryRestore.test.tsx:98-112`. 전환 후 복귀 흐름 전용 테스트는 없음 |
| 기존 grounded Ask 의미 보존 / 저장 스레드에서 후속 질문 | 충족 | LLM `messages`는 현재 `query`로 만든 system+user 한 쌍뿐 `apps/api/src/api/services/ask.py:490-512`. 이전 턴을 받는 인자가 없음. 기존 Ask 라우트 테스트가 같은 단건 경로를 유지 `test_ask_router.py:233-278` |
| 기존 grounded Ask 의미 보존 / SSE 호환성 | 충족 | 이벤트 순서 `meta` → (`delta`*) → `citations` → persist 후 `done` `ask.py:434-455,495-547,583-594`. 테스트 `test_ask_thread_history.py:78-80` |
| 저장소 작성 규약 / 계획 문서와 구현 산출물 검토 | 충족 | OpenSpec·주석은 한국어, 식별자는 ASCII, `0018_ask_history.sql` 키워드·식별자 소문자. 이 리뷰가 해당 WHEN |

## 조치가 필요한 항목

1. **동일 `(thread_id, client_turn_id)` 재전달 멱등 테스트가 없다** — DDL에 UNIQUE와 `on conflict do nothing`은 있으나, 같은 키를 두 번 persist해도 메시지 행이 늘지 않고 성공으로 수렴하는지 검증하는 테스트가 없다. task 1.1 Then은 이 동작을 완료로 표시한다. 근거 Scenario: 「동일 완료 턴 재전달」. 제안: `persist_ask_turn`을 같은 `p_thread_id`·`p_client_turn_id`로 두 번 호출하거나 `/ask`를 같은 키로 두 번 보내 `ask_messages` 건수가 1인지 단언한다.

2. **저장된 `no-evidence`/`error` 턴 복원이 미검증이다** — `turnsFromMessages`는 라이브 SSE 핸들러와 다른 경로다. 복원 테스트는 resolved 이중 인용만 덮는다. task 1.1 Then은 "`no-evidence`/`error` 턴은 placeholder 없이 해당 카드로 복원된다"를 `[x]`로 주장한다. 근거 Scenario: 「근거 없음 또는 오류 턴 복원」. 제안: `AskThreadHistoryRestore`에 status `no-evidence`와 `error` GET fixture를 넣고 `no-evidence-card`/`ask-error-card`·재시도 버튼·placeholder 부재를 단언한다.

3. **멤버십을 잃은 작성자 접근이 미검증이다** — SELECT `using`에 `is_workspace_member`가 있어 구현은 스펙과 맞다. 그러나 같은 워크스페이스 다른 멤버 테스트는 `user_id` 불일치만 증명한다. 작성자 일치 + 멤버십 상실을 막지 못하면 0017 즐겨찾기식 SELECT로 후퇴해도 현재 격리 테스트는 통과한다. task 3.1 When은 "작성자가 멤버십을 잃은 뒤 접근한다"를 포함한다. 근거 Scenario: 「멤버십을 잃은 작성자」. 제안: 스레드를 만든 뒤 해당 사용자의 `workspace_members` 행을 제거하고 GET/PATCH/DELETE가 거절되는지 로컬 스택 테스트를 추가한다.

4. **`AskThreadSwitch`의 abort 단언은 거짓 통과다** — `abortSpy`를 선언만 하고 `fetch`/`AbortController`에 연결하지 않은 채 `not.toHaveBeenCalled()`를 단언한다 `AskThreadSwitch.test.tsx:69-85`. 구현에 abort가 없는 것은 맞지만, task 2.1 Verification이 이 파일로 전환 중 취소를 증명한다고 주장하므로 스파이 연결 또는 abort signal 부재 단언으로 고쳐야 한다.

## 판정 근거

스펙이 요구하는 사용자 흐름(스레드 CRUD, persist-then-`done`, 이중 인용 재수화, `user_client`, 스트리밍 중 미취소, 단건 grounded Ask, RLS 작성자∩멤버십)의 코드 경로는 존재하고 핵심 슬라이스 테스트도 있다. 미충족 세 건은 THEN 경로가 빠져서가 아니라, 완료 표시된 task가 명시한 동작을 확인하는 테스트가 없는 **미검증 완료 주장**이다. 특히 「멤버십을 잃은 작성자」는 동료 멤버 테스트로 대체할 수 없고, 「no-evidence/error 복원」은 라이브 SSE 테스트로 대체할 수 없다. 스펙을 고칠 필요는 없고 테스트를 보강하면 되므로 `blocked`가 아니라 `needs_fix`다. 전환 후 복귀는 `openThread` GET이 persist 이후 최종 턴을 읽도록 구현되어 있어 시나리오 자체는 충족으로 본다.
