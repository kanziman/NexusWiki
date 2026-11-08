# Spec Conformance 리뷰 — ask-replay-retrieval-eval r1

- 판정: needs_fix
- 대상: `main`(`3c62233`) 대비 브랜치 `feat/ask-replay-retrieval-eval`의 미커밋 변경. `scripts/ask_replay.py`, `apps/worker/tests/test_ask_replay_script.py`, `docs/ops/ask-sample-replay.md`, 미추적 `docs/ops/evaluation-map.md`
- 일시: 2026-11-08T00:00:00+09:00
- 테스트: `uv run pytest apps/worker/tests/test_ask_replay_script.py -q` → 55 passed (새로 실행)

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Retrieval-only scoring / Relevant source item ranked first | 충족 | 원문 근거의 raw_source를 `metadata.raw_source_id`, 없으면 청크 조회 값으로 판정 `scripts/ask_replay.py:539-541`. 순위별 적중과 첫 적중 순위 `:552-557`. hit@1·@3·@8·MRR `:596-599` · 테스트 `apps/worker/tests/test_ask_replay_script.py:430`(1위 적중 → 네 지표 모두 1.0), `:444`(청크 id 조회 폴백) |
| Retrieval-only scoring / Relevant wiki item through its compiled sources | 충족 | 위키 근거는 `wiki_pages.sources`로 판정 `scripts/ask_replay.py:537-538`. sources는 사용자 토큰으로 조회 `:1009-1016`. API의 위키 `document_id`가 wiki_id임은 `packages/core/src/nexuswiki_core/rrf.py:65`에서 확인 · 테스트 `test_ask_replay_script.py:449` |
| Retrieval-only scoring / Wiki page compiled from another document | 충족 | 같은 경로에서 교집합이 비면 `relevant=False` `scripts/ask_replay.py:555` · 테스트 `test_ask_replay_script.py:453` |
| Retrieval-only scoring / No relevant item in the top 8 | 충족 | `first_relevant_rank=None` → hit@1·@3은 `(None or 99) <= k`가 거짓, hit@8은 `is not None`이 거짓, MRR 0.0 `scripts/ask_replay.py:596-599` · 테스트 `test_ask_replay_script.py:459`(hit@8·MRR만 단언. hit@1·@3은 코드 판독으로 확인) |
| Retrieval-only scoring / Only one side of the dual citation is found | 충족 | `source_hit`·`wiki_hit`·`dual_hit` `scripts/ask_replay.py:561-568`, 요약 `:600-602` · 테스트 `test_ask_replay_script.py:468`(질문 단위 플래그만 단언, 요약 비율은 같은 플래그의 평균이라 코드 판독으로 확인) |
| Retrieval-only scoring / Question with several expected documents | 충족(정상 응답 한정) | `found_count`/`expected_count` `scripts/ask_replay.py:558-570`, any/all 집계 `:591`, `:603-612` · 테스트 `test_ask_replay_script.py:473`. 단, 실패 요청과 결합하면 아래 조치 1의 결함이 있다 |
| Retrieval-only scoring / Unanswerable question | 충족 | `doc == "none"`을 분모에서 제외 `scripts/ask_replay.py:579`, 근거 건수 별도 보고 `:613-617`, 정답 집합은 빈 집합 `:1019-1023` · 테스트 `test_ask_replay_script.py:482` |
| Retrieval-only scoring / Retrieval request fails for a question | 부분 충족 | 비-200 응답을 `status: "http_<code>"`, `result: None`으로 기록 `scripts/ask_replay.py:1029-1039`. 실패 수 `:595`. hit@k·MRR·원문/위키/이중 적중에서는 미적중으로 센다 · 테스트 `test_ask_replay_script.py:493`. **그러나 여러 문서 질문이 실패하면 any/all 지표의 분모에서 사라진다**(조치 1). 상태 기록 경로(`cmd_retrieval_eval`)는 테스트가 없다(행을 손으로 만들어 요약만 검증) |
| Retrieval-only scoring / 지표 정의 문구를 지표 옆에 적는다 (Requirement 본문) | 충족 | `RETRIEVAL_METRIC_DEFINITION` `scripts/ask_replay.py:519-523`가 요약 `:593`과 비교 표 `:642`에 실린다. 문서 `docs/ops/ask-sample-replay.md` 「검색만 채점」 절 · 테스트 `test_ask_replay_script.py:503` |
| Retrieval-only scoring / 답변 생성 공급자 호출 금지 (Requirement 본문, MUST NOT) | 충족(코드 판독) | `cmd_retrieval_eval`이 부르는 엔드포인트는 auth 토큰 `:998`(→`:723-732`), `/health` `:999`(→`:903-907`), PostgREST 조회 `:1001-1015`·`:1048-1058`, `/workspaces/{id}/retrieval` `:1024-1028`뿐이다. 서버의 검색 경로는 질의 임베딩만 호출하고 답변 생성이 없다 `apps/api/src/api/routers/retrieval.py:82-109`, `apps/api/src/api/services/retrieval.py:111`. 이를 고정하는 테스트는 없다 |
| Retrieval-only scoring / 요청자 토큰 사용 (Requirement 본문) | 충족 | 검색 호출 `Authorization: Bearer {token}` `scripts/ask_replay.py:1026`, 세 조회 모두 `token=token` `:1006`, `:1014`, `:1057`(→`_select`가 anon 키 + 사용자 JWT로 읽음 `:671-675`) |
| Append-only records / Output path already exists | 충족 | 출력 경로 검사가 함수 첫 문장이며 state 읽기·로그인·검색 호출보다 앞선다 `scripts/ask_replay.py:978-981` · 테스트 `test_ask_replay_script.py:507`(존재하지 않는 `missing.json`을 state로 넘겨도 `SystemExit`이 나므로 검사 순서가 state 읽기보다 앞섬이 증명되고, 파일 내용 `{}` 불변 단언) |
| Append-only records / 기록 내용과 금지 항목 (Requirement 본문) | 충족 | 기록은 `label`, `git_sha`, `k`, `rows`, `summary`만 갖는다 `scripts/ask_replay.py:1074-1080`. 행은 `id`·`doc`·`status`·`evidence_count`·`result`(순위별 `rank`/`kind`/`relevant`) `:1030-1037`, `:1061-1068`, `:551-571`. 토큰·이메일·credential·답변·질문 본문 없음. 기록 내용 자체를 단언하는 테스트는 없다 |
| Append-only records / Two records compared | 충족 | 공통 질문 id로 좁힌 뒤 양쪽 요약을 다시 계산 `scripts/ask_replay.py:635-638`, 7개 지표 + 실패 요청 수를 나란히 출력 `:621-630`, `:647-648` · 테스트 `test_ask_replay_script.py:518`(공통 1문항, hit@8 행만 단언) |

## 조치가 필요한 항목

1. **실패한 여러 문서 질문이 "하나라도/전부" 지표에서 조용히 빠진다** — `summarize_retrieval`은 여러 문서 질문을 `result.expected_count > 1`로 고른다(`scripts/ask_replay.py:591`). 요청이 실패한 행은 `result`가 `None`이라 `expected_count`가 0으로 읽혀 `multi_doc_questions` 분모에서 사라진다. 직접 확인: 정상 `a+b` 1건(한쪽만 적중)과 실패 `c+d` 1건을 넣으면 `multi_doc_questions=1, any=1, all=0`이 나온다(기대: 2, 1, 0). 같은 원인으로, `raw_sources.title` 매칭에 실패한 정답 문서는 `expected`에서 빠져(`:1022`) `expected_count`가 줄고 "전부 찾음"이 부풀 수 있다. 근거 Scenario: "the question is recorded as failed with its status, counts as not found **in every metric**" 및 "counts as found under 'any expected document' and not found under 'every expected document'". design.md 결정 7("조용히 빼면 분모가 줄어 지표가 좋아 보인다")과도 어긋난다. 제안: 여러 문서 여부와 정답 문서 수를 행의 `doc` 필드(`len(doc.split("+"))`)로 정하고, `result`가 없거나 실패한 행은 any/all 모두 미발견으로 센다. `test_failed_request_counts_as_not_found_and_is_reported`에 여러 문서 실패 행을 더해 `multi_doc_questions`가 줄지 않음을 단언한다.

## 참고(판정에 반영하지 않음)

- 실패 상태를 기록하는 `cmd_retrieval_eval`의 분기(`:1029-1039`)와 "답변 생성 공급자 미호출"은 코드 판독으로만 확인했다. 가짜 `httpx` 전송(`httpx.MockTransport`)으로 비-200 응답 행의 `status`와 호출된 URL 목록(`/ask` 계열 없음), 기록에 `credential`·`access_token`·`answer` 키가 없음을 단언하는 테스트 하나가 있으면 세 주장이 함께 고정된다.
- 연결 오류(`httpx.TransportError`)나 `source_chunks` 조회 실패는 행으로 기록되지 않고 실행 전체가 예외로 끝난다(기록 파일 없음). 스펙의 "endpoint returns an error"는 HTTP 오류 응답으로 읽어 미충족으로 보지 않았다.
- 덮어쓰기 거부는 시작 시점 검사이며 마지막 쓰기는 `write_text`(`"w"` 모드, `:1081`)다. 실행 중 같은 경로가 생기면 덮어쓴다. 시나리오는 충족하지만 `open(out, "x")`로 쓰면 경쟁 구간도 닫힌다.
- "source-only hit@8"을 구현은 "원문 근거만 보고 센 hit@8"로 정의했다(`:561`, `:600`). 시나리오 5는 이 해석과 "원문만 찾고 위키는 못 찾음" 해석 모두와 맞는다. 문서(`ask-sample-replay.md`)가 앞의 해석으로 일관되게 쓰고 있어 문제 삼지 않았다.
- task 4.1의 측정 기록 파일은 저장소에 없다(작업 트리 밖이거나 무시 경로로 보인다). 결과 수치는 문서에만 있어 이 리뷰에서는 기록 파일 형식을 실물로 대조하지 못했다.

## 판정 근거

13개 판정 항목 중 12개는 코드와 테스트(일부는 코드 판독)로 충족됐다. 특히 덮어쓰기 거부가 state 읽기와 모든 네트워크 호출보다 앞서고, 검색 경로가 답변 생성 공급자를 부르지 않으며, 기록에 답변과 자격 증명이 없다는 점을 확인했다. 남은 하나는 "요청 실패는 모든 지표에서 미발견" 시나리오가 여러 문서 any/all 집계에서 깨지는 것이다. 실패한 여러 문서 질문이 분모에서 빠진다. 이 결함은 스펙을 바꿀 필요 없이 `summarize_retrieval`의 여러 문서 판정을 `doc` 필드 기준으로 바꾸고 테스트를 더하면 고쳐지므로 `needs_fix`다. 첫 실측은 실패 요청이 0이라 이미 발표한 수치는 영향을 받지 않는다.
