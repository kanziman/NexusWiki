## Context

동기는 proposal.md의 Why를 본다. 설계를 좌우하는 현재 사실은 다음과 같다.

- `scripts/retrieval_ablation.py`의 `answer`는 프로세스 안에서 `AskService`를 조건별 `scope_policy`와 고정 질의 벡터(`FixedQueryEmbeddingClient`)로 만들고, LLM 호출만 워커 내부 리스너(`/internal/llm-chat`)로 보낸다. 원문만 조건은 HTTP Ask로는 만들 수 없어서 이 경로가 유일하다.
- 답변 모델은 워커 프로세스의 `LLM_MODEL` 하나로 정해진다. `scripts/ask_replay_serve.sh`는 이를 `.env`에서만 읽고, 같은 값으로 `ASK_COST_POLICIES`를 만든다(정책이 없으면 Ask가 503). 워커 리스너는 8081 고정이라 한 번에 한 벌만 뜬다.
- `retrieval_ablation`의 `SELECTION_RULE`은 코드 상수이고 `bothxtitle_body`를 조건부로 재생한다. 이 실험에 그대로 쓰면 원치 않는 조건이 예산을 쓴다.
- #237 기록(`.worktrees/ablation-evidence-20261108/`)의 `retrieve.json`에 고정 입력 해시가, `answer.json`에 Sonnet `source_onlyxbody` · `bothxbody` 30문항 행이 있다. 문항당 입력 약 4,900~5,800 · 출력 약 530~600토큰이었다.
- 2026-11-09 OpenRouter 공개 가격으로 모델당 2조건 30문항 추정치는 Haiku 5.5 $0.049 · GPT-6 Luna $0.049 · DeepSeek V4.1 Flash $0.036이다. 같은 식의 Sonnet 추정 $1.476은 실측 $1.461과 맞았다. 세 모델 모두 추론을 지원하고 워커는 추론 옵션을 보내지 않는다.
- Ask는 수리 실패 시 상태 `fallback`으로 끝나고, 수리 호출은 같은 trace의 두 번째 `usage_events` 행으로 남는다.

## Goals / Non-Goals

**Goals:**

- 모델 · 조건 · 회차가 달라도 수집 · 검색 · 프롬프트 · 판정이 같은 기록을 만든다.
- 총 지출이 등록 상한 $1.00을 넘지 않는다는 것을 기록으로 보일 수 있다.
- 사람이 브라우저 한 화면에서 모델별 위키 차이와 실패 신호를 읽는다.

**Non-Goals:**

- 공개 쇼케이스 · curated 원장 반영(다른 세션 작업 중), 대시보드 코드 변경
- Sonnet 재실행, 저가 모델 위키 컴파일, `wiki_only` · `title_body` 조건
- 추론 옵션 조정. 제품 요청 형태 그대로 각 모델의 기본 추론 동작을 잰다.
- 회차를 합친 신뢰 구간이나 유의성 검정. 회차는 독립 표본이 아니다.
- 워커 리스너 포트 설정화 같은 제품 코드 변경

## Decisions

### D1. 새 스크립트가 ablation의 프로세스 내 답변 경로를 재사용한다

`scripts/model_evidence_eval.py`를 추가하고 `retrieval_ablation.py`를 경로로 불러와 `load_corpus` · `scope_policy` · `FixedQueryEmbeddingClient` · `turn_row` · 판정 함수를 그대로 쓴다. 기각한 대안: (a) `retrieval_ablation`에 모델 축을 더한다 — 그 스펙은 "정확히 6조건"과 검색 선행 등록을 계약으로 갖고 있어 의미가 섞인다. (b) HTTP Ask로 재생한다 — 근거 범위를 제한할 수 없다. 세 갈래 비교를 만들 만한 실질 대안이 없어 이 근거만 기록한다(게이트 2).

### D2. 모델 전환은 워커 재기동, 서버 스크립트에 두 옵션

`ask_replay_serve.sh`에 `ASK_REPLAY_LLM_MODEL`(있으면 `.env`의 `LLM_MODEL` 대신 쓰고 `ASK_COST_POLICIES`도 그 모델로 만든다)과 `ASK_REPLAY_WORKER_ONLY=1`(API를 띄우지 않음)을 더한다. `.env`는 바꾸지 않는다. 실행기 `scripts/model_evidence_run.sh`가 회차 × 모델마다 워커를 띄우고 리스너 준비를 기다린 뒤 `run`을 부르고 내린다. 리스너가 8081 고정이라 모델별 워커를 동시에 띄우는 방식은 기각했다.

모델 일치는 턴마다 `usage_events.model`로 확인한다(스펙: served model). 불일치는 측정 장애로 즉시 멈춘다.

### D3. 사전 등록 · 점검 · 계획 세 기록

- `register`: 모델 3종, 조건 2종, 회차 최대 3 · 최소 1, 상한 1,000,000 micros, 점검 문항 `q01`, 안전계수 1.5, 고정 입력(재사용할 `retrieve.json`의 `fixed_inputs` 사본과 그 파일 sha256). 내용 해시를 함께 쓴다.
- `probe`: 모델마다 `bothxbody`로 `q01` 1턴. 상태 · 모델 · 토큰 · 비용 · 잘림을 기록한다. 등록보다 늦어야 한다.
- `plan`: 점검 기록만 읽는다. 실패 모델 제외, `rounds = max{r ∈ [min, max] : spent + r × 남은 모델 수 × 60턴 × max(점검 턴 비용) × 1.5 ≤ cap}`. 정답 필드는 읽지 않는다(읽을 필드를 화이트리스트로 제한).

### D4. 지출의 진실 공급원은 재생 DB

상한 검사의 지출은 기록 파일 합이 아니라 재생 DB `usage_events`에서 등록 시각 이후 · 재생 워크스페이스의 전체 `cost_micros` 합으로 센다. 실행이 중간에 죽어 기록이 안 남아도 지출은 잡힌다. 턴 직전 검사: `spent + 다음 턴 추정 ≤ cap`, 추정은 그 모델에서 지금까지 관측한 턴 비용 최댓값(점검 포함) × 안전계수.

### D5. 회차 우선 실행과 순서 집행

`run --round R --model M`은 계획에서 앞선 (회차, 모델) 기록이 모두 있어야 시작한다. 한 실행은 그 모델의 두 조건을 연달아 30문항씩 돈다. 상한으로 멈추면 남은 턴을 `not_run`으로 남기고 부분 기록을 쓴다. 턴 행은 조건별 목록에 바로 쌓여서, 예외로 죽어도 `finally`에서 과금된 턴과 두 조건의 성적표 줄을 남긴다. 실행 장애가 3턴 연속이면(402 · 워커 다운) 그 실행을 멈춰, 분모만 줄어든 회차가 완료 회차로 집계되지 않게 한다. 실행이 멈추면 실행기가 `close`로 시작하지 못한 계획 실행을 미실행 기록과 성적표 줄로 남긴다. 실행기는 이전 워커 리스너가 30초 안에 내려가지 않으면 다음 모델로 넘어가지 않는다. 기존 기록 경로는 덮어쓰지 않는다.

성적표 화면은 줄이 가리키는 실행 기록의 등록 · 고정 입력 · 답변 프롬프트 해시가 기준(등록, 회차 순서상 첫 실행)과 같은 줄만 합산한다. 다른 줄은 실행별 표에 남기고 합산에서 뺀 개수를 표시한다(리뷰 r1 반영).

### D6. 턴 판정

`turn_row`의 필드에 다음을 더한다: `llm_calls`(비임베딩 사용량 행 수), `repair_attempted`(`llm_calls > 1`), `fallback`(상태 `fallback`), `truncated`(어느 호출이든 `completion_tokens ≥ max_tokens`; `max_tokens`는 워커 런타임 manifest의 정책 값), `measurement_failure`(사용량 없음 · 모델 불일치). 사실 포함은 기존 `keyword_hit`, 제품 통과는 `bothxbody`에만 기존 `verdict`. 거절 문항 `q30`은 따로 센다. 판정은 장애를 문항 종류보다 먼저 거른다: 채널 실패나 상태가 `resolved` · `fallback` · `no-evidence` 밖이면 거절 문항이어도 실행 장애이고 거절 분모에서 빠진다. 턴 도중 예외로 끝난 턴은 `interrupted`(측정 장애)로 남겨 묻지 않은 턴과 구분한다(리뷰 r2 반영).

### D7. JSONL 성적표와 화면

실험 디렉터리의 `scoreboard.jsonl`에 실행마다 한 줄을 덧붙인다(필드는 스펙). `import-reference`가 #237 `answer.json`의 Sonnet 두 조건을 `reference: true`, `round: null`로 한 번 싣는다. `scoreboard` 명령은 dart-workbench `sec01/scoreboard.py`와 같은 표준 라이브러리 `http.server`로 `127.0.0.1:8801`(8800은 dart-workbench 성적표가 쓴다)에서 요청마다 파일을 다시 읽어 그린다. 위에는 모델 요약(조건별 사실 포함 · 위키 차이 · 안정성 · 늘 복구/회귀 문항), 아래에 실행별 행. `--html`로 같은 화면을 정적 파일로 낸다. 문항별 집계는 줄이 가리키는 실행 기록을 읽어 만든다. 모든 값은 `html.escape`를 거친다. 기존 `ask_replay` 성적표와 같은 다크 톤만 빌리고 외부 자산은 쓰지 않는다.

### D8. 재생 월 한도

재생 DB 월 한도에 이 실험 상한 + 여유($1.10)가 들어갈 자리가 없으면 그만큼만 일시 올리고, 끝나면 원래 값으로 되돌린다. 사용자가 $1 실측과 끝까지 진행을 승인했다(2026-11-09). 기존 미정산 예약은 지우지 않는다.

## Risks / Trade-offs

- [기본 추론이 출력 1,500토큰을 잠식해 답이 잘림] → 점검에서 잘림을 기록하고 화면 첫 열에 둔다. 잘림이 많은 모델의 사실 포함 하락은 모델 실력이 아니라 요청 형태 한계로 표시한다.
- [`data_collection` 거부로 공급자 라우팅 실패] → 점검이 실행 장애로 잡아 그 모델만 제외한다.
- [가격이 등록 뒤 바뀜] → 상한은 실측 `usage_events`로 집행하므로 추정이 틀려도 넘지 않는다. 회차가 줄 수 있다.
- [30문항 · 3회차의 작은 표본] → 1문항 3.4%p. 위키 효과는 "모든 완료 회차에서 복구된 문항"으로만 주장한다.
- [Sonnet 기준선은 원문만이 1회뿐] → `reference`로만 표시하고 모델 간 순위에 넣지 않는다.
- [다른 세션의 eval 페이지 작업] → `apps/dashboard`와 curated 원장 파일을 건드리지 않는다.

## Migration Plan

배포 대상이 없다. 실험 원본은 Git 밖 `.worktrees/model-evidence-20261109/`에 두고, 결과 요약과 해시를 `docs/ops/ask-sample-replay.md`와 change의 `verification.md`에 남긴다. 끝나면 워커를 내리고 월 한도를 원래 값으로 되돌린다. 546xx 스택과 수집 볼륨은 유지한다.
