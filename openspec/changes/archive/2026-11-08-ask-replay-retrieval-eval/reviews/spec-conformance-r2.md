# Spec Conformance 리뷰 — ask-replay-retrieval-eval r2

- 판정: needs_fix
- 대상: `main`(`3c62233`) 대비 브랜치 `feat/ask-replay-retrieval-eval`의 미커밋 변경. `scripts/ask_replay.py`, `apps/worker/tests/test_ask_replay_script.py`, `docs/ops/ask-sample-replay.md`, 미추적 `docs/ops/evaluation-map.md`, `openspec/changes/ask-replay-retrieval-eval/`
- 일시: 2026-11-08T00:00:00+09:00
- 새로 실행한 검증: `uv run pytest apps/worker/tests/test_ask_replay_script.py -q` → 60 passed. `openspec validate ask-replay-retrieval-eval --strict` → valid
- 추가 확인: `httpx.MockTransport`로 `cmd_retrieval_eval`을 직접 실행하는 일회용 탐침(스크래치패드, 저장소 밖)으로 상태 분기와 제목 중복 거부를 확인했다. 결과는 아래 표의 "탐침"으로 표시한다. 탐침은 저장소 테스트가 아니므로 테스트 증거로 세지 않는다.

## r1 지적 해소 여부

| r1 항목 | 결과 | 증거 |
| --- | --- | --- |
| spec r1 조치 1: 실패한 여러 문서 질문이 multi_doc 분모에서 빠짐 | 해소 | 여러 문서 여부와 정답 문서 수를 `doc` 필드로 센다 `scripts/ask_replay.py:610-613`. `status != "ok"`인 행은 결과를 빈 dict로 읽어 any/all 모두 미발견 `:598-599`, `:630-633` · 테스트 `apps/worker/tests/test_ask_replay_script.py:552`(정상 `a+b` 둘 다 찾음 + 실패 `c+d` → 분모 2, any 1, all 1) |
| tenant r1 조치 1: 200 응답의 채널 장애를 정상으로 기록 | 해소 | `channel_failures`가 `meta`의 채널별 `status == "failed"`를 읽는다 `:544-554`. API가 실패 채널을 `{"status": "failed", ...}`로 `meta` 최상위에 펼쳐 넣는 것과 맞다(`apps/api/src/api/services/retrieval.py:118`, `:148`, `:174-181`, `:369-380`, 라우터 `apps/api/src/api/routers/retrieval.py:108`). 실패 채널이 있으면 `status="channel_failed"` `:1112-1113` · 테스트 `test_ask_replay_script.py:532`, `:543` |
| tenant r1 조치 1: `policy_version` 미기록 | 해소 | 응답마다 모아 기록에 `policy_versions` `:1087-1088`, `:1137-1138`. 비교 표 머리에 두 기록의 정책 표시 `:664-665` · 테스트 `test_ask_replay_script.py:574` |
| tenant r1 조치 2(a): 정답 문서 미매핑이 조용히 미적중 | 해소 | 정답 문서 중 하나라도 제목 매핑에 실패하면 검색 호출 없이 `status="unmapped_expected"`와 `unmapped` 목록을 남긴다 `:1049-1066`. 일부만 매핑된 정답 집합으로 채점하는 경로가 없어졌다 |
| tenant r1 조치 2(a): 제목 중복 시 마지막 것만 남김 | 해소 | 중복 제목이면 `SystemExit` `:1032-1037`(검색 호출 전) |
| tenant r1 조치 2(b): 청크 조회 누락 근거가 조용히 비적중 | 해소 | `unresolved` 계산과 `status="unresolved_evidence"`, 행에 `unresolved_evidence` 개수 `:1109`, `:1114-1115`, `:1124` |
| spec r1 참고: 쓰기가 `"w"` 모드 | 해소 | `out.open("x")` `:1142-1144` |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Retrieval-only scoring / Relevant source item ranked first | 충족 | `scripts/ask_replay.py:539-541`, `:565-570`, `:622-625` · 테스트 `test_ask_replay_script.py:430`, `:444` |
| Retrieval-only scoring / Relevant wiki item through its compiled sources | 충족 | `:537-538`, `wiki_pages.sources` 사용자 토큰 조회 `:1039-1046` · 테스트 `:449` |
| Retrieval-only scoring / Wiki page compiled from another document | 충족 | `:568` 교집합이 비면 `relevant=False` · 테스트 `:453` |
| Retrieval-only scoring / No relevant item in the top 8 | 충족 | `:622-625`(`first`가 None이면 hit@1·@3·@8 모두 거짓, MRR 0) · 테스트 `:459`(hit@8·MRR 단언) |
| Retrieval-only scoring / Only one side of the dual citation is found | 충족 | `:574-581`, `:626-628` · 테스트 `:468` |
| Retrieval-only scoring / Question with several expected documents | 충족 | `found_count` `:571-573`, any/all `:630-633` · 테스트 `:473` |
| Retrieval-only scoring / Unanswerable question | 충족 | `:595`, `:634-638` · 테스트 `:482` |
| Retrieval-only scoring / Retrieval request fails for a question | 충족 | `status=f"http_{code}"` `:1073-1083`, 실패 수 `:620`, 종류별 `status_counts` `:614-616`, `:621` · 테스트 `:493`(요약). 상태 기록 경로는 탐침으로만 확인(`q3 → http_500`) |
| Retrieval-only scoring / Retrieval succeeds with a failed channel | 충족(연결부 테스트 없음) | `:1089`, `:1112-1113`, 요약에서 미적중 `:598-599` · 테스트 `:532`(채널 판별), `:543`(상태가 찍힌 행의 요약). **HTTP 200 + 실패 채널 응답이 `channel_failed` 행이 되는 연결부는 테스트가 없다.** 탐침: `source_vector` 실패 응답 → `q1 channel_failed`, hit@8 0 |
| Retrieval-only scoring / Expected document cannot be mapped | 충족(연결부 테스트 없음) | `:1049-1066` · 테스트 `:567`은 `status="unmapped_expected"`가 **미리 찍힌 행**을 요약할 뿐이다. WHEN("제목이 맞는 raw_source가 없음")에서 그 상태가 나오는 경로는 테스트가 없다. 탐침: `c` 미수집 → `q2 unmapped_expected`, 검색 호출 없음 |
| Retrieval-only scoring / Failed multi-document question | 충족 | `:610-613`, `:630-633` · 테스트 `:552` |
| Retrieval-only scoring / Duplicate raw source titles | 충족(테스트 없음) | `:1032-1037` · **대응 테스트 없음.** 탐침: 제목 `A` 중복 → `SystemExit("제목이 같은 원문이 둘 이상이다: A")`, 검색 호출 0회, 기록 파일 없음 |
| Retrieval-only scoring / 원문 근거 추적 실패를 측정 실패로 (Requirement 본문) | 충족(테스트 없음) | `:1090-1115`. 테스트 없음. 탐침: `metadata.raw_source_id` 없고 청크 조회 빈 결과 → `unresolved_evidence` |
| Retrieval-only scoring / 지표 정의 문구 (Requirement 본문) | 충족 | `:519-523`, `:618`, `:663` · 테스트 `:503` |
| Retrieval-only scoring / 답변 생성 공급자 미호출 (Requirement 본문, MUST NOT) | 충족(코드 판독 + 탐침) | 호출 대상은 로그인, `/health`, PostgREST 3개 테이블, `/workspaces/{id}/retrieval`뿐 `:1021-1108`. 탐침의 호출 URL 중 `/ask` 계열 0건 |
| Retrieval-only scoring / 요청자 토큰 (Requirement 본문) | 충족 | `:1030`, `:1044`, `:1070`, `:1106` |
| Append-only records / Output path already exists | 충족 | 함수 첫 검사 `:1001-1004`, 쓰기도 `"x"` 모드 `:1143` · 테스트 `:507` |
| Append-only records / 기록 내용과 금지 항목 (Requirement 본문) | 충족(테스트 없음) | `label`·`git_sha`·`k`·`policy_versions`·`rows`(상태 포함)·`summary` `:1133-1141`. 탐침: 기록 키가 정확히 이 6개이고 `credential` 문자열 없음 |
| Append-only records / Two records compared | 충족 | 공통 질문으로 양쪽 재계산 `:656-659`, 지표 나란히 `:670-671`, 정책 버전 `:664-665` · 테스트 `:518`, `:574` |

## 조치가 필요한 항목

1. **"Duplicate raw source titles" 시나리오에 테스트가 없다** — 코드(`scripts/ask_replay.py:1032-1037`)는 맞게 동작하지만 이를 고정하는 테스트가 저장소에 없다. 근거 Scenario: "WHEN two raw sources in the workspace share a title THEN the run refuses to start". 제안: `httpx.Client`를 `httpx.MockTransport`로 바꿔 `cmd_retrieval_eval`을 실행하는 테스트를 추가한다. `raw_sources` 응답에 같은 제목 두 행을 주고, `SystemExit`과 `/retrieval` 호출 0회, 출력 파일 미생성을 단언한다.

2. **측정 실패 상태를 정하는 경로(`cmd_retrieval_eval`)가 테스트되지 않는다** — 새 테스트 `test_ask_replay_script.py:543`, `:567`은 `status`가 이미 `channel_failed`/`unmapped_expected`로 찍힌 행을 손으로 만들어 `summarize_retrieval`만 검증한다. "HTTP 200 + 실패 채널 → `channel_failed`"(`:1112-1113`), "정답 제목 미매핑 → `unmapped_expected`, 검색 호출 없음"(`:1049-1066`), "원문 추적 실패 → `unresolved_evidence`"(`:1109-1115`)라는 WHEN→상태 연결은 테스트가 없어서, 이 분기가 회귀해도 60개 테스트가 모두 통과한다. r1 참고 항목에서 이미 같은 공백을 짚었다. 근거 Scenario: "Retrieval succeeds with a failed channel", "Expected document cannot be mapped". 제안: 1번의 가짜 전송 테스트 하나로 질문 네 개(실패 채널 200, 미매핑 정답, HTTP 500, 추적 불가 원문)를 돌려 각 행의 `status`, `summary.status_counts`, `policy_versions`, 기록 키 집합(자격 증명·답변 없음)을 함께 단언한다. 이번 리뷰의 탐침이 그 형태로 모두 기대대로 나왔으므로 코드 수정 없이 테스트만 추가하면 된다.

3. **tasks.md에 r1 반영 범위가 없다** — r1 수정으로 스펙에 측정 실패 규칙과 시나리오 4개(채널 장애, 매핑 실패, 실패한 여러 문서 질문, 제목 중복)와 `policy_versions` 기록이 추가됐지만 `tasks.md`는 바뀌지 않았다. 3.1의 시나리오 목록은 r1 이전 10개 그대로이고, 2.x에는 채널 장애·매핑 실패·제목 중복·정책 버전 기록 task가 없다. 추가 동작은 delta spec에 있으므로 스펙 밖 동작은 아니지만, 완료 표시가 실제 범위를 덮지 못한다. 제안: 2.x에 해당 task를, 3.1(또는 새 3.2)에 새 시나리오 테스트를 추가하고 1·2번 테스트가 들어간 뒤에 체크한다.

## 참고(판정에 반영하지 않음)

- 답할 수 없는 질문도 `unresolved_evidence`나 `channel_failed`가 되면 `failed_requests`에 들어간다(탐침의 `q4`). hit/rank 분모에는 영향이 없고 "측정 실패를 종류별로 보고"와 어긋나지 않는다. 다만 `failed_requests`라는 이름과 비교 표의 "측정 실패 질문"은 답할 수 없는 질문을 포함한 수라는 점을 문서에 적어 두면 읽는 사람이 헷갈리지 않는다.
- 상태가 둘 이상 해당하면(채널 장애와 원문 추적 실패) `channel_failed`가 우선한다(`:1112-1117`). 행에 `failed_channels`와 `unresolved_evidence` 개수가 함께 남으므로 정보는 사라지지 않는다.
- `state["documents"]`는 수집을 시도한 문서 목록이라(`:797-802`) 수집에 실패한 문서의 질문은 `seeded` 필터에서 빠지지 않고 `unmapped_expected`로 잡힌다. 의도대로다.
- 문서(`docs/ops/ask-sample-replay.md`)는 재측정 결과에 "채널 장애 0건, 측정 실패 0"을 적고, 채널 상태를 남기기 전 측정을 기준으로 쓰지 않는다고 밝혔다. tenant r1의 문서 조치와 맞다.

## 판정 근거

r1의 지적(실패한 여러 문서 질문의 분모 이탈)과 tenant r1의 두 지적(채널 장애, 매핑·추적 실패의 조용한 미적중)은 모두 코드에서 해소됐고, 추가된 시나리오 4개를 포함한 모든 시나리오의 동작이 코드 판독과 가짜 전송 탐침에서 스펙과 맞았다. 남은 문제는 동작이 아니라 검증이다. "Duplicate raw source titles" 시나리오는 테스트가 전혀 없고, "failed channel"과 "cannot be mapped" 시나리오는 WHEN에서 상태가 정해지는 경로가 테스트되지 않아 그 분기가 깨져도 테스트가 통과한다. tasks.md도 늘어난 범위를 담지 못한다. 스펙을 바꿀 필요 없이 가짜 전송 테스트 하나와 tasks.md 갱신으로 해결되므로 `needs_fix`다. 다음 라운드(r3)가 리뷰 게이트의 마지막 라운드다.
