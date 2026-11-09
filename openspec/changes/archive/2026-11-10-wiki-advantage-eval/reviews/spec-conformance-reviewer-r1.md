# Spec Conformance 리뷰 — wiki-advantage-eval r1

- 판정: blocked
- 대상: `33a4476` 위 미커밋 작업 트리(`git diff` 7파일 +1079/−17, 새 파일 `scripts/fixtures/wiki_advantage.v1.json`)와 실측 원본 `.worktrees/wiki-advantage-20261110/`(`state.json` 제외)
- 일시: 2026-11-09T16:45:03Z

## 새로 실행한 검증

| 명령 | 결과 |
| --- | --- |
| `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_model_evidence_eval_script.py apps/worker/tests/test_retrieval_ablation_script.py apps/worker/tests/test_eval_regression_gate.py -q` | 210 passed |
| `uv run python scripts/check_eval_regression.py` | "합성 답변 30문항의 고정 판정 일치" |
| `uv run python scripts/ask_replay.py check-sample --sample scripts/fixtures/wiki_advantage.v1.json` | exit 0, `multi_doc` · `conflict` · `long_noisy` · `distractor` 각 10, `refusal` 4, 문서 29 |
| `uv run ruff check`(바뀐 5개 파일) · `ruff format --check scripts apps/worker/tests` | 통과. 전체 `ruff check`의 오류 43건은 바뀌지 않은 `benchmark_retrieval.py` · `generate_retrieval_benchmark_corpus.py`에만 있다 |
| `openspec validate wiki-advantage-eval --strict` | valid |
| 시험지 해시 `fingerprint.fixture_sha256` | `43713409…`, `budget.json` · 두 등록의 `fixture_sha256`과 같다 |
| 성적표 재계산(`build_view`, 현재 코드로 원본 재채점) | 전체 `not_supported`, Haiku `supported`(늘 복구 d08 · m02 · m05, 늘 회귀 없음), Luna `not_supported`(c05), 측정 장애 0. 결과 문서와 같다 |

## 요청받은 세 가지 확인

1. **결과를 본 뒤 사전 등록 판정을 바꾸지 않았는가: 바꾸지 않았다.** `effect_criterion {3, 2}`는 첫 유료 답변 호출(무효 점검, 16:05:27Z) 전에 `registration.void-cost.json`(16:05:10Z)에 등록됐고, 재등록 `registration.json`(16:06:34Z)도 같은 값이다. 모든 실행 줄이 재등록 해시 `5f717066…`을 가리킨다. 현재 코드로 다시 계산해도 `not_supported`가 나온다. `docs/ops/ask-sample-replay.md`는 사전 등록 판정을 그대로 적었다. "기대 사실 포함만" 표는 사후 진단이라고 밝히고 "판정으로 쓰지 않는다"고 적었다. DeepSeek은 점검 비용이 가장 커서(2,970 micros, 다른 두 모델은 1,296 · 899) 뺐고, 점검 세 건 모두 `keyword_hit: true`였다. 점검 답의 맞고 틀림이 이 결정에 영향을 줄 여지는 없었다.
2. **기존 30문항 판정이 그대로인가: 그대로다.** 회귀 관문이 일치하고, `test_rows_without_forbidden_field_keep_old_verdict`도 통과한다. 기존 시험지에는 `expect_all`과 `expect_none`이 0건이어서 `retrieval_ablation.turn_row`가 `fact_hit`으로 바뀌어도 값이 같다.
3. **계획 이탈이 스펙 위반인가: 대부분 위반이 아니다. 잡 재시도 한 건은 스펙 해석이 필요하다.** 아래 「계획 이탈 판정」을 본다.

## 시나리오 판정

### wiki-advantage-evaluation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Typed question set / Multi-document fact stated in one document | **부분 충족** | `scripts/ask_replay.py:1021-1026`는 질문의 `doc`에 적힌 문서만 본다. 스펙 본문은 "MUST NOT be stated in **any single source document**"이고, 설계 D3도 "어느 단일 문서에도 없다"다. 이 축소 때문에 실제 시험지 위반 하나를 놓쳤다. **m09**의 기대 사실 `2,400원`이 `doc`에 없는 `l_email`에 그대로 있다("타사 두 곳은 2,400원, 2,500원을 제시"). 테스트 `test_ask_replay_script.py:1180`은 `doc`에 적힌 문서 경우만 다룬다 |
| Typed question set / Conflict question without the old value forbidden | 충족 | `ask_replay.py:1029-1043` · 테스트 `test_ask_replay_script.py:1187` |
| Typed question set / Question without a type | 충족 | 검사 `ask_replay.py:1001-1004`, `seed`가 수집 전에 부름 `:1110-1113` · 테스트 `:1201`, `:1219`(네트워크 호출 전에 거부, state 파일 없음) |
| (본문) 유형별 최소 개수 · `long_noisy` 4,000자 · `distractor` 형제 문서 2개 이상 · 해시 고정 | 충족 | `ask_replay.py:1044-1066`, `budget.json` 해시 = 현재 시험지 해시 · 테스트 `:1209`, `:1239`. 단 `distractor`의 "거의 같은 제목 · 구조"는 `family` 필드로만 대신 검사한다. 실제 제목 3무리는 눈으로 보면 거의 같다(예: "누리해운물류 이천/평택/김해 센터 운영 기준") |
| Fixed cheap compile model / Compile model equals an answer model | 충족 | `model_evidence_eval.py:246`(`budget-open`), `:168`(`register`), 둘 다 모델 이름을 적는다 · 테스트 `test_model_evidence_eval_script.py:745`, `:750` |
| Fixed cheap compile model / One compile job failed | 충족(코드) · 해석 필요(실측) | `model_evidence_eval.py:274-288`, `replay_cap` `:303-307`이 등록을 거부한다 · 테스트 `:755`, `:771`. 실측 문제는 「조치」 2를 본다 |
| Total budget / Ingestion spent part of the budget | 충족 | `model_evidence_eval.py:1668-1685`(총 상한 − `spent_since(EPOCH)`) · 테스트 `:783`(920,000), `:948`. 실측 890,000 − 22,932 = 867,068 |
| Total budget / Remaining budget too small | 충족 | 기존 `plan_rounds` `model_evidence_eval.py:387` · 테스트 `:229`. 실측 `plan.void-cost.json`이 `rounds 0`과 이유 "최소 2회차도 상한 872233 micros 안에 들어가지 않는다"를 남겼다 |
| Pre-registered effect criterion / Wiki recovers enough questions | 충족 | `model_verdict` `:992-999`, `overall_verdict` `:1002-1008` · 테스트 `:825`, `:896` |
| Pre-registered effect criterion / Wiki shows no difference | 충족 | 같은 함수 · 테스트 `:825`(`not_supported` × 3) |
| Pre-registered effect criterion / Too few complete rounds | 충족 | `MIN_ROUNDS_FOR_VERDICT = 2` · 테스트 `:825`(1회차 → `inconclusive`) |
| Per-type report / Wiki helps only on conflicts | 충족 | `model_summary.by_type` `:964-975`, `_effect_section` `:1288` · 테스트 `:896`(`conflict`만 복구, `multi_doc`은 `[]`) |
| Per-type report / Refusal question differs between conditions | 충족 | 거절은 `counts_for_fact`에서 빠져 `hits` · `by_type`에 없다. 거절 구역은 조건 · 회차별 수를 그린다 · 테스트 `:896`("1회: 1/1 · 2회: 0/1", `r01`이 복구 · 회귀에 없음) |
| (본문) 유형별 **위키 차이** | **미충족** | 스펙은 유형별로 "두 조건의 사실 정답 수, 위키 차이, 늘 복구/회귀"를 요구하고, 설계 D8도 표에 위키 차이를 넣는다. `_TYPE_HEAD`(`:1284`)에는 위키 차이 열이 없다. 실측 `scoreboard.html`도 같다. 위키 차이는 모델 요약 표에 모델 전체 값으로만 있다 |

### ask-replay-scorecard

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Per-question pass verdict / Answerable question meets every criterion | 충족 | `ask_replay.py:216-240` · 기존 테스트 |
| / Question fails on one criterion | 충족(기존) | 테스트 `test_ask_replay_script.py:188` |
| / Several criteria fail at once | 부분 충족 | 코드 순서 `:216-223`과 docstring `:188`은 "상태 → 위조 앵커 → 기대 사실 → 금지 사실 → 이중 인용"이다 · 테스트 `:194`, `:1070`. 그런데 순서를 적어 둔 문서 `docs/ops/ask-sample-replay.md:32`의 통과 조건 · 순서 문단에 **금지 사실이 없다**. 시나리오의 "fixed documented order"가 문서와 어긋난다 |
| / No expected fact defined | 충족(기존) | `keyword_hit is None`이면 건너뜀 `:219` |
| / Answer states a forbidden fact | 충족 | `ask_replay.py:221-223`, 행 기록 `:1268` · 테스트 `:1070`, `:1084` |
| / No forbidden facts defined | 충족 | `forbidden_hit`은 빈 목록이면 `None`(`:139`) · 테스트 `:1079` · 회귀 관문 일치 |
| / 거절 6개 시나리오(정확한 거절 · 모델 거절 · 그래도 답함 · 거절 문구가 뒤에 옴 · 위조 앵커 · 공백 차이) | 충족(이번 변경으로 바뀌지 않음) | `ask_replay.py:203-210` · 테스트 `:203`, `:376`, `:380`, `:384`, `:392`, `:397`, `:402` |
| / Turn did not reach the model | 충족(기존) | `:214-216` · 테스트 `:801` |

### model-evidence-ablation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Per-turn verdicts / Answer ends as a fallback | 충족(기존) | 테스트 `test_model_evidence_eval_script.py:136` |
| / Source-only answer | 충족(기존) | 테스트 `:159`. 금지 사실 분류 `retrieval_ablation.py:1141`은 금지 사실이 정의된 경우에만 동작한다 |
| / Answer lists the old and the new value | 충족 | `turn_row` `retrieval_ablation.py:1262-1264`, `fact_correct` `model_evidence_eval.py:528`, `Harness` `:1566-1567` · 테스트 `:793`. 실측 행에 `qtype` · `forbidden_hit` · `fact_correct`가 있다(`runs/r1-anthropic_claude-haiku-5.5.json`) |
| / Existing sample without types or forbidden facts | 충족 | `row["qtype"] = question.get("type")`(`:1566`)이면 기존 시험지는 `None`이다 · 테스트 `:811`(사실 정답 = 기대 사실 포함). `qtype`이 비는지는 `Harness` 단위 테스트가 없어 코드로만 확인했다 |

## 계획 이탈 판정

| 이탈 | 스펙 위반 여부 |
| --- | --- |
| 월 한도를 REST가 아니라 psql로 설정 | 위반 아님. 스펙은 수단을 정하지 않는다. 설계 D5에 반영했다. `_set_monthly_budget`(`ask_replay.py:1082`)은 UUID와 int만 받는다 |
| 컴파일 모델 qwen → ministral | 위반 아님. qwen 수집은 잡 실패로 재생하지 않았다(스펙 그대로). 새 `budget-open`이 새 컴파일 모델과 새 해시 기록으로 다시 시작했다. 두 시도를 합한 지출 379,847은 $1 이하다. 다만 유효 `budget.json`에는 앞선 시도 지출(107,422)이 기계 기록으로 남지 않고 `verification.md`에만 있다 |
| 답변 모델 3종 → 2종, `register`가 부분집합 허용 | 위반 아님. 효과 기준은 첫 유료 답변 호출 전에 등록됐고 바뀌지 않았다. 비용만으로 뺐다는 주장은 점검 기록과 맞는다. 다만 `min_models: 2`가 그대로라서 실질 기준이 "3개 중 2개"에서 "2개 모두"로 엄격해졌다. 결과를 보기 전에 정한 것이므로 사후 변경은 아니다 |
| 임베딩 잡 `dead` → 재시도 API로 복구 | **해석 필요.** 「조치」 2 |
| `ASK_REPLAY_RESERVE_MICROS` 추가 | 위반 아님. 실험 도구의 환경 변수이고, 사용자가 관찰하는 제품 동작이 아니다 |
| 금지 사실 규칙이 대조로 언급한 옛 값까지 실패로 셈 | 구현 위반 아님. 스펙이 요구한 동작 그대로다(Scenario "Answer lists the old and the new value"). 판정도 바꾸지 않았다. 스펙 설계의 약점이라 후속 change 후보다(Haiku `conflict` 사실 정답이 두 조건 모두 0/10) |

## 조치가 필요한 항목

1. **`multi_doc` 검사 범위가 스펙보다 좁고, 고정된 시험지 m09가 스펙 문구를 어긴다** — `check_typed_sample`은 질문의 `doc`에 적힌 문서만 검사한다(`ask_replay.py:1024`). 그래서 m09의 기대 사실 `2,400원`이 무관한 `l_email`(가온유통 견적 메일의 타사 견적)에 그대로 있는데도 통과했다. 근거 Scenario: "WHEN a `multi_doc` question's expected fact appears verbatim in a single source document THEN the fixture check fails naming that question and document". 실측 영향은 없다. m09는 모든 실행 · 조건에서 `keyword_hit: false`였고, 늘 복구 · 늘 회귀에도 들지 않는다. **사람의 결정이 필요한 이유:** 코드를 스펙대로 고치면(전체 문서 검사) 이미 해시를 고정하고 실측한 시험지가 `check-sample`과 `test_wiki_advantage_fixture_passes_typed_check`에서 실패한다. 시험지를 고치면 해시가 바뀌어 기록된 실측과 저장소 시험지가 어긋난다. 제안은 둘 중 하나를 고르는 것이다. (a) 스펙 문구를 "질문이 가리키는 원문 문서 중 어느 하나에도"로 좁히고, 우연히 같은 값이 다른 문서에 있는 m09는 `verification.md`에 한계로 남긴다. (b) 스펙을 유지하고 코드를 전체 문서 검사로 고친 뒤, m09를 v1의 알려진 위반으로 기록하거나 v2로 재측정한다.
2. **수집 중 실패했다가 재시도로 복구한 잡이 수집 기록에 남지 않았다** — `drain-retry.log` 기준으로 임베딩 잡 4개(`dead` 3, `failed` 1)가 실패했다가 제품 재시도 API와 워커 자동 재시도로 성공했다. `ingest-record`는 그 시점의 상태만 보므로(`model_evidence_eval.py:274`) `ingestion.json`은 `failed_jobs: []`이다. 재생 DB에서도 지금은 `last_error`가 비어 있고 7개 잡이 `attempts > 1`로만 흔적이 남았다. 근거: "MUST record … any failed ingestion job. The experiment MUST NOT start answer replay when any ingestion job failed". 이 스펙은 "실패"가 최종 상태인지, 한 번이라도 실패한 것인지 정하지 않는다. 최종 상태로 읽으면 실측은 유효하다. 컴파일 잡 29개는 모두 첫 시도에 성공했고 위키는 39쪽이다. 한 번이라도 실패한 것으로 읽으면 재생을 하지 말았어야 한다. 제안: 사람이 해석을 정한다. 최종 상태로 정하면 스펙 문구를 "수집 기록 시점에 성공하지 못한 잡"으로 고치고, `ingest-record`가 `attempts > 1`인 잡도 `recovered_jobs`로 남기도록 코드를 보강한다(코드만으로 가능하다).
3. **유형별 표에 위키 차이 열이 없다** — 근거 Requirement "Per-type wiki difference report": "the fact-correct counts of both conditions, **the wiki difference**, … broken down by question type". 제안: `_TYPE_HEAD`와 `_effect_section`에 회차별 `both − source` 열을 더하고, `test_effect_view_by_type_and_refusal_excluded`에서 그 값을 확인한다. 그 뒤 `scoreboard.html`을 다시 그리고 `verification.md`의 sha256을 갱신한다(스펙 안의 코드 수정).
4. **문서에 적은 판정 순서에 금지 사실이 없다** — `docs/ops/ask-sample-replay.md:32`의 통과 조건 · 순서 문단이 금지 사실 이전 순서 그대로다. 근거 Scenario "Several criteria fail at once … in a fixed documented order". 제안: 그 문단에 "기대 사실 다음, 이중 인용 앞에 금지 사실(`expect_none`, 정의가 없으면 건너뜀)"을 넣는다.
5. (경미 · 스펙 문구) **측정 장애 조건의 범위** — 스펙은 "`inconclusive` applies … when **any model** has a measurement failure"라고 쓰는데, 구현(`model_evidence_eval.py:996`, `:1083-1090`)과 설계 D7은 측정 장애를 그 모델에만 적용한다. 그래서 지지 모델이 기준 수 이상이면 다른 모델에 측정 장애가 있어도 전체 판정이 `supported`가 될 수 있다. 이번 실측은 측정 장애가 0이라 결과에 영향이 없다. 제안: sync 전에 스펙 문구를 설계 D7("그 모델에 측정 장애가 있으면")에 맞춘다.

## 판정 근거

이 change의 핵심 무결성은 지켜졌다. 사전 등록 판정은 등록 해시로 묶여 있고, 현재 코드로 다시 계산해도 `not_supported`가 나오며, 결과 문서는 사후 진단을 판정과 분리했다. 기존 30문항 회귀 관문도 그대로다. 그런데도 `blocked`로 판정하는 이유는 두 항목(1, 2)이 코드 수정만으로 닫히지 않기 때문이다. 1은 스펙 문구("any single source document")와 이미 해시로 고정해 실측한 시험지(m09)가 충돌한다. 코드를 스펙에 맞추면 고정된 시험지가 검사에 실패하므로, 스펙을 좁힐지 시험지 위반을 한계로 받아들일지 사람이 정해야 한다. 2는 "failed ingestion job"의 뜻이 정해져 있지 않다. 이 해석에 따라 이번 실측이 유효한지가 갈린다. 두 결정이 내려지면 남은 3 · 4(그리고 1 · 2를 따라 생기는 코드 보강)는 스펙 범위 안의 작은 수정이고, r2에서 확인할 수 있다.
