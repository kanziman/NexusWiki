# Spec Conformance 리뷰 — ask-scorecard r2

- 판정: pass
- 대상: `git diff` 미커밋 변경 (HEAD c97d3b3 + 작업 트리)
- 일시: 2026-11-07

## r1 지적 해소 확인

| r1 항목 | 결과 | 증거 |
| --- | --- | --- |
| 이중 인용 기준이 문장 단위 | 해소 | `scripts/ask_replay.py` `verdict()`가 `cited_wiki_count`/`cited_source_count`가 있으면 각각 1 이상인지 답변 단위로 판정. `_count_kind()`(`ask_replay.py:649`)가 `citations.resolved`의 `kind`를 센다. API가 `resolved`를 citations 이벤트에 싣고(`ask.py:1060`), kind는 `wiki`/`source`(`ask.py:296`, `hit.kind`)라 값이 일치한다. 이벤트가 없으면 None으로 0과 구분 |
| 옛 결과 대체 경로 | 해소 | 두 필드가 None이면 `dual_citation_rate > 0`으로 대체하고 이유에 "옛 결과, 문장 기준"을 밝힘 |
| 테스트 | 해소 | `test_ask_replay_script.py:329` (위키·원문이 다른 문장이어도 통과), `:335` (원문 0이면 실패), `:346` (`_count_kind`) |
| 문서·design | 해소 | `design.md:26`, `docs/ops/ask-sample-replay.md:32,34`가 답변 단위 기준·대체 경로·q26 한계를 설명 |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 판정 / 모든 기준 충족 | 충족 | `verdict()` · `test_answerable_question_passes_when_every_criterion_holds` |
| 판정 / 한 기준 실패(위키만 인용) | 충족 | 답변 단위 분기, 원문 0이면 "위키 또는 원문 인용이 없다" 이유. 이유가 "이중 인용 누락"을 가리킨다 · `:335` 테스트 |
| 판정 / 여러 기준 실패 | 충족 | 고정 순서 상태→위조→기대사실→인용 · `test_failure_reason_follows_the_documented_order` |
| 판정 / 기대 사실 없음 | 충족 | `keyword_hit is False`만 실패 |
| 판정 / 답 불가 정상 거절·답함 | 충족 | `not answerable` 분기 |
| 판정 / 모델 미도달 | 충족 | 상태명을 이유에 기재 |
| 지연 백분위 (2개) | 충족 | `summarize()` p50/p95, 없으면 None |
| 누적 기록 (3개) | 충족 | `append_scorecard`(append), `scorecard_line`(asked/planned, unknown 기본값) |
| 정적 페이지 (5개) | 충족 | `render_report`, `_json_for_script` 이스케이프, 빈 성적표 안내, 상세 없음 표기 (r1과 동일, 회귀 없음) |
| 지출 없음 / 오프라인 생성 | 충족 | `cmd_report`는 파일 읽기와 HTML 쓰기만 수행 |
| 호환성 / 옛 결과 파일 | 충족 | 추가 필드만 더함, 옛 행은 대체 경로로 재판정 |

`uv run pytest apps/worker/tests/test_ask_replay_script.py -q` 직접 실행: 35 passed.

## 조치가 필요한 항목

없음.

## 판정 근거

r1의 유일한 미충족(문장 단위 기준)이 코드·테스트·문서 모두에서 답변 단위로 바뀌었고, 나머지 시나리오에서 회귀는 보이지 않는다. 한계: 옛 결과 파일은 문장 기준 대체 경로를 쓰므로 스펙보다 엄격하며, 이는 이유 문구와 문서에 밝혀져 있어 호환성 요구(옛 필드만으로 판정 도출)와 모순하지 않는다. 실제 재생 수치(27/30)의 사실 여부와 브라우저 렌더링은 검증하지 않았다.
