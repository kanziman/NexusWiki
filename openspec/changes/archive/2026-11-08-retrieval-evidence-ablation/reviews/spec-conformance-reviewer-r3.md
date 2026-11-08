# Spec Conformance 리뷰 — retrieval-evidence-ablation r3

- 판정: pass
- 대상: 커밋되지 않은 작업 트리 (`git diff` + 미추적 파일, 기준 `016ad7b18ad131ce28997df1c297acae8cddfb6c`, 브랜치 `feat/retrieval-evidence-ablation`)
- 일시: 2026-11-08T12:52:21Z
- 새로 실행한 검증: `uv run pytest packages/core/tests/test_retrieval_golden.py apps/api/tests/test_retrieval_service.py apps/worker/tests/test_retrieval_ablation_script.py` → 90 passed. `ruff format --check`(변경 파일 7개) 통과. `ruff check .`은 43건을 냈지만 전부 `scripts/benchmark_retrieval.py`(13)와 `scripts/generate_retrieval_benchmark_corpus.py`(30)에 있고 `retrieval_ablation` 파일에는 없다. `benchmark_retrieval.py`는 HEAD 판도 같은 13건이라 이번 변경에서 생긴 것이 아니다. `openspec validate retrieval-evidence-ablation --strict` → valid
- 추가 확인: 테스트 헬퍼로 답변 기록과 검색 기록을 만들고 `publishable`의 요약 키와 비용, 그리고 답변 행의 `succeeded_channels`를 직접 출력했다. 출력한 경우는 실패 채널이 있는 행과 미실행 행이다. 유료 호출, DB 쓰기, 서버 실행은 하지 않았다. DDL·insert의 실제 DB 동작은 호출자가 롤백 트랜잭션으로 확인했다고 보고했지만, 이 리뷰에서 재현하지는 않았다.

## r2 지적 사항 해소 여부

| r2 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. 공개 필드에 규칙이 섞인 `pass_rate` | 해소 | `_PUBLISHABLE_SUMMARY_KEYS`에서 `pass_rate`를 뺐다. 이제 `product_pass_rate`와 `diagnostic_pass_rate`만 공개한다 `scripts/retrieval_ablation.py:1331-1351`. 공개 요약은 이 목록만 통과시킨다 `:1363`. 실측한 공개 요약 키에도 `pass_rate`가 없다. 내부 `summary.pass_rate`는 기록 본문에 남지만 비교 표(`_ANSWER_ROWS` `:1020-1029`)와 공개 필드 어디에도 노출되지 않는다. 테스트 `apps/worker/tests/test_retrieval_ablation_script.py:872`는 단일 근거 조건의 `product_pass_rate`가 None이고 `both`의 `diagnostic_pass_rate`가 None인지 확인한다 |
| 2. 공개 비용의 범위 표시와 재사용 제목 벡터 비용 | 해소 | 공개 비용은 기록의 `cost`를 그대로 복사한다 `scripts/retrieval_ablation.py:1384`. 기록 `cost`에는 `embedding_scope`, `reused_query_vectors(_micros)`, `reused_title_vectors(_micros)`가 있다 `:1842-1862`. 실험 테이블에 `cost_micros` 열을 추가했고 `:487`, 기존 테이블은 `alter table ... add column if not exists`로 맞춘다 `:493`. 기존 벡터 키를 조회할 때 비용도 함께 읽고 `:659-676`, insert할 때 비용을 쓴다 `:679-698`. `EmbedBudget.last_cost_micros`가 호출마다 실측한다 `:783-786`. `prepare_title_vectors`는 재사용한 키의 비용을 합산하고 `:804-808`, 새로 만든 비용도 행마다 저장한다 `:841-843` · `:854-856`. 공개 비용에는 식별자나 본문이 없다. 답변 기록의 공개 비용은 `answer_micros`·`answer_cap_micros`뿐이다 `:1449`. 테스트 `test_retrieval_ablation_script.py:882`(공개 비용의 범위 표시), `:904`(생성 비용 7 → 재사용 시 `reused_micros` 7) |
| 3. 답변 행의 성공 채널 | 해소 | `build_answer_record`가 행마다 `succeeded_channels = SCOPES[scope] − failed_channels`를 채우고, 미실행 행에는 빈 목록을 넣는다 `scripts/retrieval_ablation.py:1413-1418`. `failed_channels`는 Ask `meta.missing_channels`에서 온다 `:1300-1313`. 채널 이름 집합 `SCOPES`는 `:80-84`에 있다. 테스트 `test_retrieval_ablation_script.py:923`은 실패 없는 경우만 다룬다. 실패와 미실행 분기는 직접 실행해 확인했다. `wiki_vector`가 실패한 행은 `['source_lexical','source_vector','wiki_lexical']`와 `execution_failure`를, 미실행 행은 `[]`와 `not_run_cap`을 냈다 |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Six-condition matrix / All six conditions share fixed inputs | 충족 | 조건 행렬 `scripts/retrieval_ablation.py:80-88`, 고정 입력 `:196-220`, 6조건 루프 `:1805-1822`. 테스트 `test_retrieval_ablation_script.py:224` |
| Six-condition matrix / A condition was produced from different inputs | 충족 | `_differing_fixed_inputs`·`merge_records` `scripts/retrieval_ablation.py:963-1000`(답변 프롬프트 해시 포함). 질의 벡터 파일의 비용 필드는 해시 입력에 들지 않는다 `:223`. 테스트 `test_retrieval_ablation_script.py:534` · `:839` |
| Title header / Source chunk with a real title | 충족 | `embedding_text` `scripts/retrieval_ablation.py:105`, 실험 함수의 해시식 `:526-530`. 테스트 `test_retrieval_ablation_script.py:334` · `:352` |
| Title header / Section is not available | 충족 | 입력 형식은 `title_body-v1` 하나뿐이다 `scripts/retrieval_ablation.py:88`. 섹션을 입력하는 경로가 없다 |
| Distinguishable vectors / Title changes while body stays the same | 충족 | 재사용 키에 `text_sha256`이 들어간다 `scripts/retrieval_ablation.py:803`. 기본키 `:489`, 검색 시 현재 제목 해시와 일치하는 행만 쓴다 `:526-530` · `:561-565`. 비용 열 추가는 키와 재사용 판정을 바꾸지 않는다. 테스트 `test_retrieval_ablation_script.py:415` · `:904` |
| Distinguishable vectors / Product request runs during an experiment | 충족 (구조적 증거만) | 제품 소스(`apps/api/src`, `apps/worker/src`, `packages/core/src`, `supabase`의 `.py`·`.sql`)에 `ablation` 참조가 없다. 스키마 권한도 회수한다 `scripts/retrieval_ablation.py:474`. r1·r2와 같다 |
| Evidence scope / Wiki-only scope | 충족 | `scope_policy` `scripts/retrieval_ablation.py:120`. 검색 행의 `disabled_channels`·`succeeded_channels`는 `:339-348`에 있다. 테스트 `test_retrieval_ablation_script.py:111` · `:122` · `:863`, `apps/api/tests/test_retrieval_service.py` |
| Evidence scope / A channel fails during a condition | 충족 | 검색 단계 `classify` `scripts/retrieval_ablation.py:282-293`, 답변 단계 `turn_row` `:1300-1313`, `answer_verdict` `:1171`, 답변 행의 성공·실패 채널 `:1413-1418`. 테스트 `test_retrieval_ablation_script.py:153` · `:161` · `:820` · `:923` |
| Retrieval-first / Retrieval phase completes | 충족 | `cmd_retrieve`에는 LLM 클라이언트가 없고 `answer_micros: 0`을 기록한다 `scripts/retrieval_ablation.py:1861` |
| Retrieval-first / Selection rule recorded after results | 충족 | `check_registration` `scripts/retrieval_ablation.py:1119`. 테스트 `test_retrieval_ablation_script.py:587` · `:595` |
| Retrieval-first / Spending cap reached | 충족 | `run_answers` `scripts/retrieval_ablation.py:1256-1287`, `EmbedBudget` `:738-787`. `last_cost_micros`를 추가해도 상한 판정식 `:769`는 바뀌지 않았다. 테스트 `test_retrieval_ablation_script.py:635` · `:431` · `:438` · `:445` |
| Diagnostic verdicts / Source-only answer without wiki citation | 충족 | `answer_verdict` `scripts/retrieval_ablation.py:1171-1218`. 테스트 `test_retrieval_ablation_script.py:668` |
| Diagnostic verdicts / Gold document absent from evidence | 충족 | `classify` `scripts/retrieval_ablation.py:282-293`. 테스트 `test_retrieval_ablation_script.py:171` |
| Diagnostic verdicts / Diagnostic result next to product scorecard | 충족 | 공개 요약은 분리된 두 통과율만 싣고 해당하지 않는 쪽은 None이다 `scripts/retrieval_ablation.py:1243-1252` · `:1331-1351`. 비교 표는 두 행으로 나뉜다 `:1024-1025`. 진단 표시는 `:1230` · `:1362`. 테스트 `test_retrieval_ablation_script.py:760` · `:850` · `:872` |
| Append-only record / Output path already exists | 충족 | `scripts/retrieval_ablation.py:1666` · `:1871` · `:1953`, `"x"` 모드 `:1462-1469`. 테스트 `test_retrieval_ablation_script.py:258` · `:274` |
| Append-only record / Question recovers under another condition | 충족 | `transitions` `scripts/retrieval_ablation.py:418`. 테스트 `test_retrieval_ablation_script.py:511` |
| Append-only record / Publication reads the record | 충족 | `publishable` `scripts/retrieval_ablation.py:1354-1386`. 비용 전체를 실어도 식별자나 본문은 새로 들어가지 않는다. 다른 실험은 거부한다 `:985`. 테스트 `test_retrieval_ablation_script.py:734` · `:746` · `:546` · `:882` |
| Product defaults / Experiment completes | 충족 | 워커 임베딩 코드는 바뀌지 않았다. 기본 정책 해시가 보존되는지 `packages/core/tests/test_retrieval_golden.py`가 확인한다 |
| Product defaults / Non-loopback target | 충족 | `assert_loopback` `scripts/retrieval_ablation.py:1669-1670` · `:1956-1957`. 테스트 `test_retrieval_ablation_script.py:292` · `:311` |

## 조치가 필요한 항목

없음.

## 판정 근거

r2에서 남은 3건이 모두 코드와 테스트로 해소됐다. 공개 요약에서는 규칙이 섞인 `pass_rate`가 빠졌다. 공개 비용은 이번 실행분이라는 범위 표시와 재사용한 질의·제목 벡터의 비용을 함께 싣는다. 답변 행은 성공 채널을 명시한다. 수정이 다른 시나리오를 깨지도 않았다. 비용 열은 벡터 기본키와 재사용 판정에 들지 않는다. 질의 벡터 해시는 여전히 벡터만 보므로 고정 입력 대조는 그대로다. `last_cost_micros`를 추가해도 상한 판정식은 바뀌지 않았다. 공개 필드에 새로 들어간 값은 숫자와 불리언뿐이다. 90개 테스트가 모두 통과하고 strict 검증도 valid다. 모든 Scenario를 증거로 확인했으므로 `pass`다.

참고(판정에 반영하지 않음):

- `alter table ... add column if not exists cost_micros ... default 0`(`scripts/retrieval_ablation.py:493`) 때문에 비용 열이 생기기 전에 만든 행은 비용 0으로 읽힌다. 이런 행을 재사용하면 `reused_title_vectors_micros`가 "비용 모름"이 아니라 0으로 과소 기록된다. 다만 실제 실행은 `cleanup`으로 `ablation` 스키마를 지운 뒤 끝났다(tasks 4.2·4.3). 이 열이 없는 옛 테이블이 남는 경우는 정리를 건너뛴 로컬뿐이다. 이 공백을 없애려면 열을 nullable로 두고, null을 "이전 실행분 미포함"으로 기록하면 된다.
- 답변 행 `succeeded_channels`의 실패 차감 분기와 미실행 분기는 전용 테스트가 없다(`test_retrieval_ablation_script.py:923`은 실패 없는 경우만 다룬다). 이 리뷰에서 직접 실행해 동작은 확인했다.
- `test_title_vector_cost_is_stored_and_reported_when_reused`는 `insert_vectors`를 가로채므로, insert SQL에 `cost_micros`가 실리는지는 단위 테스트로 확인하지 않는다. 실제 저장은 호출자가 로컬 DB 롤백 트랜잭션으로 확인했다고 보고했다.
- 이미 쓰인 `retrieve.json`·`answer.json`은 append-only라 r2 이후의 새 필드가 없다. 그 공백은 `verification.md:21`에 공개돼 있다.
- 이번 라운드도 사용자 지시로 tenant-isolation 리뷰를 생략했다.
