## 1. 판정과 집계 (순수 로직)

- [x] 1.1 `scripts/ask_replay.py`에 `verdict(row, question)` 추가: 통과 4조건, `answerable: false` 예외, `keyword_hit is None` 건너뛰기, 고정 순서 첫 실패 이유 한 줄
- [x] 1.2 `dual_citation_rate > 0`이 "한 답변 안에 위키와 원문 모두 인용"을 뜻하는지 `apps/api/src/api/services/ask.py`의 계산으로 확인하고, 다르면 기준 필드를 바꾼다
- [x] 1.3 `summarize()`에 `latency_p50_ms`/`latency_p95_ms`와 `pass_rate`, `passed`, `asked` 추가. 경과 시간이 하나도 없으면 값 없음(0 아님)
- [x] 1.4 `_ask_once`의 `usage_events` 조회에 모델 컬럼을 더해 행/요약에 `model` 기록, 없으면 `unknown`. 컬럼명은 마이그레이션으로 확인
- [x] 1.5 `apps/worker/tests/test_ask_replay_script.py`에 판정 시나리오(스펙의 각 시나리오)와 백분위·빈 입력 테스트 추가

## 2. 누적 기록

- [x] 2.1 `ask` 명령 끝에서 `scorecard.jsonl`에 한 줄 append(label·git_sha·model·pass_rate·asked/planned·토큰·비용·p50/p95·결과 파일 상대 경로). 본문·키·공급자 ID 제외
- [x] 2.2 `--scorecard` 인자 추가(기본: `--out` 옆). 지출 상한 중단 시 asked < planned가 줄에 남는지 확인
- [x] 2.3 append가 앞선 줄을 건드리지 않고, 깨진 줄은 읽을 때 건너뛰는 테스트 추가

## 3. 정적 HTML 성적표

- [x] 3.1 `report` 하위 명령 추가: `scorecard.jsonl`과 결과 JSON을 읽어 단일 HTML 파일 생성. API·DB·공급자·스택 코드에 접근하지 않음
- [x] 3.2 위쪽 실행별 표(통과율 막대, 토큰, $/문항, p50/p95, 문항 수), 고정 문구(합성 샘플·운영 수치 아님·지연은 클라이언트 측정)
- [x] 3.3 실행 선택 시 30문항 상세(통과/실패 글자 표기, 실패 이유 한 줄, 답변 `<details>` 접기). 결과 파일 없는 실행은 "상세 없음", 빈 스코어카드는 안내와 명령 표시
- [x] 3.4 데이터 JSON의 `<` 이스케이프와 `textContent` 렌더링. 마크업이 든 답변/이유가 실행되지 않는 테스트 추가
- [x] 3.5 라이트/다크 대응, 모바일 폭에서 가로 스크롤 없음 확인

## 4. 검증과 문서

- [x] 4.1 기존 결과 JSON(또는 테스트 fixture)으로 `report`를 오프라인 실행해 화면을 브라우저로 직접 확인
- [x] 4.2 옛 결과 파일(판정 필드 없음)로 `compare`와 `report`가 모두 동작하는지 확인
- [x] 4.3 `docs/ops/ask-sample-replay.md`에 성적표 실행법, 통과 기준, p95 정의(인덱스 방식), 합성 샘플 경고 추가
- [x] 4.4 사용자 확인을 받은 뒤 실제 30문항을 1회 재생(약 $0.75~$0.94)하고 누적 줄과 화면을 확인, 비용을 문서에 기록
- [x] 4.5 새로 실행: 관련 테스트 · ruff · typecheck · `openspec validate ask-scorecard --strict`
