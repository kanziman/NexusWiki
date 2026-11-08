# Spec Conformance 리뷰 — ask-scorecard r1

- 판정: needs_fix
- 대상: `git diff main...HEAD` 미커밋 변경 (HEAD c97d3b3 + 작업 트리)
- 일시: 2026-11-07

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 판정 / 모든 기준 충족 | 충족 | `scripts/ask_replay.py` `verdict()` · 테스트 `test_answerable_question_passes_when_every_criterion_holds` |
| 판정 / 한 기준 실패(위키만 인용) | 충족(경로 한정) | `verdict()` 마지막 분기 · `test_missing_dual_citation_fails_with_that_reason`. 단 아래 항목 1 |
| 판정 / 여러 기준 실패 | 충족 | 고정 순서 상태→위조→기대사실→이중인용, `test_failure_reason_follows_the_documented_order` |
| 판정 / 기대 사실 없음 | 충족 | `keyword_hit is False`만 실패, `test_unknown_expected_fact_is_not_a_failure` |
| 판정 / 답 불가 질문 정상 거절 | 충족 | `verdict()` `not answerable` 분기 · `test_unanswerable_question_passes_only_on_refusal` |
| 판정 / 답 불가인데 답함 | 충족 | 같은 분기("답하면 안 되는 질문에 답했다") · 같은 테스트 |
| 판정 / 모델 미도달 | 충족 | `status != "resolved"` 분기가 상태명 기재 · `test_turn_that_never_reached_the_model_fails_with_its_status` |
| 지연 백분위 / 정상 | 충족 | `summarize()`의 `latency_p50_ms/p95_ms`(ms 단위) · `test_summary_reports_pass_rate_and_latency_percentiles` |
| 지연 백분위 / 경과 시간 없음 | 충족 | 빈 목록이면 None · `test_latency_is_absent_not_zero_without_elapsed_times` |
| 누적 기록 / 두 실행 순서 | 충족 | `append_scorecard`는 "a" 모드 append · `test_append_keeps_earlier_lines_untouched` |
| 누적 기록 / 지출 상한 중단 | 충족 | `scorecard_line`의 `asked`/`planned` (`planned_questions`는 `cmd_ask`에서 기록) · `test_scorecard_line_has_no_text_and_marks_early_stops` |
| 누적 기록 / 리비전·모델 불명 | 충족 | `"unknown"` 기본값 · `test_scorecard_line_records_unknown_revision_and_model` |
| 정적 페이지 / 여러 실행 | 충족 | `render_report` 표·5개 수치 · `test_report_lists_runs_in_order_and_marks_missing_detail` |
| 정적 페이지 / 실행 상세 | 충족 | `renderDetail()`의 판정·이유(글자 ✓/✗ 병기) |
| 정적 페이지 / 결과 파일 없음 | 충족 | `rows is None`이면 "상세를 볼 수 없습니다" |
| 정적 페이지 / 빈 성적표 | 충족 | 안내와 `ask_replay.py ask ...` 명령 표시 · `test_empty_report_names_the_command` |
| 정적 페이지 / 신뢰 불가 텍스트 | 충족 | `_json_for_script` 이스케이프 + `textContent` · `test_markup_in_results_cannot_break_out_of_the_page` |
| 지출 없음 / 오프라인 생성 | 충족 | `cmd_report`는 파일 읽기만, httpx 호출 없음 |
| 호환성 / 옛 결과 파일 | 충족 | 추가 필드만 더함, `--result`로 행 필드 재판정 · `test_report_rederives_verdicts_for_old_result_files` |

## 조치가 필요한 항목

1. **이중 인용 기준이 스펙보다 엄격하다(조용한 범위 이탈)** — 스펙은 "답변이 위키 페이지와 원문을 각각 적어도 한 번 인용"(답변 단위)을 요구한다. 구현은 `dual_citation_rate > 0`을 쓰는데, `apps/api/src/api/services/ask.py:287-302`에서 이 값은 "한 문장 안에 `wiki:`와 `src:` 앵커가 모두 있는 문장 비율"이다. 위키는 한 문장, 원문은 다른 문장에서 인용한 정상 답변이 스펙상 pass인데 구현에서는 "위키와 원문을 함께 인용한 문장이 없다"로 fail이 된다. tasks 1.2와 design.md:26은 "다르면 `cited_anchor_count`와 종류별 필드로 바꾼다"고 했는데 `[x]` 처리만 되고 기준은 바뀌지 않았다. docs 32행이 "한 문장에"라고 풀어 적은 것은 이 차이를 인정한 것이며, 실측의 q26 실패도 이 차이에서 나온 것일 수 있다. 근거 Scenario: "Question fails on one criterion", Requirement "Per-question pass verdict". 제안: `_ask_once` 행에 답변 단위 인용 종류(예: `cited_wiki_count`/`cited_raw_count`, `citations.resolved`의 kind에서 산출)를 추가 필드로 기록하고, `verdict()`는 그 필드를 우선 사용하되 옛 결과 파일에는 `dual_citation_rate`로 대체한다. 문서 설명과 q26 재채점도 갱신한다. 해당 로직을 검증하는 테스트(위키 문장과 원문 문장이 따로 있는 답변이 pass)를 추가한다.

## 판정 근거

항목 1을 제외한 모든 Scenario는 코드 경로와 테스트로 확인됐다. 항목 1은 스펙의 판정 기준 자체를 구현이 다르게 해석한 것이며, 스펙(답변 단위)이 명확하고 design 결정도 "다르면 바꾼다"로 되어 있어 코드와 문서만 고치면 해결된다. 스펙 수정은 필요 없으므로 blocked가 아니라 needs_fix다. 참고로 이 리뷰는 테스트·ruff를 직접 실행하지 않았고 정적 대조만 했다. 실제 재생(4.4) 수치의 사실 여부도 검증하지 않았다.
