# Spec Conformance 리뷰 — retrieval-evidence-ablation r2

- 판정: needs_fix
- 대상: 커밋되지 않은 작업 트리 (`git diff` + 미추적 파일, 기준 `016ad7b18ad131ce28997df1c297acae8cddfb6c`, 브랜치 `feat/retrieval-evidence-ablation`)
- 일시: 2026-11-08T12:48:30Z
- 새로 실행한 검증: `uv run pytest packages/core/tests/test_retrieval_golden.py apps/api/tests/test_retrieval_service.py apps/worker/tests/test_retrieval_ablation_script.py` → 86 passed, `uv run ruff check`·`ruff format --check`(변경 스크립트·테스트) 통과, `openspec validate retrieval-evidence-ablation --strict` → valid
- 추가 확인: 테스트 헬퍼(`_answer_record` · `_evaluate`)로 만든 기록에서 `publishable`의 요약·비용 필드와 `answer_verdict`의 경계 사례를 직접 출력해 봤다. 유료 호출 · DB 쓰기 · 서버 실행은 하지 않았다.

## r1 지적 사항 해소 여부

| r1 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. 답변 단계 채널 장애 | 해소 | `turn_row`가 `meta.missing_channels`를 `failed_channels`로 기록 `scripts/retrieval_ablation.py:1276-1289`. `missing_channels`는 `status == "failed"`만 고르므로 꺼 둔 채널이 섞이지 않음 `apps/api/src/api/services/ask.py:599-610`. `answer_verdict`가 범위 판정보다 먼저 `execution_failure`로 분류 `scripts/retrieval_ablation.py:1162-1168`. 답변 조건에 `enabled_channels` `:1397`. 테스트 `apps/worker/tests/test_retrieval_ablation_script.py:820`. 기존 `answer.json`이 이 정보를 갖지 않는다는 점은 `verification.md:23`에 공개됨 |
| 2. 답변 프롬프트 해시 | 해소 | `merge_records`가 답변 기록끼리 `answer_prompt_sha256`을 대조하고 다르면 이름을 보이며 거부 `scripts/retrieval_ablation.py:965-972`. 주석 정정 `:1409-1410`. 테스트 `test_retrieval_ablation_script.py:839` |
| 3. 통과율 분리 | 부분 해소 | 요약에 `product_pass_rate`/`diagnostic_pass_rate` 분리, 반대쪽 None `scripts/retrieval_ablation.py:1218-1228`. 비교 표 두 행 `:1000-1001`. 문서 `docs/ops/ask-sample-replay.md:131-132`. 테스트 `test_retrieval_ablation_script.py:760` · `:850`. 단, 공개 필드에 규칙이 섞인 `pass_rate`가 그대로 남음 → 조치 1 |
| 4. 비용 | 부분 해소 | 기록 `cost`에 `embedding_scope: this_run_only`, 재사용 여부, 재사용 질의 벡터 비용 `scripts/retrieval_ablation.py:1813-1830`. 질의 벡터 파일이 생성 비용을 가짐 `:1682-1684`(`query_vectors_sha256`은 벡터만 해시해 `:223-226` 고정 입력은 바뀌지 않음). 실제 합계와 경위 `verification.md:21`. 그러나 `publishable.cost`는 `_micros`/`_calls` 접미사만 통과시켜 `embedding_scope`와 `reused_title_vectors`가 빠지고, 재사용 제목 벡터의 비용은 어디에도 남지 않음. 새 필드에 대한 테스트 없음 → 조치 2 |
| 5. 성공 채널 | 검색은 해소, 답변은 미적용 | 검색 행 `succeeded_channels` `scripts/retrieval_ablation.py:344-348` · `:367`, 테스트 `test_retrieval_ablation_script.py:863`. 답변 행은 `failed_channels`만 있고 성공 채널은 조건의 `enabled_channels`와의 차집합으로만 알 수 있음 → 조치 3(경미) |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Six-condition matrix / All six conditions share fixed inputs | 충족 | 조건 행렬 `scripts/retrieval_ablation.py:80-88`, 고정 입력 `:196-220`, 6조건 루프 `:1776-1789`. 테스트 `test_retrieval_ablation_script.py:224` |
| Six-condition matrix / A condition was produced from different inputs | 충족 | 고정 입력 대조 `scripts/retrieval_ablation.py:939-948` · `:965-972`(답변 프롬프트 포함). 테스트 `test_retrieval_ablation_script.py:534` · `:839` |
| Title header / Source chunk with a real title | 충족 | `embedding_text` `scripts/retrieval_ablation.py:105`. 테스트 `test_retrieval_ablation_script.py:334` · `:352` · `:459` |
| Title header / Section is not available | 충족 | 입력 형식은 `title_body-v1` 하나 `scripts/retrieval_ablation.py:88`. 섹션 입력 경로 없음 |
| Distinguishable vectors / Title changes while body stays the same | 충족 | 재사용 판정 `scripts/retrieval_ablation.py:777-835`. 테스트 `test_retrieval_ablation_script.py:415` |
| Distinguishable vectors / Product request runs during an experiment | 충족 (구조적 증거만) | 제품 코드에 `ablation` 참조 없음, 권한 회수 `scripts/retrieval_ablation.py:474`. r1과 같음 |
| Evidence scope / Wiki-only scope | 충족 | `apps/api/src/api/services/retrieval.py`의 `disabled` 메타, `scope_policy` `scripts/retrieval_ablation.py:120`. 테스트 `test_retrieval_ablation_script.py:111` · `:122`, `apps/api/tests/test_retrieval_service.py` |
| Evidence scope / A channel fails during a condition | 충족 | 검색 `classify` `scripts/retrieval_ablation.py:282-293`, 답변 `:1162-1168` · `:1276-1289`. 테스트 `test_retrieval_ablation_script.py:153` · `:161` · `:820` |
| Retrieval-first / Retrieval phase completes | 충족 | `cmd_retrieve`는 LLM 클라이언트 없음, `answer_micros: 0` `scripts/retrieval_ablation.py:1829` |
| Retrieval-first / Selection rule recorded after results | 충족 | `check_registration` `scripts/retrieval_ablation.py:1095-1110`, 호출 `:1928`. 테스트 `test_retrieval_ablation_script.py:587` · `:595` |
| Retrieval-first / Spending cap reached | 충족 | `run_answers` `scripts/retrieval_ablation.py:1232-1263`, `EmbedBudget` `:727`. 테스트 `test_retrieval_ablation_script.py:635` · `:431` · `:445` |
| Diagnostic verdicts / Source-only answer without wiki citation | 충족 | `answer_verdict` 단일 근거 분기 `scripts/retrieval_ablation.py:1175-1193`. 테스트 `test_retrieval_ablation_script.py:668` |
| Diagnostic verdicts / Gold document absent from evidence | 충족 | `classify` `scripts/retrieval_ablation.py:292-293`. 테스트 `test_retrieval_ablation_script.py:171` |
| Diagnostic verdicts / Diagnostic result next to product scorecard | 부분 충족 | 비교 표·운영 문서는 분리됨(위 r1-3). 그러나 공개 필드 `publishable.conditions[].summary`에 단일 근거의 진단 통과율과 `both`의 이중 인용 통과율이 같은 키 `pass_rate`로 실림 `scripts/retrieval_ablation.py:1216` · `:1319`. 실측: `source_onlyxbody` → `pass_rate: 1.0`, `bothxbody` → `pass_rate: 1.0` |
| Append-only record / Output path already exists | 충족 | `scripts/retrieval_ablation.py:1637` · `:1839` · `:1921`, `"x"` 모드 `:1433-1441`. 테스트 `test_retrieval_ablation_script.py:258` · `:274` |
| Append-only record / Question recovers under another condition | 충족 | `transitions` `scripts/retrieval_ablation.py:418`. 테스트 `test_retrieval_ablation_script.py:511` |
| Append-only record / Publication reads the record | 충족 (비용 필드 제외) | `publishable` `scripts/retrieval_ablation.py:1331-1363`, 다른 실험 거부 `:960-964`. 테스트 `test_retrieval_ablation_script.py:734` · `:746` · `:546`. 공개 비용의 범위 표시 누락은 조치 2 |
| Product defaults / Experiment completes | 충족 | 워커 임베딩 코드 변경 없음, 기본 정책 해시 보존 테스트 `packages/core/tests/test_retrieval_golden.py` |
| Product defaults / Non-loopback target | 충족 | `assert_loopback` `scripts/retrieval_ablation.py:1640-1641` · `:1924-1925`. 테스트 `test_retrieval_ablation_script.py:292` · `:311` |

## 조치가 필요한 항목

1. **공개 필드에 규칙이 섞인 `pass_rate`가 남아 있다** — r1-3의 수정으로 요약에 `product_pass_rate`/`diagnostic_pass_rate`가 생겼지만, 공통 키 `pass_rate`(`scripts/retrieval_ablation.py:1216`)도 그대로 두고 `_PUBLISHABLE_SUMMARY_KEYS`(`:1319`)로 공개한다. #230은 `publishable`만 읽는 소비자다. 조건마다 같은 키를 한 열로 모으면 r1-3에서 표와 문서로 막은 비교가 공개 데이터에서 다시 생긴다. `diagnostic`과 `verdict_rule` 표시가 함께 있지만, 같은 키 아래 서로 다른 규칙의 수치가 놓이는 것은 그대로다. 근거 Requirement: "Diagnostic verdicts per condition" — "MUST NOT be reported as or compared with the product scorecard's dual-citation pass rate". 제안: `_PUBLISHABLE_SUMMARY_KEYS`에서 `pass_rate`를 빼고 분리된 두 키만 공개한다. 공개 요약의 단일 근거 조건에 `product_pass_rate`가 None인지 보는 테스트를 추가한다.

2. **공개 비용이 범위 표시 없이 이번 실행분만 담고, 재사용 제목 벡터 비용은 남지 않는다** — 기록 `cost`에는 `embedding_scope: this_run_only`가 있지만, `publishable`의 비용 필터(`scripts/retrieval_ablation.py:1359-1361`, `_micros`/`_calls` 접미사만 통과)가 `embedding_scope`와 `reused_title_vectors`를 떨어뜨린다. 실측 출력은 `{'embedding_micros': 3, 'embedding_calls': 1, 'embedding_cap_micros': 100, 'reused_query_vectors_micros': 60, 'answer_micros': 0}`다. 이것만 읽으면 제목 벡터를 재사용한 사실도, 그 비용이 빠졌다는 사실도 알 수 없다. r1-4가 지적한 "#230이 `publishable`만 읽으면 과소 보고" 문제가 제목 벡터 쪽에 남아 있다. `prepare_title_vectors`(`:777-835`)는 개수만 돌려주고 비용은 `ablation` 행에도 남기지 않는다. 새 비용 필드(`embedding_scope`, `reused_*`, 질의 벡터 파일의 `embedding_micros`)를 확인하는 테스트도 없다. 근거 Requirement: "Append-only reusable experiment record" — "measured cost" 포함, 공개 필드 정의. 설계 D8 — `publishable`에 "비용 합계". 제안: 공개 비용에 `embedding_scope`와 재사용 개수를 함께 싣는다. 예를 들어 필터를 접미사 대신 명시적 키 목록으로 바꾼다. 재사용 제목 벡터 비용은 실험 테이블에 행별 생성 비용을 남겨 합산하거나, 모르면 `reused_title_vectors_micros: null`과 함께 "이전 실행분 미포함"을 명시한다. 기록과 공개 필드에 이 값이 실리는지 테스트를 추가한다.

3. **답변 행에 성공 채널이 명시되지 않는다** (경미) — 검색 행에는 `succeeded_channels`가 생겼지만(`scripts/retrieval_ablation.py:367`), 답변 행은 `failed_channels`(`:1289`)만 있다. 성공 채널은 조건의 `enabled_channels`(`:1397`)와의 차집합으로만 알 수 있다. 이는 r1-5가 지적한 바로 그 형태다. 근거 Requirement: "Evidence scope restricts retrieval channels" — "Each condition record MUST list which channels were active by design, which succeeded, and which failed." 제안: `build_answer_record`에서 행마다 `succeeded_channels = enabled − failed`를 채운다. Ask `meta`는 실패 채널만 주므로 이 차집합이 정확하다. 테스트에서 함께 확인한다.

## 판정 근거

r1의 5건 중 1(답변 채널 장애)과 2(프롬프트 해시)는 코드와 테스트로 완전히 해소됐다. 수정이 다른 시나리오를 깨지 않았다. 질의 벡터 파일에 비용 필드를 추가해도 고정 입력 해시는 벡터만 보므로 바뀌지 않는다. 비교 거부, 진단 표시, append-only 테스트도 모두 통과한다. 남은 것은 3·4·5의 잔여분이다. 공개 필드에 섞인 `pass_rate`, 공개 비용의 범위 표시 누락과 재사용 제목 벡터 비용, 답변 행의 성공 채널이 그것이다. 셋 다 스펙을 바꾸지 않고 `scripts/retrieval_ablation.py`의 공개 필드와 기록 필드를 고치고 테스트를 더하면 해결되므로 `needs_fix`다. 다음 라운드(r3)가 리뷰 게이트의 마지막이다.

참고(판정에 반영하지 않음):

- 답할 수 없는 문항(`doc == "none"`)은 채널이 실패해도 `answer_verdict`가 거절 판정(`refusal_*`)을 먼저 낸다(`scripts/retrieval_ablation.py:1153-1159`. 실측: 채널 실패 + 거절 실패 → `refusal_wrong`). 검색 단계 `classify`도 `unanswerable`을 먼저 내므로 두 단계는 일관된다. 스펙 시나리오가 다루는 "affected question"을 답할 수 있는 문항으로 읽으면 충족한다.
- 기존 `answer.json`·`retrieve.json`은 append-only라 r1 이후 필드가 없다. 그 공백(턴별 채널 상태, 실제 비용 합계)은 `verification.md:21-23`과 `docs/ops/ask-sample-replay.md:153`에 공개됐다.
- 이번 라운드도 사용자 지시로 tenant-isolation 리뷰를 생략했다.
