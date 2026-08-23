# Tenant Isolation 리뷰 — ask-thread-history r1

- 판정: pass
- 대상: `git diff main...HEAD` (`757701df60386ce980f019d1b98c2c65f2145663`)
- 일시: 2026-08-23T04:59:38Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | Ask 라우터·서비스·스레드 CRUD가 전부 `_user_db()` → `UserDb`(요청자 JWT). `persist_ask_turn`도 `user_db.rpc`로만 호출. 대시보드는 `apiFetch`/`session.access_token`. 이번 diff에 `service_client`/`service_role` 사용 없음 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | `0018_ask_history.sql`에서 `ask_threads`(11–32행)·`ask_messages`(77–96행) 모두 `create table`과 같은 파일에서 `enable row level security`. 정책 없는 창 없음 |
| A-3 | anon 신규 GRANT/정책 | 통과 | 마이그레이션은 `authenticated`에만 GRANT·정책. `anon` 정책 0건. 로컬 DB 실측: `anon`은 두 테이블 모두 `TRUNCATE/REFERENCES/TRIGGER`(스키마 기본값)만 보유, `SELECT/INSERT/UPDATE/DELETE` 없음. `set role anon; select … from ask_threads` → `permission denied for table ask_threads`. `persist_ask_turn` EXECUTE는 `authenticated`·`postgres`만 |
| A-4 | 워커 workspace_id 명시 필터 | 해당 없음 | 워커/service_role 경로가 생기지 않음. 로컬 카탈로그에서 `service_role`은 두 테이블에 DML GRANT가 없고, `persist_ask_turn` EXECUTE도 없음 |
| A-5 | 신규 자식 테이블 복합 FK | 통과 | `ask_messages`가 `(thread_id, workspace_id) references ask_threads (id, workspace_id)` (`0018_ask_history.sql:88-90`). 부모 `ask_threads`는 `unique (id, workspace_id)`(22행)로 이를 뒷받침. 다른 워크스페이스 id를 짝지으면 FK가 막음 |
| B-6 | 0행 → 403 매핑 | 통과 | PATCH/DELETE는 `UserDb.update_one`/`delete_one` → `_exactly_one`이 0행을 `WorkspaceForbidden`으로 올림 (`user.py:118-153`). GET-one은 빈 SELECT를 `WorkspaceForbidden(table="ask_threads", affected=0)`으로 변환 (`ask.py:151-153`). `test_api_zero_row_rename_and_delete_are_403`이 교차 멤버 403을 단언 |
| B-7 | 42501 → 403 매핑 | 통과 | 전역 핸들러가 SQLSTATE `42501`을 403으로 렌더 (`errors.py:39,181-202`). `persist_ask_turn`은 비가시 스레드를 `errcode = '42501'`로 raise (`0018_ask_history.sql:191-194`). SSE 경로에서는 스트림이 이미 열린 뒤라 HTTP 상태를 바꿀 수 없고, `done`을 생략해 저장 성공으로 위장하지 않음 (`ask.py:388-418`, `test_persist_failure_omits_done`) |
| C-8 | at-least-once 멱등성 | 통과 | 새 도메인 키 `unique (thread_id, client_turn_id)` + `on conflict do nothing` 후 기존 행을 성공으로 반환 (`0018_ask_history.sql:87,215-224`). 위키/청크 upsert 키 대상 테이블이 아님. 재시도 버튼은 새 `client_turn_id`를 씀 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 테이블·큐 함수 변경 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 SQL/RPC 변경 없음. 기존 retrieval 경로를 그대로 호출 |
| D-11 | 토크나이저 버전 일치 | 해당 없음 | `tsv_tokenizer_version` 관련 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 통과 | `ask.py` persist 래핑이 `_render()`를 건드리지 않음. `_render`는 `str.format` 금지를 유지 (`ask.py:196-213`). 신규 `str.format` 호출 없음 |
| D-14 | 인용 앵커 포함 여부 | 통과 | LLM 컨텍스트 조립(`_context_blocks`, `ask.py:312-338`)은 원문에 `raw_source_id`+`chunk_index`, 위키에 발급 별칭을 그대로 실음. persist는 `citations.text`+`resolved[]`를 저장하고 복원은 `splitTextWithAnchors(text, resolved)`로 재수화 |
| E-15 | 마이그레이션 번호 순서 | 통과 | 기존 최대 `0017_wiki_bookmarks.sql` 다음이 `0018_ask_history.sql`. 앞선 번호 삽입 없음 |

## 조치가 필요한 항목

없음.

## 판정 근거

사용자 Ask 경로가 `service_role`을 끼워 넣지 않고 요청자 JWT `UserDb`만 쓰며, `persist_ask_turn`은 `security invoker`라 RLS가 그대로 평가된다. 새 테이블은 생성과 동시에 RLS가 켜지고 정책은 `to authenticated` + `user_id = auth.uid()` ∩ `is_workspace_member(workspace_id)`다(0017 SELECT보다 한 겹 엄격). 자식 행은 복합 FK로 워크스페이스를 나르고, `anon`에는 DML GRANT·정책이 없다(로컬에서 SELECT `permission denied` 실측). PATCH/DELETE 0행과 GET-one 공집합은 403으로 매핑되며 교차 멤버 테스트가 이를 단언한다. 멱등 키 `(thread_id, client_turn_id)`는 at-least-once 재전송을 중복 행으로 키우지 않고, 인용 앵커 조립·`str.format` 금지는 기존 Ask 계약을 유지한다. 테넌트 경계를 넘는 경로를 찾지 못했다.
