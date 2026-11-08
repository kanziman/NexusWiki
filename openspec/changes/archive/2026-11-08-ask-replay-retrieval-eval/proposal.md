## Why

평가 지도(`docs/ops/evaluation-map.md`)에서 검색 칸이 비어 있다. 기록된 검색 수치(recall 0.222)는 2026-08 대규모 스트레스 측정이라 현재 제품의 검색 품질이 아니다. 성적표가 답변을 실패로 판정해도 그 원인이 검색인지 답변 작성인지 가를 수 없고, 모델 비교나 개선 작업의 효과도 검색이 흔들리면 해석할 수 없다. 강의 32편(에이전트 · RAG 평가)의 방식대로 검색을 답변과 분리해 먼저 잰다.

## What Changes

- `scripts/ask_replay.py`에 `retrieval-eval` 하위 명령을 추가한다. 재생 30문항에 LLM 없이 검색 API만 돌려 질문마다 정답 문서와 대조한다.
- 정답 매칭: 원문 근거는 그 근거의 원문이 정답 문서면 적중, 위키 근거는 그 위키 페이지를 만든 원문 목록에 정답 문서가 있으면 적중이다.
- 지표: hit@1 · hit@3 · hit@8, MRR, 원문만 hit@8, 위키만 hit@8, **이중 적중@8**(상위 8 안에 정답 원문과 정답 위키가 둘 다 있음). 여러 문서 질문은 "하나라도 적중"과 "전부 적중"을 따로 센다. 답할 수 없는 질문은 적중 지표에서 빼고 근거 반환 건수만 보고한다.
- 지표 이름 옆에 정의를 적는다. 여기서 hit@k는 "정답 문서의 근거가 하나라도 상위 k에 있는 질문의 비율"(hit rate)이다.
- 결과는 append-only 기록 파일(JSON)로 남기고, 요약을 출력하며, 두 기록을 비교한다.
- 평가 지도의 검색 칸과 적용 원장을 측정 결과로 갱신한다.

## Capabilities

### New Capabilities

(없음)

### Modified Capabilities

- `ask-replay-scorecard`: 재생 질문 세트로 검색만 따로 채점하는 요구사항을 추가한다(ADDED)

## Impact

- 코드: `scripts/ask_replay.py`, `apps/worker/tests/test_ask_replay_script.py`
- 문서: `docs/ops/evaluation-map.md`(이 브랜치의 미커밋 초안), `docs/ops/ask-sample-replay.md`
- DB, API, RLS, 마이그레이션 변경 없음. 기존 검색 API를 사용자 토큰으로 호출만 한다.
- 비용: 질의 임베딩 30건. 재생 스택을 다시 띄우면 문서 재수집(컴파일)에 약 $0.22가 든다. 답변 LLM은 부르지 않는다.
