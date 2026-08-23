# Spec Conformance 리뷰 — ask-thread-history r2

- 판정: pass
- 대상: `git diff main...HEAD` (`a8d804ed22492fa7dbe7fe222fb353e1bf73ef7e`)
- 일시: 2026-08-23T05:08:54Z

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 사용자 소유 Ask 스레드 생명주기 / 새 대화 시작 | 충족 | 초안은 `thread_id`를 보내지 않음 `apps/dashboard/components/AskConversation.tsx:241-243,277-291`. `persist_ask_turn`이 스레드를 insert하고 제목을 첫 질문 80자로 자름 `supabase/migrations/0018_ask_history.sql:176-184`. 테스트 `apps/dashboard/tests/AskThreadSwitch.test.tsx:75-99`(빈 상태·첫 제출 `client_turn_id`) |
| 사용자 소유 Ask 스레드 생명주기 / 자신의 대화 목록 조회와 전환 | 충족 | 목록 `updated_at.desc` `apps/api/src/api/routers/ask.py:122-134`. 서랍 선택 → `openThread` `AskConversation.tsx:214-219,422-424` · `ThreadDrawer.tsx:82-90`. 테스트 `AskThreadHistoryRestore.test.tsx:98-112` · 소유 목록 `test_ask_thread_history_isolation.py:49-55` |
| 사용자 소유 Ask 스레드 생명주기 / 대화 이름 변경 | 충족 | PATCH `min_length=1` `ask.py:107-110,163-176`. 클라이언트 공백 제목은 저장 호출을 생략 `ThreadDrawer.tsx:107-110`. 테스트 `AskThreadLifecycle.test.tsx:118-129` · `test_ask_thread_history.py:197-219`(200·빈 제목 422) |
| 사용자 소유 Ask 스레드 생명주기 / 대화 삭제 확인 | 충족 | 확인 모달 후 DELETE `AskConversation.tsx:624-665` · `ask.py:179-190`. 메시지 cascade `0018_ask_history.sql:88-90`. 활성 스레드 삭제는 새 대화 상태 `AskConversation.tsx:657-659,378-386`. 테스트 `AskThreadLifecycle.test.tsx:131-145` · 삭제 딥링크 notice `108-113` |
| 완료된 턴의 내구성과 멱등성 / 정상 완료 후 done 발행 | 충족 | persist 성공 뒤에만 `done` `apps/api/src/api/services/ask.py:394-418,583-594`. 클라이언트는 `done.thread_id`로 초안 키만 옮기고 인용 본문을 `done`에서 저장하지 않음 `AskConversation.tsx:337-351`. 테스트 `test_ask_thread_history.py:49-84` |
| 완료된 턴의 내구성과 멱등성 / 동일 완료 턴 재전달 | 충족 | UNIQUE `(thread_id, client_turn_id)`와 `on conflict on constraint ask_messages_turn_key do nothing` 후 기존 `message_id`를 반환 `0018_ask_history.sql:87,215-226`. 같은 키를 두 번 RPC해도 성공·동일 `message_id`·메시지 1행 `test_ask_thread_history_isolation.py:134-176` |
| 완료된 턴의 내구성과 멱등성 / 사용자가 명시적으로 답변 재시도 | 충족 | 매 제출마다 `newClientTurnId()` `AskConversation.tsx:60-62,240`. 재시도 버튼이 같은 질문으로 `submitQuestion`을 다시 호출 `534-536`. 테스트 `test_ask_thread_history.py:223-259`(서로 다른 `client_turn_id`가 persist로 전달) |
| 완료된 턴의 내구성과 멱등성 / 영속화 실패 | 충족 | persist 예외·빈 결과는 `done`을 yield하지 않음 `ask.py:385-391,416-417`. 테스트 `test_ask_thread_history.py:88-116`(`done` 없음) |
| 복원된 턴의 이중 Citation 재수화 / 위키와 원문 인용이 있는 답변 복원 | 충족 | `turnsFromMessages`가 `splitTextWithAnchors(text, resolved)` `AskConversation.tsx:107-116`. 마커 클릭은 기존 위키·원문 경로 `388-407`. 테스트 `AskThreadHistoryRestore.test.tsx:98-112`(wiki+source resolved, placeholder 없음) · 클릭 경로 `AskConversation.test.tsx:245-306` |
| 복원된 턴의 이중 Citation 재수화 / 발급되지 않은 앵커가 포함된 저장 텍스트 | 충족 | resolved에 없는 별칭은 part를 emit하지 않음 `apps/dashboard/lib/citation-anchors.ts:71-76`. 복원 경로가 같은 함수를 resolved와 함께 호출 `AskConversation.tsx:109-112`. 테스트 `citation-anchors.test.ts:28-41` |
| 복원된 턴의 이중 Citation 재수화 / 근거 없음 또는 오류 턴 복원 | 충족 | `turnsFromMessages`가 `no-evidence`/`error`를 카드 상태로 매핑하고 빈 인용 placeholder를 만들지 않음 `AskConversation.tsx:85-102,514-538`. GET fixture 복원 테스트 `AskThreadHistoryRestore.test.tsx:114-146`(no-evidence 카드·placeholder 부재) · `148-181`(error 카드·재시도·placeholder 부재) |
| 복원된 턴의 이중 Citation 재수화 / 연결 끊김 상태 | 충족 | `dropped`는 스트림이 `streaming`으로 끝난 로컬 finally만 설정 `AskConversation.tsx:354-362,539-554`. persist 상태는 SQL이 `resolved`/`no-evidence`/`error`만 허용 `0018_ask_history.sql:85`. 테스트 `AskConversation.test.tsx:175-193`(드롭 카드·재시도). 클라이언트 persist 호출 경로 없음 |
| 작성자와 워크스페이스를 함께 강제하는 RLS / 작성자인 현재 멤버의 접근 | 충족 | SELECT/INSERT/UPDATE/DELETE가 `user_id = auth.uid()` ∩ `is_workspace_member` `0018_ask_history.sql:36-70,98-124`. 테스트 `test_ask_thread_history_isolation.py:39-55` |
| 작성자와 워크스페이스를 함께 강제하는 RLS / 같은 워크스페이스의 다른 작성자 | 충족 | 동일 정책. 테스트 목록 공백·쓰기 0행 `test_ask_thread_history_isolation.py:57-84` · API 403 `88-117` |
| 작성자와 워크스페이스를 함께 강제하는 RLS / 멤버십을 잃은 작성자 | 충족 | SELECT `using`에 `is_workspace_member`가 있어 작성자만으로는 통과하지 않음 `0018_ask_history.sql:34-42`. 작성자 스레드 생성 후 `workspace_members` 삭제 → REST GET 0행·PATCH/DELETE HTTP 403 `test_ask_thread_history_isolation.py:180-227` |
| 작성자와 워크스페이스를 함께 강제하는 RLS / 익명 접근 | 충족 | 정책·GRANT가 `authenticated`만 `0018_ask_history.sql:38-72,100-127,238-239`. `anon` 정책 없음. 테스트 `test_ask_thread_history_isolation.py:120-130` |
| 작성자와 워크스페이스를 함께 강제하는 RLS / USING 정책이 쓰기를 0행으로 만든 경우 | 충족 | `update_one`/`delete_one`이 1행이 아니면 `WorkspaceForbidden` `apps/api/src/api/db/user.py:146-153` → HTTP 403 `apps/api/src/api/errors.py:197`. 테스트 `test_ask_thread_history_isolation.py:88-117` · 빈 GET도 403 `test_ask_thread_history.py:194-216` |
| 사용자 요청의 JWT 데이터 경로 / 스레드 사용자 요청 처리 | 충족 | 스레드 CRUD·`/ask` persist 모두 bearer JWT `UserDb` `ask.py:46-54,100,128,144,171,186` · `AskService._persist_completed_turn` `ask.py:376-384`. 테스트 `test_ask_thread_history.py:120-219` |
| 사용자 요청의 JWT 데이터 경로 / 우회 자격 증명 방지 | 충족 | `persist_ask_turn`은 `security invoker`이고 `authenticated`에만 execute `0018_ask_history.sql:164,238-239`. ask 라우터·서비스에 `service_role`/`service_client` 없음. 시나리오 WHEN이 경로 검사이므로 이 리뷰가 증거 |
| 스레드 전환 중인 Ask 요청의 지속 / 스트리밍 중 다른 스레드로 이동 | 충족 | `submitQuestion`에 `AbortController`가 없고 fetch에 `signal`을 넘기지 않음 `AskConversation.tsx:277-293,378-386,422-424`. 테스트 `AskThreadSwitch.test.tsx:57-64,75-94`(signal 존재 시 throw · `fetchInit.signal` undefined · 빈 상태 전환) |
| 스레드 전환 중인 Ask 요청의 지속 / 완료 후 원래 스레드로 복귀 | 충족 | `done` 이후 복귀는 `openThread` GET + `turnsFromMessages` `AskConversation.tsx:214-219,83-116`. `done`은 persist 커밋 뒤에만 오므로 GET이 최종 턴을 읽는다. 이중 인용 복원 테스트 `AskThreadHistoryRestore.test.tsx:98-112` |
| 기존 grounded Ask 의미 보존 / 저장 스레드에서 후속 질문 | 충족 | LLM `messages`는 현재 `query`로 만든 system+user 한 쌍뿐 `apps/api/src/api/services/ask.py:507-512`. 이전 턴을 받는 인자가 없음. 기존 Ask 라우트 테스트가 같은 단건 경로를 유지 `test_ask_router.py:233-278` |
| 기존 grounded Ask 의미 보존 / SSE 호환성 | 충족 | 이벤트 순서 `meta` → (`delta`*) → `citations` → persist 후 `done` `ask.py:434-455,495-547,583-594`. 테스트 `test_ask_thread_history.py:78-80` · delta 포함 순서 `test_ask_router.py:219-222` |
| 저장소 작성 규약 / 계획 문서와 구현 산출물 검토 | 충족 | OpenSpec·주석은 한국어, 식별자는 ASCII, `0018_ask_history.sql` 키워드·식별자 소문자. 이 리뷰가 해당 WHEN |

## 조치가 필요한 항목

없음. r1의 미충족 세 시나리오와 거짓 통과 abort 단언은 `a8d804e`에서 닫혔다.

1. **동일 `(thread_id, client_turn_id)` 재전달** — `test_same_client_turn_id_replay_does_not_duplicate_messages`가 같은 키로 `persist_ask_turn`을 두 번 호출해 동일 `message_id`와 메시지 1행을 단언한다. ON CONFLICT는 출력 컬럼명 모호를 피하도록 `ask_messages_turn_key` 제약 이름으로 지정됐다.
2. **저장된 `no-evidence`/`error` 턴 복원** — `AskThreadHistoryRestore`가 GET fixture로 두 최종 상태를 열고 카드·재시도·placeholder 부재를 단언한다.
3. **멤버십을 잃은 작성자** — 작성자 스레드를 만든 뒤 `workspace_members`를 제거하고 REST GET 0행과 API PATCH/DELETE 403을 단언한다.
4. **`AskThreadSwitch` abort 단언** — fetch mock이 `signal`이 있으면 throw하고, 호출 init의 `signal`이 undefined임을 확인한다.

## 판정 근거

delta spec의 24개 Scenario 모두 WHEN 경로와 THEN 결과가 코드에 있고, 완료 표시된 task가 명시한 동작을 확인하는 테스트가 따라온다. r1 `needs_fix`의 원인은 구현 부재가 아니라 미검증 완료 주장이었고, `a8d804e`가 멱등 재전달·무근거/오류 복원·멤버십 상실 접근을 각각 독립 테스트로 증명했다. 스펙 범위 밖의 사용자 관찰 가능 동작은 보이지 않는다.
