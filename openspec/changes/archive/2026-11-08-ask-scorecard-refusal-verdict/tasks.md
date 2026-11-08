## 1. 판정 규칙

- [x] 1.1 `scripts/ask_replay.py`에 거절 문구 상수(출처: `0006_seed_prompts.sql` 151·184행)와 `is_refusal(answer)` 추가: 제목 줄(`#`)·빈 줄을 건너뛴 첫 본문 줄이 문구로 시작, 공백 차이 무시
- [x] 1.2 `verdict()`의 답할 수 없는 질문 분기를 고친다: 위조 앵커 0건이면서 `no-evidence`이거나 (`resolved`이고 `is_refusal`)이면 통과, 위조 앵커는 두 경로 모두 실패, 거절 줄이 아닌 답은 기존 이유 문구로 실패

## 2. 테스트

- [x] 2.1 `apps/worker/tests/test_ask_replay_script.py`에 스펙 시나리오 추가: 제목 줄 뒤 거절(q30 실제 답변 본문), 공백만 다른 거절, 문구가 중간에만 있는 답, 거절 줄 + 위조 앵커, 거절 없이 답한 경우
- [x] 2.2 기존 `test_unanswerable_question_passes_only_on_refusal`이 새 규칙과 어긋나지 않는지 확인하고 필요하면 고친다

## 3. 문서

- [x] 3.1 `docs/ops/ask-sample-replay.md`의 통과 조건에 답할 수 없는 질문의 새 기준과 알려진 한계 두 가지(장애성 `no-evidence`, 혼합 답변)를 적는다
- [x] 3.2 같은 문서의 q30 설명을 "이제 통과로 판정된다"는 사실에 맞게 고친다

## 4. 검증

- [x] 4.1 새로 실행: 관련 테스트 · ruff check · ruff format --check · `openspec validate ask-scorecard-refusal-verdict --strict` · `openspec validate --specs`
