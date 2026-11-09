# Tasks — eval-reliability

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/238

## 1. 성적표가 거절 성능을 통과율과 분리해 보인다 (https://github.com/kanziman/NexusWiki/issues/239)

의존성: 없음. 예상: 반나절. 유료 호출: 없음.

- [x] 1.1 `summarize`에 답할 수 있는 문항 통과 · 정확한 거절 · 잘못된 거절 수치를 더하고, 성적표 줄과 정적 화면이 세 수치를 보이게 한다. 화면은 필드가 없는 옛 줄이면 결과 파일 행에서 다시 계산하고, 결과 파일도 없으면 "-"로 표시한다. 정확한 거절 옆에는 거절 문항 수를 적는다(설계 D4).

Given 답할 수 있는 29문항 중 28개 통과와 거절 1문항 정확 거절, When 요약을 만들면, Then 답할 수 있는 문항 28/29 · 정확한 거절 1/1 · 잘못된 거절 0/29이고 기존 통과율은 29/30 그대로다.
Given 답할 수 있는 문항이 `resolved`이고 첫 본문 줄이 표준 거절 문구, When 판정하면, Then 기존대로 실패하고 잘못된 거절로도 센다.
Given 답할 수 있는 문항이 `no-evidence`로 끝남, When 판정하면, Then 실패이고 잘못된 거절로 센다.
Given 거절 문항 없이 돌린 회차, When 요약을 만들면, Then 정확한 거절은 0이 아니라 없음이다.
Given 이 변경 전의 결과 파일과 성적표 줄, When 화면을 만들면, Then 세 수치를 행에서 다시 계산하고 옛 줄은 바뀌지 않는다.

검증: `uv run pytest apps/worker/tests/test_ask_replay_script.py && uv run ruff check . && uv run ruff format --check .`, 보존된 결과 파일(`.worktrees/rrf-evidence-20261108/valid-after/`)로 `report`를 오프라인 실행해 화면을 확인한다.

## 2. 재생 기록이 #232와 같은 정의의 고정 입력을 남긴다 (https://github.com/kanziman/NexusWiki/issues/240)

의존성: 없음. 예상: 1일. 유료 호출: 없음(테스트는 가짜 HTTP 응답).

- [x] 2.1 `scripts/eval_fingerprint.py`에 `canonical_sha256` · `snapshot_inputs` · fixture 해시를 옮긴다. 수집 테이블 조회와 기본 Ask 프롬프트 해시는 `ask_replay`로 옮기고, `retrieval_ablation`이 그것을 쓰게 한다. 옮기기 전 해시 값을 테스트에 고정한다(설계 D1 · D2).
- [x] 2.2 `ask` 결과에 `fixed_inputs`(스냅샷 · fixture · 프롬프트 해시 · `requested_k` · 모델 · 정책 버전)를 남기고, 행에 SSE `meta`의 `policy_version` · `missing_channels`를 남긴다. `requested_k=8`을 명시해 보낸다. `retrieval-eval` 기록에도 스냅샷 지문과 fixture 해시를 남긴다. 값을 얻지 못하면 `unknown`을 쓴다(설계 D3).

Given 고정한 작은 수집 테이블, When 이동 후의 `snapshot_inputs`로 해시를 계산하면, Then 이동 전에 고정한 값과 같다.
Given 같은 수집 테이블, When `ask`와 `retrieval-eval`이 지문을 계산하면, Then 두 기록의 스냅샷 지문이 같다.
Given 프롬프트 템플릿 조회가 실패, When `ask`를 실행하면, Then 결과의 `answer_prompt_sha256`은 `unknown`이고 회차는 그대로 기록된다.
Given SSE `meta`에 실패 채널이 있는 턴, When 행을 만들면, Then 행의 `missing_channels`에 그 채널이 남는다.
Given 이 변경 전의 결과 파일, When `compare`와 `report`를 실행하면, Then 이전과 같은 출력이 나온다.

검증: `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_retrieval_ablation_script.py && uv run ruff check . && uv run ruff format --check .`

## 3. 같은 조건의 여러 회차를 한 묶음으로 읽어 변동폭을 보고한다 (https://github.com/kanziman/NexusWiki/issues/241)

의존성: 2. 예상: 1일. 유료 호출: 없음.

- [x] 3.1 `scripts/ask_replay_reliability.py report`를 만든다. HTTP 결과 파일들과 #232 답변 기록의 `both × body` 조건을 회차로 읽고, 실행 경로를 표시하고, 묶음 키가 다르거나 없으면 거부한다(설계 D6).
- [x] 3.2 문항별 k/N과 안정 통과 · 안정 실패 · 흔들림 · 미실행, 회차별 통과 수 · 최소 · 최대 · 평균 · Wilson 95% 구간, 회차별 거절 3수치를 낸다. 경로가 섞이면 HTTP만의 값과 전체 값을 둘 다 낸다. `ask-replay-reliability-v1` 기록을 새 파일로만 쓰고 Markdown 요약을 출력한다(설계 D7 · D10).

Given 고정 입력이 같고 revision만 다른 결과 3개, When `report`를 실행하면, Then 한 묶음이 되고 회차별 revision이 보인다.
Given 수집 지문이 다른 결과 하나, When `report`를 실행하면, Then 묶음을 거부하고 수집 스냅샷을 다른 항목으로 보인다.
Given 지문이 없는 옛 결과 파일, When 묶음에 넣으면, Then 지문 누락을 이유로 거부한다.
Given #232 답변 기록, When `source_only × body`나 `both × title_body` 조건을 회차로 요청하면, Then 거부한다.
Given 2/3 회차만 통과한 문항, When 보고서를 보면, Then 2/3 흔들림으로 표시된다.
Given 20문항에서 멈춘 회차, When 보고서를 보면, Then 남은 10문항은 그 회차에서 실패가 아니라 미실행이다.
Given 이미 있는 출력 경로, When `report`를 실행하면, Then 입력을 읽기 전에 거부하고 파일은 그대로다.

검증: `uv run pytest apps/worker/tests/test_ask_replay_reliability_script.py && uv run ruff check . && uv run ruff format --check .`, 네트워크 없이 합성 결과 파일과 `.worktrees/ablation-evidence-20261108/answer.json`으로 `report` 실행.

## 4. 실패 문항의 처음 틀어진 단계와 알려진 실패를 보고한다 (https://github.com/kanziman/NexusWiki/issues/242)

의존성: 3. 예상: 1일. 유료 호출: 없음.

- [x] 4.1 `scripts/fixtures/ask_replay_labels.v1.json`을 만들고 q06을 `question_ambiguity` · 알려진 실패 · 근거 #232로 넣는다. 라벨 파일을 검증해 근거가 비었거나, 없는 문항 id이거나, 원인이 집합 밖이면 거부한다(설계 D9).
- [x] 4.2 `report`가 지문이 같은 검색 기록(`retrieval-eval` 기록 또는 #232 `retrieve.json`의 `both × body`)으로 자동 단계를 실행 장애 → 검색 미적중 → 작성 순서로 판정하게 한다. 검색 기록이 없으면 검색 근거 없음으로 둔다. 라벨은 자동 단계 옆에 함께 적고, 알려진 실패와 예상 밖 실패를 나눠 세며, 통과한 알려진 실패를 드러낸다(설계 D8).

Given 기대 사실을 놓친 문항과 상위 8에 정답 근거가 없는 같은 지문의 검색 기록, When 판정하면, Then 자동 단계는 검색 미적중이다.
Given 기대 사실을 놓친 문항과 상위 8에 정답 근거가 있는 검색 기록, When 판정하면, Then 자동 단계는 작성이다.
Given HTTP 오류로 끝난 턴, When 판정하면, Then 검색 기록과 무관하게 실행 장애다.
Given 지문이 다른 검색 기록만 주어짐, When `report`를 실행하면, Then 그 기록을 거부하고 실행 장애가 아닌 실패는 검색 근거 없음이다.
Given q06 실패와 q06 라벨, When 보고서를 보면, Then 보고 단계는 질문 모호성이고 자동 단계가 옆에 보이며, 알려진 실패 1 · 예상 밖 실패 0으로 센다.
Given q06이 통과한 회차, When 보고서를 보면, Then q06이 통과한 알려진 실패로 나온다.
Given 근거가 빈 라벨, When `report`를 실행하면, Then 라벨 파일을 거부하고 보고서를 만들지 않는다.

검증: `uv run pytest apps/worker/tests/test_ask_replay_reliability_script.py && uv run ruff check . && uv run ruff format --check .`, 네트워크 없이 #232 `answer.json` · `retrieve.json`과 라벨 파일로 `report`를 실행해 q06이 질문 모호성(자동: 검색 미적중)으로 나오는지 확인.

## 5. 비용 상한 안에서 같은 조건의 답변 재생을 여러 회 돌린다 (https://github.com/kanziman/NexusWiki/issues/243)

의존성: 2. 예상: 반나절. 유료 호출: 없음(테스트는 가짜 HTTP 응답).

- [x] 5.1 `ask_replay`의 단일 회차 재생을 함수로 뽑고, `ask_replay_reliability.py repeat`가 회차 수만큼 불러 회차마다 결과 파일과 성적표 줄을 남기게 한다. 총 지출 상한이 없으면 시작하지 않고, 문항을 시작하기 전에 누적과 턴 추정의 합이 상한을 넘으면 멈춘다. 멈춘 회차와 남은 회차를 기록한다. 루프백이 아닌 주소는 거부한다(설계 D5).

Given 지출 상한 없음, When `repeat`를 실행하면, Then 요청 없이 거부한다.
Given 3회차 계획 중 두 번째 회차에서 상한에 닿음, When `repeat`를 실행하면, Then 그 문항을 시작하지 않고 멈추며, 두 번째 회차는 부분 실행, 세 번째 회차는 미실행으로 기록되고 이유는 상한이다.
Given 루프백이 아닌 API 주소, When `repeat`를 실행하면, Then 아무 요청 없이 멈춘다.
Given 정상 완료한 2회차, When 성적표를 보면, Then 회차마다 한 줄씩 두 줄이 더해지고 기존 줄은 그대로다.

검증: `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_ask_replay_reliability_script.py && uv run ruff check . && uv run ruff format --check .`

## 6. 보존된 수집 위에서 반복 재생을 실측하고 기록한다 (https://github.com/kanziman/NexusWiki/issues/244)

진행 기록(2026-11-08): 지문 대조·검색 1회는 성공했다. HTTP 한 문항 점검이 월 예산 402로 실패해 3회 반복은 시작하지 않았다. 사용자가 현재 월 한도 유지를 지정했으므로 한도와 미정산 예약은 변경하지 않았다. 중단 기록과 기존 하네스 1회 재집계만 문서화했으며 아래 두 task는 미완료로 유지한다. 근거: `verification.md`와 `docs/ops/ask-sample-replay.md` 반복 측정 절.

재개 계획 변경(2026-11-08, 사용자 요청): 비용 절감을 위해 HTTP 반복을 3회에서 2회로 줄이고 전체 실행 상한을 $2.00으로 낮춘다. 위 중단 기록은 당시 계획을 보존한다. 월 한도 증액이나 유료 실행은 이번 계획 수정에 포함하지 않는다.

의존성: 1 · 3 · 4 · 5, 그리고 #230 평가가 546xx 스택을 비운 상태. 예상: 반나절. 유료 호출: 있음(검색·점검·반복 전체 상한 $2.00, 실행 전 사용자 별도 승인).

추가 승인(2026-11-08): 사용자가 유료 실행과 필요한 로컬 월 한도 증액을 승인했다. 전체 $2.00 상한 내에서 실행하며 월 한도는 완료 후 원래 값으로 복원한다. OFF/ON 평가 종료 후 같은 546xx 스택을 순차 사용한다.

완료 기록(2026-11-09): 지문 일치, 검색 1회 · 한 문항 점검 · `repeat` 2회차 완료, 실측 $1.543486(상한 $2.00), 월 한도 $5 복원. 근거: `verification.md` 「6절 실측 재개」.

- [x] 6.1 지문이 #232 값과 같은지 대조한다. `retrieval-eval` 1회, 한 문항 점검, `repeat` 2회차를 실행하고, HTTP 2회차와 #232 harness 1회차, 라벨 파일로 `report`를 만든다. `repeat` 상한은 전체 $2.00에서 검색·점검 비용을 뺀 잔액으로 설정한다. 지문이 다르면 #232 회차 없이 보고하고 그 사실을 기록한다(설계 D11).
- [x] 6.2 `docs/ops/ask-sample-replay.md`에 반복 측정 절을, `docs/ops/evaluation-map.md`에 원장 한 줄과 지도 칸(최종 답 정답성 · 거절) 갱신을 남긴다. 원본 기록은 Git 밖 `.worktrees/`에 두고 sha256을 change의 `verification.md`에 적는다.

Given 보존된 수집과 승인된 상한, When 반복 재생과 보고서를 실행하면, Then 회차별 통과 수 · 변동폭 · 흔들린 문항 · 단계별 실패 수 · 알려진/예상 밖 실패 · 거절 3수치가 기록되고, 실제 비용이 상한 이하다.
Given 상한 도달이나 402 같은 중단, When 기록을 보면, Then 부분 회차와 미실행이 구분되고 성공으로 표시되지 않는다.
Given 문서 갱신, When 평가 지도를 보면, Then 수치 옆에 분모 · 회차 수 · 실행 경로 · 합성 샘플 한계가 함께 적혀 있다.

검증: `openspec validate eval-reliability --strict`, 기록 파일 sha256 대조, 실측 비용을 재생 DB `usage_events`와 대조.
