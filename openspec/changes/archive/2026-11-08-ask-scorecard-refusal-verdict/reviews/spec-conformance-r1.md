# Spec Conformance 리뷰 — ask-scorecard-refusal-verdict r1

- 판정: pass
- 대상: `git diff` 미커밋 변경 (베이스 5cda037)
- 일시: 2026-11-08

## MODIFIED 블록 완전성

기존 `openspec/specs/ask-replay-scorecard/spec.md`의 "Per-question pass verdict" 시나리오 7개(정답 질문 충족 / 한 기준 실패 / 여러 기준 실패 / 기대 사실 없음 / 올바른 거절 / 답했음 / 모델 미도달)는 delta에 전부 그대로 남아 있다. 정답 질문 쪽 시나리오와 요구문 문장은 손실이 없다. 변경은 unanswerable 문장, "Unanswerable question answered anyway" 시나리오의 WHEN 문구, 신규 시나리오 4개(모델 거절, 문구가 뒤에 나옴, 거절 + 위조 앵커, 공백 차이)뿐이다. 이후 Requirement(Latency percentiles)는 건드리지 않았다.

## 시나리오 판정

| Scenario | 결과 | 증거 |
| --- | --- | --- |
| 정답 질문 모든 기준 충족 | 충족 | `scripts/ask_replay.py:167-` 정답 분기는 diff에서 변경 없음 · 기존 테스트 통과 |
| 한 기준 실패(이중 인용 누락) | 충족 | `ask_replay.py:177-184` 불변 |
| 여러 기준 동시 실패 | 충족 | 고정 순서 `ask_replay.py:167-` 불변 |
| 기대 사실 미정의 | 충족 | `ask_replay.py:174-176` 불변 |
| 올바른 거절(no-evidence) | 충족 | `ask_replay.py:158-165` · 테스트 `test_no_evidence_still_passes_without_an_answer_text` |
| 모델 거절(resolved + 거절 첫 줄) | 충족 | `ask_replay.py:158-165`, `is_refusal` · 테스트 `test_q30_refusal_after_a_heading_passes_even_though_status_is_resolved` |
| 거절 없이 답함 | 충족 | `ask_replay.py:161-162` (이유 "답하면 안 되는 질문에 답했다") · 테스트 `test_made_up_number_without_refusal_still_fails` |
| 문구가 뒤에만 나옴 | 충족 | `is_refusal`이 첫 본문 줄만 검사 · 테스트 `test_refusal_statement_appearing_only_later_is_not_a_refusal` |
| 거절 + 위조 앵커 | 충족 | `ask_replay.py:163-164` · 테스트 `test_refusal_with_fabricated_anchors_fails_with_the_anchor_reason` |
| 공백 차이만 다른 거절 | 충족 | `is_refusal`이 공백 제거 후 비교 · 테스트 `test_refusal_differing_only_in_spacing_is_still_a_refusal` |
| 모델 미도달(HTTP 오류 / no-evidence) | 충족 | 정답 분기 `ask_replay.py:170-171` 불변 |

제목 줄(`#`)·공백 무시는 `is_refusal`에서 구현됐다. `fallback` 상태는 거절로 인정하지 않으며(테스트 `test_fallback_status_is_not_a_refusal_even_with_the_statement`), 스펙의 "completed normally" 조건과 일치한다.

## tasks.md 대조

1.1, 1.2, 2.1, 2.2, 3.1, 3.2 구현 흔적 확인(상수 `REFUSAL_STATEMENT`, 테스트 8개 추가, 문서 두 곳 수정). 4.1은 pytest만 직접 재실행했다. 결과는 43 passed. ruff와 `openspec validate`는 이 리뷰에서 실행하지 않았다.

## 조치가 필요한 항목

없음.

## 스펙 밖 동작

없음. 문서에 적힌 알려진 한계 두 가지(장애성 no-evidence, 혼합 답변)는 스펙 동작을 그대로 기술한 것이며 새 동작이 아니다.

## 판정 근거

delta의 모든 시나리오가 코드 경로와 대응 테스트로 확인됐고, MODIFIED 블록은 기존 정답 질문 시나리오를 하나도 잃지 않았다.
