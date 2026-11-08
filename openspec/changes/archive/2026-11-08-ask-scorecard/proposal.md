## Why

`scripts/ask_replay.py`는 합성 질문 30개를 실제 ask에 돌려 토큰·비용·이중 인용률을 재지만, 질문이 통과인지 판정하는 기준과 지연 집계가 없고 결과가 실행마다 따로 흩어진다. 그래서 코드나 모델을 바꿨을 때 "어느 질문이 왜 떨어졌는지"와 "실행들의 흐름"을 한눈에 볼 수 없다. 이중 Citation이 이 제품의 존재 이유인데, 그 품질을 사람이 눈으로 따라갈 길이 없다.

## What Changes

- 질문별 **통과 판정**을 추가한다. 통과 조건은 정상 완료, 위조 앵커 0건, 기대 사실 포함 판정이 거짓이 아님, 이중 인용 1개 이상이다. 답할 수 없는 질문(`answerable: false`)은 `no-evidence`가 정답이므로 별도 규칙을 적용한다.
- 요약에 **지연 p50/p95**를 추가한다. `elapsed_ms`는 이미 수집하고 있으나 집계하지 않는다.
- 실행이 끝날 때마다 한 줄을 `scorecard.jsonl`에 **누적**한다(label · git sha · 모델 · 통과율 · 토큰 · 비용 · p50/p95).
- `scorecard.jsonl`과 실행 결과 JSON으로 **정적 HTML 성적표**를 생성한다. 위쪽은 실행별 성적표, 실행을 고르면 30문항 상세와 실패 이유 한 줄을 보여 준다.
- 화면 상단에 "합성 샘플 수치이며 운영 트래픽이 아니다" 문구를 고정한다.
- 기존 `compare` 출력과 결과 JSON의 기존 필드는 유지한다. 새 필드만 더한다.

## Capabilities

### New Capabilities

- `ask-replay-scorecard`: ask 합성 재생의 질문별 통과 판정, 지연 백분위, 실행 누적 기록, 정적 HTML 성적표의 계약

### Modified Capabilities

(없음. 제품 사용자 행동과 API 계약은 바뀌지 않는다. 개발 검증 도구 계약만 새로 둔다.)

## Impact

- 코드: `scripts/ask_replay.py`(판정·집계·누적 기록·HTML 생성 진입점), 단위 테스트 `apps/worker/tests/test_ask_replay_script.py`
- 산출물: `scorecard.jsonl`과 생성 HTML은 저장소 밖 경로(재생 출력 디렉터리)에 둔다. 합성 샘플이라 커밋 대상이 아니다.
- 문서: `docs/ops/ask-sample-replay.md`에 성적표 실행법과 판정 기준을 추가한다.
- DB·마이그레이션·API·RLS 변경 없음. 재생은 기존처럼 loopback 스택에만 붙는다.
- 비용: 화면 검증은 기존 결과 JSON으로 하므로 무료다. 실제 30문항 재생은 1회 약 $0.75~$0.94이며 마지막 검증에서 한 번만 돈다.
