# Tenant Isolation 리뷰 — ask-replay-retrieval-eval r2

- 판정: pass
- 대상: `main`(`3c62233`) 대비 미커밋 작업 트리 — `scripts/ask_replay.py`(+329), `apps/worker/tests/test_ask_replay_script.py`(+173), `docs/ops/ask-sample-replay.md`(+37), 미추적 `docs/ops/evaluation-map.md`, `openspec/changes/ask-replay-retrieval-eval/`. 재측정 기록 `~/ask-replay-records/2026-11-08-retrieval-r2/retrieval-r2.json`(저장소 밖) 대조
- 일시: 2026-11-08T08:51:24Z

범위 확인: `git status`·`git diff --stat` 기준 변경 경로는 r1과 같다. `supabase/migrations/`(최대 `0036` 그대로), `apps/api/`, `apps/worker/src/`, `apps/web/` 변경 없음. `uv run pytest apps/worker/tests/test_ask_replay_script.py` 새로 실행 — 60 passed.

## r1 지적 해소 확인

| r1 지적 | 결과 | 근거 |
| --- | --- | --- |
| 1. 채널 장애가 난 200 응답을 정상 측정으로 기록 | 해소 | `channel_failures`(`scripts/ask_replay.py:544-554`)가 `meta`의 dict 값 중 `status == "failed"`인 채널을 고른다. 서버가 내는 채널 상태는 `ok`/`failed`/`disabled` 셋이고(`apps/api/src/api/services/retrieval.py:358-384`), 임베딩 실패(`:117-118`)·RPC 실패(`:148`, `:301`)·그래프 RPC 실패(`:272`) 모두 `_failed_meta` → `"failed"`다. 라우터는 `meta`를 그대로 내보낸다(`apps/api/src/api/routers/retrieval.py:108`). 그래프 `disabled`는 장애로 세지 않는다(테스트 `test_channel_failures_reads_failed_channels_from_meta`). 실패 채널이 있으면 `status="channel_failed"`(`:1112-1113`), 행에 `failed_channels`가 남고(`:1123`), `summarize_retrieval`이 `status != "ok"` 행의 결과를 버려 미적중으로 센다(`:598-599`, `:620-621`). `policy_versions`는 기록 최상위에 남고(`:1087-1088`, `:1138`) `retrieval_compare_table`이 표 머리에 양쪽 값을 적는다(`:664-665`, 없으면 "알 수 없음"). |
| 2a. 정답 문서 미매핑 시 expected가 빈/부분 집합 | 해소 | 정답 문서 키 중 하나라도 제목 매핑이 안 되면 검색을 부르지 않고 `status="unmapped_expected"` + `unmapped` 목록으로 남긴다(`:1049-1066`). 샘플 키가 `titles`에 없을 때도 `titles.get(d)`가 `None`이라 같은 경로로 간다. 여러 문서 질문의 정답 수는 결과가 아니라 `doc`에서 세므로(`:610-611`, `:613`, `:631-633`) 실패 행이 `multi_doc_all_found`를 부풀리지 않는다(테스트 `test_failed_multi_document_question_stays_in_the_denominator`). |
| 2a'. 같은 제목 raw_source 중복 | 해소 | 중복 제목이면 기록을 쓰기 전에 `SystemExit`(`:1033-1038`). 부분 기록이 남지 않는다. |
| 2b. 청크 조회로도 원문을 못 찾은 근거 | 해소 | `unresolved = [c for c in missing if c not in chunk_sources]`(`:1109`) → `status="unresolved_evidence"`, 행에 개수 기록(`:1114-1115`, `:1124`). 조회 HTTP 실패는 여전히 `raise_for_status`로 실행 전체가 멈춘다(`:700`). |
| append-only | 강화됨 | 시작 전 존재 검사(`:1003-1004`)에 더해 쓰기를 `open("x")`로 한다(`:1143`). 실행 중 같은 경로가 생겨도 덮어쓰지 않는다. |

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `cmd_retrieval_eval`(`scripts/ask_replay.py:1000-1146`)은 `_service_headers()`를 부르지 않는다. `raw_sources`(`:1025-1031`)·`wiki_pages`(`:1039-1045`)·`source_chunks`(`:1097-1107`) 조회는 모두 `_select(..., token=token)`이고 `_select`는 token이 있으면 anon `apikey` + 요청자 Bearer로 보낸다(`:694-698`). 검색 호출(`:1068-1072`)도 요청자 Bearer이며 서버는 `UserDb` + `has_workspace_role` 게이트(`apps/api/src/api/routers/retrieval.py:80-81`)로 처리한다. 세 조회 모두 `workspace_id=eq.<ws>`를 건다(필터 가드 `:692-693`). r2 추가 코드에 새 조회·새 역할 사용 없음 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 마이그레이션 변경 없음 |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | SQL 변경 없음. `LOCAL_ANON_KEY`는 PostgREST `apikey` 헤더일 뿐 역할은 Bearer의 `authenticated`로 정해진다 |
| A-4 | service_role 코드의 workspace_id 명시 필터 | 해당 없음 | 신규 코드에 service_role 경로 없음. 기존 `_select` service_role 분기와 필터 가드는 손대지 않았다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | UPDATE/DELETE 경로 없음(읽기 전용 스크립트) |
| B-7 | 42501 → 403 매핑 | 해당 없음 | 쓰기 경로 없음 |
| C-8 | 핸들러 멱등성 / upsert 키 | 해당 없음 | 작업 핸들러 없음. DB 쓰기 없음. 기록 파일은 `"x"` 모드 |
| C-9 | `jobs` 직접 UPDATE | 해당 없음 | `jobs` 접근 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 검색 SQL·RPC 변경 없음 |
| D-11 | 색인/질의 토크나이저 동일성 | 해당 없음 | 토크나이저 경로 변경 없음. 질의는 API가 `TSV_TOKENIZER_VERSION`과 함께 처리(`apps/api/src/api/services/retrieval.py:276-282`, 기존 코드) |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트·LLM 호출 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 없음 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음 |
| 추가-1 | loopback 가드 | 통과 | `api`(`:1005`)·`stack`(`:1007`) 모두 `assert_loopback`을 거친 뒤에야 `_login`(`:1022`, 자격 증명 전송)과 검색 호출이 일어난다. 덮어쓰기 검사(`:1003`)는 그보다 앞이라 네트워크 없이 거부된다 |
| 추가-2 | 200 응답 안의 채널 장애 | 통과 | 위 「r1 지적 해소 확인」 1 |
| 추가-3 | 정답 문서·근거 원문 해석 실패 | 통과 | 위 2a·2a'·2b |
| 추가-4 | 측정 실패의 분모 유지 | 통과 | `answerable`은 `doc != "none"` 전체(`:595`), 비 ok 행은 결과를 `{}`로 보고 미적중(`:598-599`). `failed_requests`·`status_counts`(`:614-621`)로 보고, 비교 표에도 "측정 실패 질문" 행(`:650`) |
| 추가-5 | 기록·표준 출력의 비밀·본문 | 통과 | 기록(`:1133-1141`)은 `label`·`git_sha`·`k`·`policy_versions`·`rows`·`summary`. 행 키는 `id`·`doc`·`status`·`failed_channels`·`unresolved_evidence`·`evidence_count`·`result`(+`unmapped`의 샘플 문서 키)이고 `ranked`는 `rank/kind/relevant`뿐이다. 실제 기록 파일에서도 같은 키 집합을 확인했고 `eyJ`·`password`·`credential`·`@example.com`·`workspace_id` 검색 0건. 질의문·청크 본문·답변·채널 `raw_hit_ids` 없음. 표준 출력(`:1129-1132`, `:1145`)도 질문 id·순위·요약뿐 |
| 추가-6 | 재측정 기록과 문서 수치 대조 | 일치 | `retrieval-r2.json`: `policy_versions=["hybrid-rrf-v1"]`, `status_counts={"ok": 30}`, `failed_requests=0`, `failed_channels` 비어 있지 않은 행 0, `unresolved_evidence` 합 0. hit@1 0.5517(=16/29), hit@3 0.7931(=23/29), hit@8 1.0, MRR 0.696, 원문 0.931(=27/29), 이중 0.931, 여러 문서 3/3/3, q30 근거 8 — `docs/ops/ask-sample-replay.md`·`docs/ops/evaluation-map.md` 수치와 같다. "상위 6개가 위키, 원문은 7~8위" 서술도 순위 패턴 `WWWWWWSS` 21문항·`WWWWWWSW` 9문항과 맞는다. r1 이전 측정을 "채널 상태를 남기기 전이라 기준으로 쓰지 않는다"고 문서에 적은 것도 r1 조치 1의 요구를 충족한다 |

## 조치가 필요한 항목

없음.

## 참고 (비차단)

판정에 반영하지 않았다. 지금 경로로는 도달하지 않거나 보고값으로 드러나는 것들이다.

1. **위키 근거의 원문 미해결은 여전히 조용한 미적중이다**
   - 위치: `scripts/ask_replay.py:537-538`
   - 내용: 원문 근거는 원문을 못 찾으면 `unresolved_evidence`가 되지만, 위키 근거의 `document_id`가 `wiki_sources`에 없으면 빈 집합 → 비적중으로만 남는다. 페이지 목록은 루프 전에 같은 토큰·같은 RLS로 한 번 읽으므로(`:1039-1046`) 실행 중 페이지가 새로 생기거나(컴파일 작업이 아직 도는 상태) `wiki_pages`가 PostgREST `max_rows = 1000`(`supabase/config.toml:18`)을 넘는 경우에만 일어난다. 현재 픽스처는 13쪽이라 도달하지 않는다. 대칭으로 막으려면 그런 위키 근거도 `unresolved` 개수에 넣으면 된다.
2. **분류 분기 자체를 고정하는 테스트가 없다**
   - 위치: `scripts/ask_replay.py:1033-1038`, `:1049-1066`, `:1109-1117`
   - 내용: 추가된 테스트는 이미 상태가 붙은 행을 `summarize_retrieval`이 어떻게 세는지만 본다. 제목 중복 거부, 미매핑 판정, `unresolved_evidence` 판정, `channel_failed` 우선순위는 `cmd_retrieval_eval` 안에 있어 코드 판독으로만 확인했다. `httpx.MockTransport` 하나로 네 분기를 고정할 수 있다(spec-conformance r1의 권고와 같은 테스트).
3. **답할 수 없는 질문의 근거 수는 채널 장애에도 그대로 실린다**
   - 위치: `scripts/ask_replay.py:634-638`
   - 내용: 채널이 빠지면 q30의 근거가 줄어 "거절에 유리한" 값처럼 보일 수 있다. 다만 같은 기록의 `status_counts`와 행의 `failed_channels`에 장애가 드러나므로 조용하지는 않다.
4. **`meta`가 아예 없는 응답은 `ok`로 간다**
   - 위치: `scripts/ask_replay.py:1086-1089`
   - 내용: 현재 API는 항상 `meta`를 내지만, 응답 형식이 바뀌어 `meta`가 빠지면 장애 판정이 불가능한 채 `ok`가 된다. 이 경우 `policy_versions`가 빈 목록이 되어 비교 표에 "알 수 없음"으로 드러나므로 완전히 조용하지는 않다.

## 판정 근거

r1의 두 지적이 모두 해소됐다. 200 응답 안의 채널 장애는 서버가 실제로 내는 `"failed"` 상태를 읽어 `channel_failed`로 기록하고, 정답 문서 미매핑·근거 원문 미해결은 각자의 측정 실패 상태가 되며, 제목 중복은 실행을 거부한다. 측정 실패는 분모에 남은 채 미적중으로 세고 `failed_requests`·`status_counts`로 보고된다. 새 코드는 service_role을 쓰지 않고 모든 조회·검색을 요청자 토큰과 `workspace_id` 필터로 하며, loopback 가드가 자격 증명 전송보다 앞서고, 기록과 표준 출력에 비밀·본문이 없다. 재측정 기록은 채널 장애 0건·측정 실패 0건이며 문서 수치와 일치한다. DB·RLS·API·마이그레이션 변경이 없어 테넌트 경계에 닿는 경로가 없다. 참고 항목은 현재 도달하지 않거나 기록에 드러나는 것이라 `pass`로 판정한다.
