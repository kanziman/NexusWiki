# Tasks — cheap-model-evidence-ablation

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/254

## 1. 사전 등록 · 모델별 점검 · 비용 기반 회차 계획 (https://github.com/kanziman/NexusWiki/issues/255)

의존성: 없음. 예상: 반나절. 유료 호출: 이 slice의 테스트에서는 없음(가짜 LLM 스트림 · 가짜 사용량).

- [x] 1.1 `scripts/ask_replay_serve.sh`에 `ASK_REPLAY_LLM_MODEL`(`.env`의 `LLM_MODEL` 대신 쓰고 `ASK_COST_POLICIES`도 그 모델로 만든다)과 `ASK_REPLAY_WORKER_ONLY=1`(API 미기동)을 더한다. `.env`는 읽기만 한다(설계 D2).
- [x] 1.2 `scripts/model_evidence_eval.py`에 `register`를 만든다. 모델 · 조건 · 회차 최대/최소 · 상한 · 점검 문항 · 안전계수 · 재사용 고정 입력과 그 파일 sha256을 쓰고 내용 해시를 붙인다. 상한이 양수가 아니면 거부한다(설계 D3).
- [x] 1.3 `probe`를 만든다. 등록 해시 · 시각을 검사하고, 스냅샷 · 질의 벡터 해시가 고정 입력과 다르면 유료 호출 전에 멈춘다. `bothxbody`로 점검 문항 1턴을 돌려 상태 · 모델 · 토큰 · 비용 · 잘림을 기록하고, 모델 불일치나 실행 장애는 실패로 남긴다(설계 D1 · D6).
- [x] 1.4 `plan`을 만든다. 점검 기록의 허용 필드만 읽어 실패 모델을 제외하고, 재생 DB 지출과 최고 점검 턴 비용 × 안전계수로 회차 수를 정한다. 최소 회차도 안 들어가면 계획하지 않고 이유를 남긴다(설계 D3 · D4).

Given 내용이 바뀐 등록 파일, When `probe`를 실행하면, Then 유료 호출 없이 거부된다.
Given 재수집으로 스냅샷 해시가 다른 스택, When `probe`를 실행하면, Then 유료 호출 없이 스냅샷을 다른 입력으로 지목하고 멈춘다.
Given 사용량의 모델이 등록 모델과 다른 점검 턴, When `probe`가 끝나면, Then 그 모델은 실패로 기록되고 `plan`에서 이유와 함께 제외된다.
Given 출력 상한에 닿았지만 `resolved`인 점검, When `plan`을 실행하면, Then 그 모델은 계획에 남고 점검 기록에 잘림이 표시된다.
Given 세 점검 비용으로 3회차가 상한을 넘고 2회차는 들어갈 때, When `plan`을 실행하면, Then 계획 회차는 2이고 정답 필드는 읽지 않는다.

검증: `uv run pytest apps/worker/tests/test_model_evidence_eval_script.py && uv run ruff check . && uv run ruff format --check . && bash -n scripts/ask_replay_serve.sh`

## 2. 회차 우선 재생 · 턴 판정 · JSONL 성적표 줄 (https://github.com/kanziman/NexusWiki/issues/256)

의존성: 1. 예상: 1일. 유료 호출: 이 slice의 테스트에서는 없음.

- [x] 2.1 `run --round R --model M`을 만든다. 계획에서 앞선 (회차, 모델) 기록이 없으면 거부하고, 두 조건을 30문항씩 돌며 턴 직전에 재생 DB 지출 + 다음 턴 추정이 상한을 넘으면 멈추고 남은 턴을 `not_run`으로 남긴다. 예외로 끝나도 부분 기록을 쓴다. 기존 경로는 덮어쓰지 않는다(설계 D4 · D5).
- [x] 2.2 턴 행에 `llm_calls` · `repair_attempted` · `fallback` · `truncated` · `measurement_failure`를 더하고, 모델 불일치나 사용량 누락 턴에서 실행을 멈춘다. `source_onlyxbody`는 진단으로 표시하고 이중 인용으로 판정하지 않는다. 거절 문항은 따로 센다(설계 D6).
- [x] 2.3 실행이 끝나거나 멈출 때 `scoreboard.jsonl`에 한 줄을 덧붙인다(본문 · 질문 · 키 제외). `import-reference`로 #237 Sonnet 두 조건을 `reference` 줄로 한 번 싣는다(설계 D7).
- [x] 2.4 `scripts/model_evidence_run.sh`가 계획을 읽어 회차 × 모델마다 워커를 띄우고 리스너 준비를 기다린 뒤 `run`을 부르고 내린다(설계 D2 · D5).

Given 1회차 한 모델의 기록이 없는 상태, When 2회차 `run`을 요청하면, Then 빠진 1회차 실행을 지목하며 거부된다.
Given 다음 턴이 상한을 넘는 지출 상태, When `run`이 그 턴에 이르면, Then 멈추고 남은 턴을 `not_run`으로, 이유를 상한으로 기록한다.
Given 수리도 실패해 `fallback`으로 끝난 턴, When 턴 행을 만들면, Then `repair_attempted`와 `fallback`이 참이고 사실 포함은 Fallback 본문으로 판정된다.
Given 끝난 실행, When 성적표를 보면, Then 새 줄 하나가 붙고 앞선 줄은 바뀌지 않으며 줄에 질문 · 답변 본문이 없다.
Given #237 `answer.json`, When `import-reference`를 실행하면, Then Sonnet 두 줄이 `reference: true`, `round: null`로 붙는다.

검증: `uv run pytest apps/worker/tests/test_model_evidence_eval_script.py && uv run ruff check . && uv run ruff format --check . && bash -n scripts/model_evidence_run.sh`

## 3. 로컬 성적표 화면과 정적 HTML (https://github.com/kanziman/NexusWiki/issues/257)

의존성: 2. 예상: 반나절. 유료 호출: 없음.

- [x] 3.1 `scoreboard`를 표준 라이브러리 `http.server`로 만든다. 루프백이 아니면 듣기 전에 거부하고, 요청마다 JSONL을 다시 읽어 깨진 줄 수를 알린다. 실행별 행(사실 포함 막대 · 장애 · 위조 앵커 · 수리 · Fallback · 잘림 · 토큰 · 문항당 비용 · 지연)과 진단 · 참조 표시를 그린다(설계 D7).
- [x] 3.2 모델 요약을 완료 회차로만 만든다. 조건별 사실 포함, 위키 차이, 문항 안정성, 늘 복구 · 늘 회귀 문항, 부분 회차 표시. `--html`로 같은 화면을 정적 파일로 낸다(설계 D7).

Given 루프백이 아닌 주소, When `scoreboard`를 실행하면, Then 듣기 전에 멈춘다.
Given 한 모델에서 원문만은 모든 완료 회차에 사실을 놓치고 둘 다는 모두 포함한 문항, When 모델 요약을 만들면, Then 그 문항은 "늘 복구"에 나온다.
Given 3회차가 한 모델에서만 끝난 성적표, When 모델 요약을 만들면, Then 3회차는 부분으로 표시되고 모델 간 수치에서 빠진다.
Given `<script>`가 든 모델 이름 줄, When 화면을 그리면, Then 그 값은 이스케이프되어 실행되지 않는다.

검증: `uv run pytest apps/worker/tests/test_model_evidence_eval_script.py && uv run ruff check . && uv run ruff format --check .`, 가짜 기록으로 `scoreboard --html` 생성 확인

## 4. 실측과 기록 (상한 $1.00) (https://github.com/kanziman/NexusWiki/issues/258)

의존성: 3. 예상: 반나절. 유료 호출: 있음(점검 + 재생, 총 $1.00 이하).

- [x] 4.1 재생 월 한도 여유를 확인하고, 부족하면 이 실험에 필요한 만큼만 일시 조정한다. `register` → 모델별 `probe` → `plan` → `model_evidence_run.sh`를 실행하고, 끝나면 워커를 내리고 한도를 원래 값으로 되돌린다(설계 D8).
- [x] 4.2 `docs/ops/ask-sample-replay.md`에 결과 절(모델별 위키 차이 · 실패 신호 · 비용 · 한계)을, change의 `verification.md`에 기록 파일 sha256 · 실측 지출 · 계획 이탈을 남긴다.

Given 등록 상한 $1.00, When 실측이 끝나면, Then 재생 DB `usage_events`의 등록 이후 지출 합이 1,000,000 micros 이하다.
Given 실측 기록, When 성적표 화면을 열면, Then 모델 3종(또는 제외 이유) · 완료 회차 · 위키 차이가 보이고 Sonnet은 참조로만 표시된다.
Given 실측 종료, When 재생 DB 월 한도를 보면, Then 실험 전 값과 같다.

검증: `uv run python scripts/model_evidence_eval.py scoreboard --dir <실험 디렉터리> --html <파일>` 생성, 재생 DB 지출 조회, `openspec validate cheap-model-evidence-ablation --strict`
