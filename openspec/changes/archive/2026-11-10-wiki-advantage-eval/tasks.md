# Tasks — wiki-advantage-eval

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/260

## 1. 금지 사실 판정과 유형 시험지 검사 (https://github.com/kanziman/NexusWiki/issues/261)

의존성: 없음. 예상: 반나절. 유료 호출: 없음.

- [x] 1.1 `scripts/ask_replay.py`에 `forbidden_hit`을 더하고 `verdict`의 실패 순서를 상태 → 위조 앵커 → 기대 사실 → 금지 사실 → 이중 인용으로 한다. 재생 행에 `forbidden_hit`을 남긴다(설계 D4).
- [x] 1.2 `check-sample` 하위 명령을 만들고 `seed`가 수집 전에 부르게 한다. 유형 · 개수 · `multi_doc` · `conflict` · `long_noisy` · `distractor` · 금지 사실 위치 조건을 검사한다. 유형 필드가 없는 기존 시험지는 검사 대상이 아니다(설계 D3).
- [x] 1.3 `seed --monthly-budget-micros`가 새 워크스페이스를 만든 직후, 문서를 넣기 전에 그 워크스페이스 월 한도를 낮춘다(설계 D5).

Given 기대 사실과 금지 사실을 함께 말한 답, When `verdict`를 계산하면, Then 실패이고 이유는 금지 사실이다.
Given 금지 사실 필드가 없는 기존 30문항 기록, When 오프라인 회귀 관문을 돌리면, Then 기대값이 그대로 통과한다.
Given 기대 사실이 한 문서에 그대로 있는 `multi_doc` 문항, When `check-sample`을 돌리면, Then 그 문항과 문서를 지목하며 실패한다.
Given 옛 값이 금지 사실에 없는 `conflict` 문항, When `check-sample`을 돌리면, Then 실패한다.
Given 유형이 없는 문항이 섞인 유형 시험지, When `seed`를 실행하면, Then 수집을 시작하지 않는다.

검증: `uv run pytest apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_model_evidence_eval_script.py && uv run python scripts/check_eval_regression.py && uv run ruff check scripts/ask_replay.py scripts/retrieval_ablation.py scripts/model_evidence_eval.py apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_model_evidence_eval_script.py && uv run ruff format --check scripts/ask_replay.py scripts/retrieval_ablation.py scripts/model_evidence_eval.py apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_model_evidence_eval_script.py`

## 2. 위키 유리 시험지 작성과 고정 (https://github.com/kanziman/NexusWiki/issues/262)

의존성: 1. 예상: 1일. 유료 호출: 없음.

- [x] 2.1 `scripts/fixtures/wiki_advantage.v1.json`을 쓴다. 문서 약 29개(긴 문서 4개 4,000~7,000자, `family` 3무리 × 3개, 시행일 있는 옛/새 5쌍), 질문 44개(`multi_doc` · `conflict` · `long_noisy` · `distractor` 각 10, `refusal` 4)(설계 D2).
- [x] 2.2 `check-sample`을 통과시키고, 시험지 형식과 검사 통과를 테스트로 고정한다(설계 D3 · D9).

Given 새 시험지, When `check-sample`을 돌리면, Then 통과하고 유형별 문항 수를 보인다.
Given 새 시험지, When 테스트가 유형을 세면, Then 답할 수 있는 유형마다 8개 이상, 거절 3개 이상이다.

검증: `uv run python scripts/ask_replay.py check-sample --sample scripts/fixtures/wiki_advantage.v1.json && uv run pytest apps/worker/tests/test_ask_replay_script.py`

## 3. 전 단계 상한 · 유형 기록 · 효과 판정 · 유형별 성적표 (https://github.com/kanziman/NexusWiki/issues/263)

의존성: 1. 예상: 1일. 유료 호출: 없음.

- [x] 3.1 `model_evidence_eval.py`에 `budget-open`(총 상한 · 컴파일 모델 · 답변 모델 · 시험지 해시, 컴파일 모델 = 답변 모델이면 거부)과 `ingest-record`(잡 실패 · 위키 쪽수 · 수집 지출)를 만든다. `register`는 `budget.json`이 있으면 재생 상한을 총 상한 − 워크스페이스 지출로 정하고, 수집 기록이 실패면 거부하고, 효과 기준을 기록한다(설계 D5 · D7).
- [x] 3.2 턴 행에 `qtype` · `forbidden_hit` · `fact_correct`를, 성적표 줄에 조건별 사실 정답 수를 더한다(설계 D8).
- [x] 3.3 효과 판정(모델별 · 전체 `supported` · `not_supported` · `inconclusive`)과 모델 × 유형 표, 거절 구역을 성적표에 그린다(설계 D7 · D8).

Given 컴파일 모델이 답변 모델 중 하나인 예산 개시, When `budget-open`을 실행하면, Then 그 모델을 지목하며 거부된다.
Given 컴파일 잡 하나가 실패한 수집 기록, When `register`를 실행하면, Then 거부된다.
Given 총 상한 1,000,000과 수집 지출 80,000, When `register`를 실행하면, Then 재생 상한은 920,000 이하다.
Given 옛 값과 새 값을 함께 말한 `conflict` 턴, When 턴 행을 만들면, Then `forbidden_hit`이 참이고 `fact_correct`가 거짓이다.
Given 최소 3 · 모델 2 기준과 늘 복구 4 · 늘 회귀 0인 모델 두 개, When 판정을 내면, Then 그 모델들과 전체가 `supported`다.
Given 완료 회차가 1개뿐인 모델, When 판정을 내면, Then 그 모델은 `inconclusive`다.
Given 거절 문항이 두 조건에서 다르게 나온 기록, When 성적표를 그리면, Then 거절 구역에만 나오고 복구 · 회귀에 세지 않는다.

검증: `uv run pytest apps/worker/tests/test_model_evidence_eval_script.py && uv run ruff check scripts/ask_replay.py scripts/retrieval_ablation.py scripts/model_evidence_eval.py apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_model_evidence_eval_script.py && uv run ruff format --check scripts/ask_replay.py scripts/retrieval_ablation.py scripts/model_evidence_eval.py apps/worker/tests/test_ask_replay_script.py apps/worker/tests/test_model_evidence_eval_script.py`

## 4. 실측과 기록 (총 상한 $1.00) (https://github.com/kanziman/NexusWiki/issues/264)

의존성: 2 · 3. 예상: 반나절. 유료 호출: 있음(수집 · 컴파일 · 임베딩 · 점검 · 재생, 총 $1.00 이하).

- [x] 4.1 `budget-open` → 저가 컴파일 워커로 `seed --monthly-budget-micros <총 상한>` → `retry-dead`(dead 잡만 제품 API로 재시도) → `ingest-record` → `retrieval_ablation retrieve` → `register` → 점검 → `plan` → 재생을 실행하고, 성적표와 효과 판정을 낸다(설계 D5 · D6 · D7).
- [x] 4.2 `docs/ops/ask-sample-replay.md`에 결과 절(효과 판정 · 유형별 위키 차이 · 실패 신호 · 비용 · 한계)을, change의 `verification.md`에 기록 sha256 · 실측 지출 · 계획 이탈을 남긴다.

Given 총 상한 $1.00, When 실측이 끝나면, Then 실험 워크스페이스의 전체 지출이 1,000,000 micros 이하다.
Given 실측 기록, When 성적표를 열면, Then 전체 효과 판정과 모델 × 유형 위키 차이가 보인다.

검증: `uv run python scripts/model_evidence_eval.py scoreboard --dir <실험 디렉터리> --html <파일>`, 재생 DB 지출 조회, `openspec validate wiki-advantage-eval --strict`
