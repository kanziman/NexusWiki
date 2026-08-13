---
status: resolved
trigger: "worker의 파싱 단계에서 발생하는 JSONDecodeError 진단. HANDOFF.md에 기록된 트레이스백: handlers/parse.py:184의 run_parse -> db.index_source_chunk_lexical(어휘 색인 RPC 호출, db/service.py:279) -> db/service.py:755의 _rpc()가 response.json()을 호출하는 지점에서 json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0) 발생. RPC 응답 바디가 비어있거나 JSON이 아님. 원인 미조사 상태."
created: 2026-08-13T00:56:42Z
updated: 2026-08-13T01:20:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

reasoning_checkpoint:
  hypothesis: "_rpc()가 raise_for_status() 이후 무조건 response.json()을 호출한다. index_source_chunk_lexical/index_wiki_page_lexical은 SQL에서 returns void이고, PostgREST는 void 함수 호출에 HTTP 204(빈 바디)로 응답하므로 .json()이 JSONDecodeError를 던진다."
  confirming_evidence:
    - "curl로 로컬 PostgREST RPC 엔드포인트를 직접 호출 -> HTTP 204 No Content, 바디 없음 (Content-Range: 0-0/*)"
    - "python3 재현: httpx.Response(204, content=b'', request=req); raise_for_status() 통과; .json()이 정확히 'Expecting value: line 1 column 1 (char 0)'을 던짐 — 보고된 트레이스백과 문자 그대로 일치"
  falsification_test: "PostgREST가 200+빈 JSON 객체로 응답했거나 raise_for_status()가 204에서 실제로 예외를 던졌다면 이 가설은 거짓이었을 것이다. 둘 다 아님 — 204 + raise_for_status 무반응 + 빈 바디로 실증됨."
  fix_rationale: "_rpc()가 '내용 없음' 응답(204 또는 빈 바디)을 유효한 None 결과로 처리하도록 고쳐야 한다 — 실제 결함(바디 없는 2xx를 전혀 예상하지 않는 코드 경로)을 고치는 것이지, 호출부만 try/except로 감싸 증상을 덮는 게 아니다."
  blind_spots: "다른 _rpc() 호출부가 204에서 예외가 나는 것에 암묵적으로 의존하는지 전체 스위트로 아직 확인 안 함(다음 단계에서 pytest 실행으로 확인). 앞으로 추가될 다른 void RPC도 동일 버그를 겪을 수 있으므로 특정 함수가 아니라 _rpc() 자체를 고쳐 일반화한다."
  candidate_causes:
    - "code: _rpc()가 status_code==204 또는 빈 바디를 확인하지 않고 response.json()을 무조건 호출 (확정된 근본 원인)"
    - "config/environment: PostgREST 버전/설정에 따른 다른 동작 가능성 — 로컬 postgrest 14.15에서 curl로 직접 확인한 204는 PostgREST의 표준 동작(void 반환 함수)이지 오설정이 아님 — 별도 원인으로서는 배제"
  and_gate: "no — code 결함 하나만으로 void RPC를 호출할 때마다 100% 재현된다. 환경/데이터의 특정 조합이 추가로 필요하지 않다."
next_action: "완료 — 오케스트레이터가 로컬 실사용 흐름(worker 기동 -> 소스/parse job 삽입 -> claim -> parse -> lexical indexing)으로 confirmed fixed 응답. 세션 resolved로 아카이브 및 커밋함."

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: 대시보드에서 소스를 등록하면 worker가 잡을 claim해 파싱 -> 어휘 색인(lexical indexing) -> 이후 단계까지 정상적으로 진행되어야 한다.
actual: worker가 파싱 단계 도중 `db.index_source_chunk_lexical` RPC 호출에서 예외를 던지며 죽는다. CORS 수정(커밋 250f4e8) 이후 대시보드 -> API 소스 등록 자체는 성공하게 되었고, 이 경로가 이번 세션에 처음 실제로(라이브로) 실행되었다.
errors: |
  json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
  at worker/db/service.py:755, inside _rpc(), called at response.json()
  call chain: handlers/parse.py:184 run_parse() -> db.index_source_chunk_lexical() (worker/db/service.py:279) -> _rpc() (worker/db/service.py:755)
reproduction: apps/api + worker를 로컬 스택(SUPABASE_URL=http://127.0.0.1:54421 등 override) 대상으로 띄우고, 대시보드 드롭존에서 소스를 등록 -> worker가 파싱 잡을 claim하는 시점에 재현됨.
started: 이번 세션(2026-08-13) 중 CORS 미들웨어 수정(커밋 250f4e8) 이후 소스 등록이 처음 성공하면서 이 경로가 처음 라이브로 실행되었고, 그 직후 발견됨. 이전에는 CORS 때문에 소스 등록 자체가 안 되어 이 코드 경로를 아무도 타지 않았을 가능성이 높음(정적 검사로는 못 잡히는 런타임 전용 버그).

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-08-13T01:00:00Z
  checked: worker/db/service.py 전체 (특히 _rpc(), 752-769줄) 및 index_source_chunk_lexical 정의(270-287줄)
  found: _rpc()는 response.raise_for_status() 뒤 무조건 response.json()을 호출한다. raise_for_status()는 2xx는 전부 통과시키므로 204도 걸러지지 않는다.
  implication: 만약 PostgREST가 이 RPC에 204(빈 바디)로 응답한다면 raise_for_status()는 통과하고 response.json()에서 바로 예외가 난다 — 정확히 관찰된 트레이스백 위치(755줄)와 일치.

- timestamp: 2026-08-13T01:00:30Z
  checked: supabase/migrations/0011_retrieval.sql:18-37 (index_source_chunk_lexical, index_wiki_page_lexical 정의)
  found: 두 함수 모두 `returns void`로 선언되어 있다.
  implication: PostgREST는 void 반환 함수를 호출하면 본문 없이 HTTP 204 No Content로 응답하는 것이 알려진 동작 — 가설과 일치.

- timestamp: 2026-08-13T01:01:00Z
  checked: "docker exec supabase_db_NexusWiki psql -- \\df public.index_source_chunk_lexical, has_function_privilege(service_role, ..., 'execute')"
  found: 함수가 실제로 존재하고(void 반환), service_role에 EXECUTE 권한이 부여되어 있다. 함수 미존재/권한 부족 가설은 배제됨.
  implication: 최초 가설의 "404/403" 분기는 틀렸다 — 문제는 권한이 아니라 응답 처리다.

- timestamp: 2026-08-13T01:02:00Z
  checked: "curl -i -X POST http://127.0.0.1:54421/rest/v1/rpc/index_source_chunk_lexical (service_role 키, 유효한 형식의 UUID 페이로드)"
  found: "HTTP/1.1 204 No Content, Content-Range: 0-0/*, 바디 없음. (postgrest/14.15)"
  implication: 직접 관찰로 확정 — 로컬 PostgREST가 이 RPC에 실제로 204+빈 바디로 응답한다.

- timestamp: 2026-08-13T01:03:00Z
  checked: "python3로 httpx.Response(204, content=b'', request=req) 에 대해 raise_for_status() 후 .json() 호출"
  found: "raise_for_status()는 예외 없이 통과, .json()에서 정확히 `JSONDecodeError: Expecting value: line 1 column 1 (char 0)` 발생 — 심볼 단위로 증상과 일치."
  implication: 메커니즘 100% 확정. raise_for_status()가 2xx-빈바디 케이스를 걸러내지 못하고 .json()이 그 자리에서 터진다.

- timestamp: 2026-08-13T01:04:00Z
  checked: apps/worker/src/worker/handlers/compile.py:290 (grep으로 index_wiki_page_lexical 호출부 확인)
  found: compile 핸들러도 동일한 void RPC(index_wiki_page_lexical)를 같은 _rpc() 경로로 호출한다.
  implication: 이 버그는 parse 핸들러뿐 아니라 compile 핸들러의 위키 페이지 lexical 색인 단계에서도 동일하게 재현된다 — 영향 범위가 parse.py 한 곳이 아니다.

- timestamp: 2026-08-13T01:05:00Z
  checked: apps/worker/tests/test_service_client.py 전체, 특히 client_returning() 헬퍼와 LEXICAL_RPC_FUNCTIONS 관련 테스트 유무
  found: client_returning()은 항상 httpx.Response(status, json=payload)로 JSON 바디를 강제로 붙인다. index_source_chunk_lexical/index_wiki_page_lexical이 _rpc()를 통해 실제 204/빈 바디 응답을 받는 경로를 검증하는 테스트가 없다(claim_job 등 QUEUE_RPC_FUNCTIONS에는 있지만 LEXICAL_RPC_FUNCTIONS 전용 테스트가 없음).
  implication: "왜 못 잡았나" — 유닛 테스트가 모든 RPC 응답에 JSON 바디를 인위적으로 붙이는 목이라 실제 PostgREST의 204-무바디 동작을 재현한 적이 없다. 통합 테스트도 없어 이 경로는 오늘 처음 라이브로 실행됐다(Symptoms.started와 일치).

- timestamp: 2026-08-13T01:10:00Z
  checked: "fix 적용 후 실제 로컬 PostgREST에 대해 (mock 아님) ServiceDb.index_source_chunk_lexical()을 직접 실행"
  found: "예외 없이 성공, result = None (204 응답을 정상적으로 None으로 흡수)"
  implication: "고친 코드가 실제 네트워크 경로에서도 동작함을 실증 — mock 기반 테스트만이 아니라 원래 실패했던 정확한 경로로 종단간 확인."

- timestamp: 2026-08-13T01:12:00Z
  checked: "가드레일 신호 5(revert-and-reconfirm): git stash로 service.py의 fix만 되돌리고(테스트 파일은 유지) 새 회귀 테스트 2건 실행 -> 원복 후 재실행"
  found: "되돌린 상태에서 두 테스트 모두 정확히 동일한 JSONDecodeError: Expecting value: line 1 column 1 (char 0)로 실패(버그 재현 확인). git stash pop으로 fix 복원 후 두 테스트 모두 통과."
  implication: "이 수정이 실제로 버그를 고쳤다는 것이 직접 실증됨 — 우연히 그린이 된 게 아님."

- timestamp: 2026-08-13T01:20:00Z
  checked: "human-verify 체크포인트 — 오케스트레이터가 사용자 대신 로컬 스택(supabase_rest_NexusWiki, supabase_db_NexusWiki)에 대해 apps/worker를 실제로 기동하고, dev-test-workspace에 신규 raw_source + parse job을 직접 삽입해 원래 버그가 재현되던 정확한 경로(claim -> parse -> lexical indexing RPC)를 실사용으로 재현"
  found: "worker.job_claimed(parse) -> worker.parse_chunked(chunk_count=1, 예외 없음) -> worker.job_completed(parse). JSONDecodeError 전혀 없음. 이후 embed/compile/link_sync/conflict_check까지 자동 체인 진행(compile은 실제 OpenRouter LLM 호출까지 성공). 검증용으로 삽입한 raw_source/source_chunk/jobs 6건은 검증 후 전부 삭제해 DB를 사전 상태로 원복 확인(raw_sources=1, source_chunks=8, jobs=1 — 세션 시작 전과 일치)."
  implication: "고쳐진 코드가 목(mock)이 아닌 실제 로컬 PostgREST를 상대로, 원래 버그가 발생했던 정확한 라이브 경로에서 더 이상 죽지 않음을 확인 — 수정이 end-to-end로 검증됨. 별개 이슈로 embed 잡 1건이 OpenRouter 임베딩 400 에러로 실패했으나 JSONDecodeError와 무관하므로 이번 세션 스코프 밖(후속 과제로 남김, 이 세션에서는 조치하지 않음)."

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "worker/db/service.py의 _rpc()(752-769줄)가 PostgREST의 2xx-빈바디 응답(HTTP 204 No Content)을 처리하지 않고 무조건 response.json()을 호출한다. index_source_chunk_lexical/index_wiki_page_lexical은 SQL에서 `returns void`로 선언되어 있고(0011_retrieval.sql:18-58), PostgREST는 void 함수 호출에 204+빈 바디로 응답하므로 .json()이 json.decoder.JSONDecodeError를 던진다. 단일 code 카테고리 결함 — 권한/마이그레이션/환경 문제가 아님(함수 존재·권한 확인됨)."
fix: "worker/db/service.py의 _rpc()에 raise_for_status() 직후, response.json() 호출 전에 단락 처리를 추가: response.status_code == 204 이거나 response.content가 비어 있으면 즉시 None을 반환한다. index_source_chunk_lexical과 index_wiki_page_lexical(둘 다 이 함수 사용)이 204 No Content를 정상 응답으로 처리하게 됨. 다른 _rpc() 호출부(claim_job 등 returns public.jobs/setof 함수)는 항상 JSON 바디가 있는 200 응답을 받으므로 동작 변화 없음."
oracle_type: "specified — PostgREST의 문서화된 void-함수 204 계약과 관찰된 실제 HTTP 응답(curl)을 직접 대조해 기대값을 정했다."
verification:
  target_test: { result: pass, tests: ["apps/worker/tests/test_service_client.py::test_lexical_rpc_helpers_treat_204_no_content_as_none", "apps/worker/tests/test_service_client.py::test_rpc_treats_any_empty_body_as_none_even_with_200_status"] }
  mutation_check: { result: skipped, reason_if_skipped: "Stryker는 JS/TS 전용 — 이 프로젝트의 worker는 Python이라 이 저장소에 구성된 Python 뮤테이션 테스터가 없다" }
  no_op_deletion: { result: pass, deletion_justified_by_rca: n/a, note: "diff는 순수 추가(guard clause + 주석) — 기존 분기/로직을 지우거나 약화시키지 않음" }
  adjacent_tests: { result: pass, suites_run: ["apps/worker/tests (147 passed)", "전체 워크스페이스 pytest — apps/api + apps/worker + packages/core (410 passed)"] }
  revert_and_reconfirm: { result: pass, bug_returned_on_revert: true, fixed_on_reapply: true }
  guardrail_verdict: accepted
human_verify: "confirmed fixed — 오케스트레이터가 사용자 대신 로컬 실사용 경로(worker 기동 -> 소스/parse job 삽입 -> claim -> parse -> lexical indexing)로 라이브 검증 완료. 2026-08-13T01:20:00Z."
files_changed:
  - "apps/worker/src/worker/db/service.py (_rpc()에 204/빈 바디 단락 처리 7줄 추가)"
  - "apps/worker/tests/test_service_client.py (회귀 테스트 2건 + 헬퍼 1개 추가)"
