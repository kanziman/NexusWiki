# Tenant Isolation 리뷰 — ask-replay-retrieval-eval r1

- 판정: needs_fix
- 대상: `main`(`3c62233`) 대비 미커밋 작업 트리 — `scripts/ask_replay.py`(+266), `apps/worker/tests/test_ask_replay_script.py`(+118), `docs/ops/ask-sample-replay.md`(+35), 미추적 `docs/ops/evaluation-map.md`, `openspec/changes/ask-replay-retrieval-eval/`
- 일시: 2026-11-08T08:42:23Z

범위 확인: `git status`와 `git diff --stat` 기준 변경은 위 다섯 경로뿐이다. `supabase/migrations/`, `apps/api/`, `apps/worker/src/`, `apps/web/` 변경은 없다(최대 마이그레이션 번호 `0036` 그대로).

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `cmd_retrieval_eval`(`scripts/ask_replay.py:977-1083`)은 `_service_headers()`를 부르지 않는다. `raw_sources`(`:1001-1007`), `wiki_pages`(`:1009-1015`), `source_chunks`(`:1050-1058`) 조회는 모두 `_select(..., token=token)`이고, `_select`(`:671-675`)는 token이 있으면 `apikey=LOCAL_ANON_KEY` + 요청자 Bearer로 보내 RLS 아래에서 읽는다. 검색 호출(`:1024-1028`)도 요청자 Bearer이며, 서버 쪽 `apps/api/src/api/routers/retrieval.py:80-81`은 `UserDb` + `has_workspace_role` 게이트로 처리한다. 세 조회 모두 `workspace_id=eq.<ws>` 필터도 건다(`_select`의 필터 가드 `:669-670` 통과). |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 마이그레이션 변경 없음 |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | SQL 변경 없음. `LOCAL_ANON_KEY`는 PostgREST `apikey` 헤더용일 뿐 역할은 Bearer의 `authenticated`로 결정된다 |
| A-4 | service_role 코드의 workspace_id 명시 필터 | 해당 없음 | 신규 코드에 service_role 경로가 없다. (참고: 기존 `_select`의 service_role 분기는 이번 diff에서 손대지 않았고 필터 가드도 유지된다) |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | UPDATE/DELETE 경로 추가 없음(읽기 전용 스크립트) |
| B-7 | 42501 → 403 매핑 | 해당 없음 | 쓰기 경로 추가 없음 |
| C-8 | 핸들러 멱등성 / upsert 키 | 해당 없음 | 신규 작업 핸들러 없음. 기록 파일은 덮어쓰기 거부(`:980-981`), DB 쓰기 없음 |
| C-9 | `jobs` 직접 UPDATE | 해당 없음 | `jobs` 접근 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 검색 SQL·RPC 변경 없음(기존 API를 호출만 함) |
| D-11 | 색인/질의 토크나이저 동일성 | 해당 없음 | 토크나이저 경로 변경 없음. 질의는 API가 기존대로 처리 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 변경 없음. LLM 호출 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 없음 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음 |
| 추가-1 | loopback 가드 | 통과 | `api`(`:982`)와 `stack`(`:984`) 모두 `assert_loopback`을 거친 뒤에야 `_login`(자격 증명 전송)·검색 호출이 일어난다. `urlparse().hostname` 비교라 `http://127.0.0.1@evil.example`이나 `127.0.0.1.evil.example`도 거부된다 |
| 추가-2 | 원문 근거 raw_source 해석 | 통과(주의 1건) | API 확인: 원문 근거는 `id == document_id == chunk_id`(`packages/core/src/nexuswiki_core/rrf.py:39-48`), `metadata.raw_source_id`는 RPC 행에 있을 때만 실린다(`apps/api/src/api/services/retrieval.py:316`). 스크립트는 metadata를 먼저 쓰고 없으면 청크 id로 조회한다(`:540`, `:1041-1059`). 조회 HTTP 실패는 `raise_for_status`로 실행 전체가 멈춰 조용하지 않다. 단, 조회가 **성공했지만 행이 빠진 경우**는 아래 조치 2 참조 |
| 추가-3 | 위키 근거 raw_source 해석 | 통과 | `wiki_pages.sources`는 raw_source id 문자열 배열이다(`apps/worker/src/worker/handlers/compile.py:516-`, `apps/worker/src/worker/db/service.py:430`의 `cs.["…"]`). `str(x)` 비교가 맞다 |
| 추가-4 | 정답 제목 미매핑 시 expected 빈 집합 | **위반** | `:1019-1023` — 아래 조치 2 |
| 추가-5 | 요청 실패의 분모 유지 | 통과 | 비 200은 `status=http_<code>`, `result=None`으로 남고(`:1029-1039`), `summarize_retrieval`은 `doc != "none"`인 행 전부를 분모로 쓴다(`:582-596`). 네트워크 예외는 잡지 않아 실행 전체가 멈춘다(조용하지 않음). 테스트 `test_failed_request_counts_as_not_found_and_is_reported`가 고정한다 |
| 추가-6 | 200이지만 채널이 실패한 응답 | **위반** | `:1040-1072` — 아래 조치 1 |
| 추가-7 | 기록 파일의 비밀·본문 유출 | 통과 | 기록(`:1074-1081`)은 `label`·`git_sha`·`k`·`rows`(질문 id, doc 키, status, evidence_count, 순위별 `rank/kind/relevant`, 집계)·`summary`뿐이다. 토큰·이메일·credential·workspace_id·질의문·청크 본문·답변이 없다. 표준 출력(`:1067-1070`, `:1082`)도 같다. 문서 diff에도 키·토큰 없음 |

## 조치가 필요한 항목

1. **채널 장애가 난 200 응답을 정상 측정으로 기록한다** (심각도: 높음)
   - 위치: `scripts/ask_replay.py:1040-1072` (응답의 `meta`를 읽지 않음), `:1074-1080` (기록에 `meta`·`policy_version` 없음)
   - 깨지는 것: 검색 API는 채널 실패를 예외가 아니라 **200 + 빈 채널**로 돌려준다. 임베딩 서버가 안 떠 있으면 `wiki_vector`·`source_vector`가 `embedding_unavailable`로(`apps/api/src/api/services/retrieval.py:116-118`), RPC가 실패하면 `rpc_unavailable`로(`:148`, `:300-301`) 빠지고 나머지 채널로만 RRF가 돈다. 스크립트는 이 응답을 `status="ok"`로 세므로 `failed_requests=0`인 채 hit@k·이중 적중이 내려간 기록이 append-only 기준선으로 남는다. 이후 `retrieval-compare`는 이 하락을 코드 변경의 효과로 보여 준다. `policy_version`도 기록하지 않아 두 기록이 같은 정책에서 잰 것인지 비교 시 확인할 수 없다. 문서에 실린 첫 측정의 "상위 6개가 위키, 원문은 7~8위" 관찰도 원문 벡터 채널 장애와 기록만으로 구별할 수 없다.
   - 조치: 응답 `meta`에서 채널별 `status`/`error_code`를 읽어, 하나라도 `ok`가 아니면 그 질문을 `status="degraded:<channel>:<code>"` 같은 비 ok 상태로 기록해 `failed_requests`에 잡히게 한다(또는 실행을 멈춘다). 질문별로 `meta.policy_version`과 채널 상태 요약을 행에 남기고, `retrieval_compare_table`은 두 기록의 `k`·`policy_version`이 다르면 표 머리에 명시한다. 첫 측정 수치는 채널 상태를 확인한 재측정으로 확정하거나, 확인되지 않았다고 문서에 적는다. 테스트: degraded meta를 가진 200 응답이 실패로 집계되는 시나리오.

2. **정답 문서나 근거 원문을 못 찾으면 조용히 미적중이 된다** (심각도: 보통)
   - 위치: `scripts/ask_replay.py:1019-1023` (`if titles[d] in raw_by_title`로 미매핑 문서를 버림), `:540` + `:1059` (청크 조회 결과에 없는 근거는 origin 빈 집합)
   - 깨지는 것: (a) 답할 수 있는 질문의 정답 제목이 `raw_sources.title`과 맞지 않으면(수집 실패로 행이 없음, 제목 정규화, RLS로 안 보임) `expected`가 빈 집합 또는 일부가 되고, 질문은 `status="ok"`인 채 모든 지표에서 미적중으로 들어간다. 여러 문서 질문은 `expected_count`가 줄어 `multi_doc_all_found`가 오히려 **부풀려진다**. 현재 픽스처는 제목 8개가 유일하고 공백 문제가 없어 지금은 맞게 매핑되지만, 막는 가드는 없다. 같은 제목 raw_source가 둘이면 dict가 마지막 것만 남겨 다른 쪽 근거를 미적중으로 센다. (b) `metadata.raw_source_id`가 없는 원문 근거를 청크 조회했는데 결과에 그 청크가 없으면 origin이 빈 집합이 되어 그 근거는 조용히 비적중이 된다(조회 자체는 성공이라 예외가 안 난다).
   - 조치: `doc != "none"`인데 `len(expected) != len(doc.split("+"))`이면 그 질문을 `status="unmapped"`로 기록해 `failed_requests`에 잡히게 하거나 실행을 멈춘다. `raw_sources` 제목 중복이면 멈춘다. 청크 조회 뒤 `set(missing) - set(chunk_sources)`가 비어 있지 않으면 행에 `unresolved_evidence` 개수를 남기고 요약에 합계를 둔다(0이 아니면 그 기록은 신뢰하지 않는다). 테스트: 미매핑 정답 문서 시나리오, 청크 미해결 시나리오.

## 판정 근거

테넌트 경계는 넘지 않는다. 새 명령은 service_role을 쓰지 않고 모든 조회와 검색을 요청자 토큰과 `workspace_id` 필터로 하며, 두 URL 모두 loopback 가드를 먼저 통과하고, 기록에 비밀이나 본문이 없다. DB·RLS·API·마이그레이션 변경도 없음을 확인했다. 그러나 이 change의 산출물은 앞으로 검색 변경을 판정할 append-only 기준선이고, 두 경로에서 측정 오류가 `status="ok"`로 기록되어 지표만 조용히 낮아진다(조치 1: 200 응답 안의 채널 장애, 조치 2: 정답·근거 원문 해석 실패). 요청 실패를 분모에 남긴 설계 의도(design 결정 7)가 이 두 경로에서는 지켜지지 않는다. 코드 수정으로 해결되므로 `needs_fix`다.
