# Spec Conformance 리뷰 — ask-replay-retrieval-eval r3

- 판정: pass
- 대상: `main`(`3c62233`) 대비 브랜치 `feat/ask-replay-retrieval-eval`의 미커밋 변경. `scripts/ask_replay.py`, `apps/worker/tests/test_ask_replay_script.py`, `docs/ops/ask-sample-replay.md`, 미추적 `docs/ops/evaluation-map.md`, `openspec/changes/ask-replay-retrieval-eval/`
- 일시: 2026-11-08T17:54:15+09:00
- 새로 실행한 검증: `uv run pytest apps/worker/tests/test_ask_replay_script.py -q` → 62 passed(r2 대비 +2). `openspec validate ask-replay-retrieval-eval --strict` → valid
- 추가 확인(변이 탐침): 스크립트와 테스트를 스크래치패드에 복사해 상태 분기 4곳을 하나씩 무력화하고 테스트를 돌렸다. 저장소 밖의 일회용 확인이며 저장소 코드는 바꾸지 않았다.

| 무력화한 분기 | 실패한 새 테스트 |
| --- | --- |
| 제목 중복 거부 `scripts/ask_replay.py:1036` | `test_command_refuses_duplicate_titles_before_any_retrieval` |
| 채널 장애 `:1112` | `test_command_assigns_each_measurement_failure_from_real_branches` |
| 매핑 실패 `:1054` | 같은 테스트 |
| 원문 추적 실패 `:1114` | 같은 테스트 |

(복사본에는 샘플 데이터 파일이 없어서 `test_sample_*` 2개가 모든 변이에서 함께 실패했다. 환경 탓이며 변이와 관계없다.) 즉 r2에서 지적한 "분기가 회귀해도 테스트가 통과한다"는 공백이 닫혔다.

## r2 지적 해소 여부

| r2 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. "Duplicate raw source titles" 시나리오 테스트 없음 | 해소 | `apps/worker/tests/test_ask_replay_script.py:719-729`. `raw_sources`에 제목 `A` 두 행 → `SystemExit`, 기록 파일 미생성 단언. `retrieval={}`이라 검색이 한 번이라도 호출되면 핸들러 `:637-640`에서 `KeyError`가 나서 `SystemExit` 단언이 깨지므로 "검색 호출 전 거부"도 사실상 고정된다 |
| 2. 상태를 정하는 `cmd_retrieval_eval` 경로 미검증 | 해소 | `test_ask_replay_script.py:594-666`이 `httpx.Client`를 `MockTransport`로 바꿔 실제 명령을 실행한다. `:669-716`이 질문 5개의 상태(`ok`·`channel_failed`·`unmapped_expected`·`unresolved_evidence`·`http_500`), 매핑 실패 질문의 검색 미호출 `:711`, `policy_versions` `:712`, `failed_requests == 4` `:713`, `hit_at_8 == 1/5`(채널 장애 질문이 적중 근거를 갖고도 미적중) `:714`, 토큰·자격 증명 미포함 `:715-716`을 단언한다 |
| 3. tasks.md에 r1·r2 범위 없음 | 해소 | `tasks.md:14-16`(2.5~2.7), `:21-22`(3.2~3.3), `:27`(4.5). 각 task의 동작은 코드와 테스트로 확인했다(아래 표) |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Retrieval-only scoring / Relevant source item ranked first | 충족 | `scripts/ask_replay.py:539-541`, `:565-570`, `:622-625` · 테스트 `test_ask_replay_script.py:431`, `:445` |
| Retrieval-only scoring / Relevant wiki item through its compiled sources | 충족 | `:537-538`, `wiki_pages.sources` 요청자 토큰 조회 `:1039-1046` · 테스트 `:450` |
| Retrieval-only scoring / Wiki page compiled from another document | 충족 | `:568` · 테스트 `:454` |
| Retrieval-only scoring / No relevant item in the top 8 | 충족 | `:622-625` · 테스트 `:460` |
| Retrieval-only scoring / Only one side of the dual citation is found | 충족 | `:574-581`, `:626-628` · 테스트 `:469` |
| Retrieval-only scoring / Question with several expected documents | 충족 | `:571-573`, `:630-633` · 테스트 `:474` |
| Retrieval-only scoring / Unanswerable question | 충족 | `:595`, `:634-638` · 테스트 `:483` |
| Retrieval-only scoring / Retrieval request fails for a question | 충족 | `:1073-1083`, `:614-621` · 테스트 `:494`(요약), `:709`·`:713`(명령 경로 `q-http → http_500`, 실패 수 보고) |
| Retrieval-only scoring / Retrieval succeeds with a failed channel | 충족 | `:544-554`, `:1089`, `:1112-1113`, `:598-599` · 테스트 `:533`, `:544`, `:684`·`:706`(HTTP 200 + `source_vector` 실패 → `channel_failed`), `:714`(적중 근거가 있어도 미적중) |
| Retrieval-only scoring / Expected document cannot be mapped | 충족 | `:1049-1066` · 테스트 `:568`, `:699`·`:707`(제목 `B` 없음 → `unmapped_expected`), `:711`(검색 미호출) |
| Retrieval-only scoring / Failed multi-document question | 충족 | `:610-613`, `:630-633` · 테스트 `:553` |
| Retrieval-only scoring / Duplicate raw source titles | 충족 | `:1032-1037`(검색 호출 전) · 테스트 `:719-729` |
| Retrieval-only scoring / 원문 근거 추적 실패를 측정 실패로 (Requirement 본문) | 충족 | `:1090-1115` · 테스트 `:687-693`·`:708`(`metadata.raw_source_id` 없음 + 청크 조회 빈 결과 `:635-636` → `unresolved_evidence`) |
| Retrieval-only scoring / 지표 정의 문구 (Requirement 본문) | 충족 | `:519-523`, `:618`, `:663` · 테스트 `:504` |
| Retrieval-only scoring / 답변 생성 공급자 미호출 (Requirement 본문, MUST NOT) | 충족 | 호출 대상은 로그인, `/health`, PostgREST 3개 테이블, `/workspaces/{id}/retrieval`뿐 `:1021-1108`. 테스트의 가짜 전송은 이 6개 경로 밖 요청이면 `AssertionError`를 던지므로(`:641`) `/ask` 등 다른 호출이 생기면 실패한다 |
| Retrieval-only scoring / 요청자 토큰 (Requirement 본문) | 충족 | `:1030`, `:1044`, `:1070`, `:1106` |
| Append-only records / Output path already exists | 충족 | `:1001-1004`, `"x"` 모드 `:1143` · 테스트 `:508` |
| Append-only records / 기록 내용과 금지 항목 (Requirement 본문) | 충족 | `label`·`git_sha`·`k`·`policy_versions`·`rows`(상태 포함)·`summary` `:1133-1141` · 테스트 `:703-716`(`rows`의 상태, `policy_versions`, `summary`, 토큰·자격 증명 미포함). 답변 텍스트는 이 명령이 답변을 만들지 않으므로 기록될 경로가 없다 |
| Append-only records / Two records compared | 충족 | `:656-671`, 정책 버전 `:664-665` · 테스트 `:519`, `:575` |

## task 완료 주장 대조

| task | 결과 | 근거 |
| --- | --- | --- |
| 2.5 채널 장애 · `policy_versions` · 비교 표 정책 버전 | 확인 | 코드 `:544-554`, `:1087-1088`, `:1138`, `:664-665` · 테스트 `:533`, `:706`, `:712`, `:575` |
| 2.6 매핑 실패 · 근거 미확인 · 제목 중복 거부 | 확인 | 코드 `:1049-1066`, `:1109-1115`, `:1032-1037` · 테스트 `:707-708`, `:719` |
| 2.7 측정 실패 미적중 · 종류별 보고 · `doc`에서 정답 수 · `x` 모드 | 확인 | 코드 `:598-599`, `:614-621`, `:610-613`, `:1143` · 테스트 `:544`, `:553`, `:713-714` |
| 3.2 r1 테스트 | 확인 | 테스트 `:533-582` |
| 3.3 r2 명령 경로 테스트 | 확인 | 테스트 `:587-729`, 변이 탐침으로 각 분기 고정 확인 |
| 4.5 재측정 | 확인 불가(실측) | 외부 스택 실행이라 이 리뷰에서 재현하지 않았다. 문서 수치의 출처 검증은 스펙 시나리오 판정 범위 밖이다 |

## 조치가 필요한 항목

없음.

## 참고(판정에 반영하지 않음)

- `tasks.md`에서 4.5가 4.1과 4.2 사이에 놓여 번호 순서가 어긋난다. 실행 순서를 반영한 배치로 보이며 동작과 무관하다.
- 기록 테스트가 `label`·`git_sha`·`k` 키를 명시적으로 단언하지는 않는다. 코드(`:1133-1141`)상 항상 들어가고 비교 기능(`label`)이 이에 의존하므로 판정에는 반영하지 않았다.
- r2 참고 항목(답할 수 없는 질문도 측정 실패가 되면 `failed_requests`에 포함, `channel_failed` 우선순위)은 그대로이며 스펙과 어긋나지 않는다.

## 판정 근거

r2의 세 지적이 모두 해소됐다. 제목 중복 거부와 측정 실패 상태 네 가지(채널 장애·매핑 실패·근거 미확인·HTTP 실패)를 실제 `cmd_retrieval_eval` 경로로 고정하는 테스트가 추가됐고, 각 분기를 하나씩 무력화하면 해당 테스트가 실패함을 변이 탐침으로 확인했다. 따라서 이 테스트들은 실제로 회귀를 잡는다. `tasks.md`도 r1·r2로 늘어난 범위를 담았고, 체크된 task마다 대응 코드와 테스트가 있다. 코드는 r2 이후 바뀌지 않았고 r2에서 스펙 밖 동작이 없음을 확인했으므로, 모든 Scenario와 Requirement 본문의 MUST/SHALL이 구현과 테스트 증거로 충족된다. 이번이 리뷰 게이트의 마지막 라운드(r3)이고 pass가 아니면 blocked로 확정되지만, 남은 미충족 항목이 없으므로 `pass`로 판정한다.
