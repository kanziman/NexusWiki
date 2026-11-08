## Why

Ask 재생 성적표(`ask-replay-scorecard`)는 답할 수 없는 질문을 상태가 `no-evidence`일 때만 통과로 센다. 그런데 검색이 무관한 근거를 하나라도 가져오면 모델 호출까지 가고, 모델이 정확히 거절해도 상태는 `resolved`다. 첫 실제 재생에서 q30이 "제공된 자료로는 알 수 없습니다"라고 올바르게 거절했는데 실패로 집계됐다. 판정 규칙이 정확한 거절을 벌하고 있다. 이슈 #224.

## What Changes

- 답할 수 없는 질문의 통과 조건을 넓힌다. 위조 앵커가 0건이면서 (a) 상태가 `no-evidence`이거나, (b) 상태가 `resolved`이고 답변의 첫 본문 줄이 거절 문구로 시작하면 통과한다.
- 거절 문구는 시드 프롬프트(`0006_seed_prompts.sql`)가 모를 때 쓰라고 지시하는 "제공된 자료로는 알 수 없습니다"다. 비교는 공백 차이를 무시한다. 제목 줄(`#`로 시작)과 빈 줄은 건너뛰고 첫 본문 줄만 본다.
- 숫자를 지어내 답한 경우는 계속 실패한다. 실패 이유는 "거절하지 않고 답했다"와 "위조 앵커"로 구분해 적는다.
- 통과 기준을 `docs/ops/ask-sample-replay.md`에 적고, 그 문서의 q30 설명을 새 기준으로 맞춘다.
- 코드 변경은 `scripts/ask_replay.py`의 `verdict`와 테스트에 한정한다. 결과 파일 필드와 성적표 줄 형식은 바꾸지 않는다.

## Capabilities

### New Capabilities

(없음)

### Modified Capabilities

- `ask-replay-scorecard`: "Per-question pass verdict" 요구사항에서 답할 수 없는 질문의 통과 조건과 시나리오

## Impact

- 코드: `scripts/ask_replay.py`(`verdict`), `apps/worker/tests/test_ask_replay_script.py`
- 문서: `docs/ops/ask-sample-replay.md`
- 스펙: `openspec/specs/ask-replay-scorecard/spec.md`(sync 시)
- DB, API, RLS, 마이그레이션, 결과 파일 필드 변경 없음. 실제 LLM 재생은 하지 않는다(기존 결과 파일의 q30 행으로 검증).
