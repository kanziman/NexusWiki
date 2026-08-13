# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## worker-parse-jsondecodeerror — PostgREST 204 No Content on `returns void` RPC crashes worker's generic `_rpc()` at `.json()`
- **Date:** 2026-08-13
- **Error patterns:** JSONDecodeError, Expecting value: line 1 column 1 (char 0), response.json(), _rpc(), index_source_chunk_lexical, index_wiki_page_lexical, returns void, PostgREST 204 No Content, worker parse handler crash
- **Root cause(s):** `apps/worker/src/worker/db/service.py`의 `_rpc()`(752-769줄)가 `raise_for_status()` 통과 후 무조건 `response.json()`을 호출한다. `index_source_chunk_lexical`/`index_wiki_page_lexical`이 SQL에서 `returns void`로 선언되어 있어(`supabase/migrations/0011_retrieval.sql:18-58`) PostgREST가 이 RPC 호출에 HTTP 204 No Content(빈 바디)로 응답하고, `raise_for_status()`는 204를 2xx로 통과시키므로 `.json()`이 빈 바디에서 `JSONDecodeError`를 던진다. 단일 code 카테고리 결함(권한·마이그레이션·환경 문제 아님 — 함수 존재·EXECUTE 권한 curl/psql로 확인됨).
- **Fix:** `_rpc()`에 `raise_for_status()` 직후, `response.json()` 호출 전에 단락 처리 추가: `response.status_code == 204` 이거나 `response.content`가 비어 있으면 즉시 `None`을 반환. `index_source_chunk_lexical`과 `index_wiki_page_lexical` 둘 다 이 경로를 공유하므로 함께 고쳐짐. `claim_job` 등 항상 JSON 바디를 반환하는 다른 `_rpc()` 호출부는 동작 변화 없음.
- **Files changed:** apps/worker/src/worker/db/service.py (_rpc()에 204/빈 바디 단락 처리 7줄), apps/worker/tests/test_service_client.py (회귀 테스트 2건 + 헬퍼 1개 추가)
- **Why not caught:** 유닛 테스트(`test_service_client.py`)는 존재했지만, RPC 응답을 만드는 목 헬퍼 `client_returning()`이 항상 `httpx.Response(status, json=payload)`로 JSON 바디를 강제로 붙였다 — PostgREST의 실제 `returns void` 204-무바디 동작을 한 번도 모델링한 적이 없어, 있던 게이트가 잘못된 불변조건을 검증하고 있었다. 통합 테스트도 없었고, 이 경로(대시보드 소스 등록 -> parse job claim -> lexical indexing)는 같은 세션의 CORS 미들웨어 부재(커밋 250f4e8 이전)로 인해 오늘 처음 라이브로 실행되었다 — 정적 검사로는 잡을 수 없는 런타임 전용 버그.
- **Recurrence guard:** 회귀 테스트 `apps/worker/tests/test_service_client.py::test_lexical_rpc_helpers_treat_204_no_content_as_none`과 `::test_rpc_treats_any_empty_body_as_none_even_with_200_status`가 `_rpc()`의 204/빈 바디 -> `None` 단락 처리를 직접 검증한다(둘 다 확인 시점 통과, revert-and-reconfirm으로 실제로 버그를 잡아냄을 실증). 앞으로 새 `returns void` RPC가 추가되어도 동일한 `_rpc()` 헬퍼를 거치므로 이 클래스 전체가 커버된다.
---

