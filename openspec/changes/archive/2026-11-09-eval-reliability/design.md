## Context

동기는 `proposal.md`, 계약은 이 change의 delta spec 두 개(`ask-replay-reliability` · `ask-replay-scorecard`)를 본다.

확인한 코드 사실:

- `scripts/ask_replay.py`의 `verdict`는 행 필드만 읽어 재채점한다. `ask` 결과 행에는 고정 입력(수집 스냅샷 · 정책 버전 · 프롬프트 해시 · k)이 없고, 턴별 채널 실패(`missing_channels`)도 기록하지 않는다. `ask`는 `requested_k`를 보내지 않아 서버 기본값 8을 쓴다(`apps/api/src/api/routers/ask.py`).
- Ask SSE `meta` 이벤트에 `policy_version`과 `missing_channels`가 이미 실린다(`apps/api/src/api/services/ask.py`). 운영 코드를 바꾸지 않고 재생 쪽에서 읽을 수 있다.
- #232의 수집 스냅샷 지문 `snapshot_inputs`와 `canonical_sha256`, 프롬프트 해시 `_default_ask_prompt_sha256`은 `scripts/retrieval_ablation.py` 안에 있다. 이 파일은 `api` · `nexuswiki_core`를 import하고 `ask_replay.py`를 모듈로 불러 쓴다. 따라서 `ask_replay.py`가 이 파일을 import하면 순환이 생긴다.
- #232 답변 기록(`answer.json`)의 행은 `ask` 결과 행과 필드가 같고(`status` · `keyword_hit` · `cited_*_count` · `fabricated_anchor_count` · `answer`), 조건별로 `conditions[].rows`에 들어 있다. 기록 최상위에 `experiment` · `fixed_inputs` · `answer_prompt_sha256`이 있다. 검색 기록(`retrieve.json`)은 조건 · 문항별 분류(`hit` 등)와 첫 적중 순위를 갖는다.
- 기존 통과율 95% 구간 표기(28/30 → 78.7~98.2%)는 Wilson 구간과 일치한다.
- ⚠️ #227(`ask-evidence-research`)이 다른 worktree에서 커밋 전 상태로 `scripts/ask_replay.py`와 `ask-replay-scorecard` 스펙을 고치고 있다.

## Goals / Non-Goals

**Goals:**

- 게이트 2에서 승인된 구조(B)로 delta spec 10개 요구사항을 구현한다.
- `ask_replay.py`의 변경을 추가형 필드 · 거절 분리 · 공용 함수 이동으로 한정해 #227과의 충돌 면적을 줄인다.
- #232 기록과 같은 정의의 지문을 써서, 보존된 수집 위의 새 재생이 #232 회차와 한 묶음이 될 수 있게 한다.
- 반복 재생 실측 1회분과 측정 기록을 남긴다(546xx 스택이 빈 뒤).

**Non-Goals:**

- 거절 문항 추가. 질문 fixture가 바뀌면 기존 30문항 기준선과 #227 fixture가 함께 흔들린다. 정확한 거절은 표본 1개로 남고, 보고서가 이 한계를 적는다.
- 재수집 변동. 수집을 다시 하면 위키 컴파일이 달라진다(11쪽 vs 13쪽). 이번 변동폭은 같은 수집 위의 답변 변동만 뜻한다.
- q06 수정(#195 A)과 질문 문구 변경. q06은 라벨 파일의 알려진 실패로만 남는다.
- 회귀 CI 관문, 모델 비교, LLM 판사, 위키 컴파일 품질 채점.
- 성적표 HTML의 통과율 95% 구간 표시와 반복 보고서의 HTML 화면. 반복 보고서는 JSON 기록과 Markdown 요약만 낸다.
- 원인 판정의 "근거" 단계(검색은 맞았지만 컨텍스트 조립에서 빠짐). 턴의 실제 컨텍스트 구성이 결과에 남지 않아 판정할 수 없다. 이 경우는 "작성"으로 묶이며 한계로 적는다.
- 운영 코드 · DB 마이그레이션 · 검색 정책 · Ask 계약 · 기존 판정 규칙 변경.
- 같은 묶음에 다른 코드 revision이 섞일 때의 코드 효과 분리. revision은 기록만 한다.

## Decisions

### D1. 새 스크립트 + 지문 공용 모듈 (게이트 2 승인)

| 파일 | 역할 |
| --- | --- |
| `scripts/eval_fingerprint.py` (새) | 순수 함수만 둔다: `canonical_sha256`, `snapshot_inputs`, fixture 해시. 네트워크와 무거운 import가 없다 |
| `scripts/ask_replay.py` (추가형) | 결과 행 · 결과 최상위에 고정 입력 기록, `retrieval-eval` 기록에 지문 추가, 거절 3수치(요약 · 성적표 줄 · 화면), 수집 테이블 조회와 프롬프트 해시 함수를 공용으로 노출 |
| `scripts/retrieval_ablation.py` (경로만) | 지문 · 해시 · 테이블 조회 · 프롬프트 해시를 위 두 곳에서 가져온다. 동작은 같다 |
| `scripts/ask_replay_reliability.py` (새) | `repeat`(유료, 비용 상한 필수)과 `report`(오프라인). 묶음 · 안정성 · 실행 경로 · 원인 판정 · 라벨 · 알려진 실패 |
| `scripts/fixtures/ask_replay_labels.v1.json` (새) | 사람 원인 라벨. 첫 항목은 q06 |

기각한 대안:

- **A. `ask_replay.py`에 전부**: 기존 `retrieval-eval` 추가 방식과 같지만, 54K 파일이 더 커지고 #227과의 충돌 면적이 가장 크다. 지문 정의도 두 벌이 되어 조용히 어긋나면 같은 수집이 거부된다.
- **C. `nexuswiki_core` 라이브러리**: 엄격한 테스트를 얻지만 core는 API와 워커로 배포되는 패키지다. 합성 평가 코드는 제품이 아니다.

### D2. 지문 정의는 한 곳, #232 값으로 고정

수집 테이블을 읽는 열 목록이 곧 해시 대상이다. 그래서 조회 함수(`ask_replay.snapshot_tables`)도 한 곳에 두고 #232의 `load_corpus`가 그것을 부르게 바꾼다. 요청자 JWT로 PostgREST를 읽는 기존 방식 그대로다.

이동 전 `snapshot_inputs`로 작은 고정 테이블의 해시를 계산해 테스트에 박아 두고, 이동 후에도 같은 값이 나오는지 확인한다. 실측 단계에서는 보존된 수집의 지문이 #232 `fixed_inputs.snapshot_sha256`(`65809ec4e3b673c5…`)과 같은지 대조한다.

### D3. 재생 결과의 고정 입력

- 결과 최상위: `fixed_inputs` = `snapshot_sha256` · `fixture_sha256` · `answer_prompt_sha256` · `requested_k` · `model`, 그리고 턴들에서 모은 `policy_versions`.
- `ask`는 `requested_k=8`을 명시해 보내고 그 값을 기록한다. 서버 기본값에 기대지 않는다.
- 결과 행: SSE `meta`의 `policy_version`과 `missing_channels`를 추가한다. 원인 판정의 실행 장애 단계가 이 값을 쓴다.
- 값을 얻지 못하면 `"unknown"`을 쓴다. 묶음에서 `"unknown"`은 다른 값과 같지 않은 것으로 보고 거부한다(빈 값을 같다고 가정하지 않는다).
- 묶음 키의 정책은 회차 안 모든 턴의 `policy_version`이 하나일 때만 그 값이다. 둘 이상이면 그 회차는 묶음에서 거부한다.

### D4. 거절 3수치

`summarize`에 `answerable_asked` · `answerable_passed` · `refusal_asked` · `refusal_correct` · `false_refusals`를 더한다. 판정은 기존 `verdict`와 `is_refusal`을 그대로 쓴다.

- 정확한 거절은 답할 수 없는 문항의 `verdict` 통과다.
- 잘못된 거절은 답할 수 있는 문항이 `no-evidence`로 끝났거나, `resolved`이면서 `is_refusal`이 참인 경우다.

성적표 줄에도 같은 필드를 더한다. 화면은 줄에 필드가 없으면 결과 파일 행에서 다시 계산하고, 결과 파일도 없으면 "-"로 표시한다. `refusal_asked = 0`이면 정확한 거절은 `null`이다.

### D5. 반복 재생 (`repeat`)

- `ask_replay`의 단일 회차 재생을 함수로 뽑고(`run_replay`), `repeat`가 회차 수만큼 부른다. 회차마다 결과 파일 하나와 성적표 줄 하나가 쌓이므로 기존 화면에서도 보인다.
- `--max-total-spend-micros`가 없으면 시작하지 않는다.
- 문항을 시작하기 전에 `누적 + 턴 추정 > 상한`이면 멈춘다. 턴 추정은 `--turn-estimate-micros`(기본 30,000, 실측 문항당 약 $0.027)와 지금까지 관측한 최대 턴 비용 중 큰 값이다. 기존 `ask`처럼 넘은 뒤에 멈추지 않는다.
- 멈춘 회차는 `stopped: {"reason": "spend_cap", "asked": n}`를 남기고, 남은 회차는 `not_run`으로 결과 없이 기록한다.
- 루프백 검사는 기존 `assert_loopback`을 쓴다.

### D6. 묶음과 #232 소비 (`report`)

- 입력은 HTTP 결과 파일 여러 개, 선택적으로 #232 답변 기록 하나, 검색 기록 0~N개, 라벨 파일이다.
- #232 답변 기록은 `experiment == "retrieval-evidence-ablation"`이고 `phase == "answer"`일 때만 받는다. 조건은 `scope == "both"`, `embedding_input == "body"`인 것 하나만 꺼내 `harness` 회차로 만든다. 고정 입력은 기록의 `fixed_inputs`와 `answer_prompt_sha256`에서 가져온다.
- 묶음 키가 하나라도 다르면 묶음을 거부하고 다른 키를 이름으로 보인다.

### D7. 안정성 · 변동폭 계산

- 문항별 `passed/asked`를 계산하고, 미실행은 분모에 넣지 않는다.
  - `asked`가 0이면 `not_run`이다.
  - 전부 통과하면 `stable_pass`, 전부 실패하면 `stable_fail`, 그 밖은 `unstable`이다.
- 답할 수 있는 문항 기준으로 회차별 통과 수, 최소 · 최대 · 평균 통과율, 회차별 Wilson 95% 구간을 낸다.
  - 회차를 합친 구간은 내지 않는다. 같은 30문항의 반복은 독립 표본이 아니기 때문이다.
- 경로가 섞이면 `http`만의 값과 전체 값을 둘 다 낸다.
- 거절 3수치도 회차별로 함께 보인다.

### D8. 원인 판정

검색 근거는 지문이 같은 기록만 쓴다. `retrieval-eval` 기록, 또는 #232 `retrieve.json`의 `both × body` 조건이다. 둘 다 있으면 `retrieval-eval`을 쓰고, 둘의 판정이 다르면 그 사실을 보고한다.

자동 단계는 다음 순서로 정한다.

1. **실행 장애**: 상태가 HTTP 오류(`http_*`) · `error` · `unknown`이다. 또는 행의 `missing_channels`가 비어 있지 않다. `no-evidence`와 `fallback`은 실행 장애가 아니라 다음 단계로 넘긴다.
2. **검색 미적중**: 검색 기록상 상위 8에 정답 근거가 없다.
3. **작성**: 그 밖의 경우다.
4. 검색 기록이 없으면 2, 3 대신 **검색 근거 없음**으로 둔다.

답할 수 없는 문항이 거절하지 않은 실패는 정답 문서가 없으므로 바로 **작성**이다.

라벨이 있으면 보고 단계는 라벨 원인이고, 자동 단계를 옆에 함께 적는다.

### D9. 라벨 파일

```json
{"version": 1, "labels": [
  {"id": "q06", "cause": "question_ambiguity", "known_failure": true,
   "evidence": "#232 retrieval-evidence-ablation: 원문만 조건에서 정답 원문 6위에도 반품 검수 48시간으로 답함",
   "note": "‘입고 검수’가 반품 검수와 모호하다"}
]}
```

- `cause`는 `question_ambiguity` · `grader_error` · `other` 중 하나다.
- `evidence`가 비었거나, `id`가 fixture에 없거나, `cause`가 집합 밖이면 파일 전체를 거부한다.
- 답변 본문은 넣지 않는다. `note`는 사람이 쓴 한 줄 설명이다.

### D10. 보고서 기록

- 스키마는 `ask-replay-reliability-v1`의 JSON이다. 이미 있는 경로는 입력을 읽기 전에 거부한다.
- 담는 것: 묶음 키, 회차별 라벨 · 경로 · revision · 비용 · 멈춤 상태, 문항별 안정성 · 자동 단계 · 라벨 단계 · 알려진 실패 여부, 단계별 개수, 한계 문장.
- 담지 않는 것: 질문 · 답변 · 근거 본문, 워크스페이스 id, 토큰.
- Markdown 요약은 표준 출력으로 낸다.

### D11. 실측 계획 (마지막 slice, 유료)

2026-11-08 추가 승인: 사용자가 전체 작업의 유료 실행과 필요한 로컬 월 한도 증액을 승인했다. 앞선 현재 한도 유지 제약은 이 승인으로 대체된다. 실측 전체 지출 상한 $2.00은 유지하고, 재생 전용 월 한도는 예약 여유를 확보하도록 일시 증액한 뒤 원래 값으로 복원한다. 미정산 예약은 삭제하지 않는다.

- 선행 조건은 세 가지다.
  - #230 평가가 546xx 스택을 비웠다.
  - 보존된 수집의 지문이 #232 값과 같다.
  - 사용자가 유료 실행을 별도로 승인했다.
- 순서는 다음과 같다.
  1. `retrieval-eval` 1회. 임베딩만 쓰고 $0.01 미만이다.
  2. 한 문항 점검.
  3. `repeat` 2회차.
  4. `report`(HTTP 2회 + #232 harness 1회, 라벨 적용).
- 예상 비용은 HTTP 2회 × 이전 실측 $0.756626 + 한 문항 점검 약 $0.03으로 약 $1.54다. 검색·점검·반복을 포함한 전체 실행 상한은 **$2.00**(2,000,000 micros)이다. `repeat`에는 전체 상한에서 앞서 지출한 검색·점검 비용을 뺀 잔액을 전달한다.
- 재생 DB의 월 한도($5)에 기존 사용액이 쌓여 402가 날 수 있다. 이때는 #232처럼 사용자 승인 후 재생 전용 로컬 한도를 일시 조정했다가 복원한다. 미정산 예약은 지우지 않는다.
- 결과는 `docs/ops/ask-sample-replay.md`의 새 절과 `docs/ops/evaluation-map.md`의 원장 한 줄 · 지도 칸(거절 · 최종 답 정답성)에 남긴다. 원본 기록은 Git 밖 `.worktrees/`에 두고 해시만 남긴다.

## Risks / Trade-offs

- [#230이 546xx 스택의 수집을 바꾸거나 지움] → 실측 시작 시 지문을 #232 값과 대조한다. 다르면 #232 harness 회차는 묶음에서 거부되고, #232 검색 기록도 원인 판정에 쓸 수 없다. 이 경우 HTTP 회차와 새 `retrieval-eval`만으로 보고하고 그 사실을 기록한다. 재수집은 이 change 안에서 하지 않는다.
- [#227과 `ask_replay.py` · `ask-replay-scorecard` 스펙 충돌] → 변경을 추가형으로 한정한다. 늦게 머지하는 쪽이 충돌을 해소하며, 스펙은 양쪽 모두 ADDED 요구사항이라 sync 때 합쳐진다.
- [지문 함수 이동이 #232 해시를 바꿈] → 이동 전 값을 박은 고정 테스트와 기존 `test_retrieval_ablation_script.py`로 막는다.
- [검색 단계 판정이 그 턴의 실제 컨텍스트가 아님] → 같은 수집 위의 별도 검색 호출임을 보고서에 적는다. 질의 임베딩이 매번 새로 계산되어 순위가 미세하게 다를 수 있다.
- [2회차는 변동폭을 재기에 적음] → 두 번의 관측이 다른 문항과 관측 범위만 보고하고, 두 번 통과했다는 사실을 일반적인 안정성 보장으로 읽지 않는다. 분산 추정치는 내지 않는다. 하네스 1회는 별도 경로로 표시한다. 회차를 더 늘리는 것은 비용 상한 안에서 다음 실측의 몫이다.
- [harness 회차가 HTTP 경로와 다름] → 경로를 표시하고, HTTP만의 값을 항상 함께 낸다.
- [거절 표본 1개] → 정확한 거절은 분모와 함께만 보이고, 보고서 한계에 적는다.

## Migration Plan

DB 마이그레이션과 운영 배포는 없다. 되돌리기는 커밋 revert로 충분하다.

옛 결과 파일과 성적표 줄은 고치지 않는다(append-only). 새 필드가 없는 옛 결과는 화면에서 행 필드로 거절 수치를 다시 계산하고, 묶음에서는 지문 누락으로 거부된다.

## Open Questions

### 2026-11-08 실측 중단 기록

중단 이후 사용자가 비용 절감을 위해 반복 횟수 축소를 요청했다. 재개 계획은 HTTP 3회에서 2회로 줄이고 전체 실행 상한도 $3.00에서 $2.00으로 낮춘다. 질문 30개와 점검 1개는 유지해 새 답변은 총 61개다. 이 계획 수정은 월 한도 증액이나 유료 재실행 승인이 아니며, 기존 미실행 기록은 당시 3회 계획 그대로 보존한다.

사용자가 6절 실행과 로컬 재생 계정 비밀번호 재설정을 승인했으며, 월 한도는 현재 값을 유지하도록 지정했다. 수집·fixture·프롬프트 해시는 #232와 일치하고 검색 평가도 성공했으나 한 문항 점검이 내부 예산 402로 실패했다. 기존 한도 $5보다 유효 사용·예약액 $7.835789가 커 3회 반복은 시작하지 않았다. 이번 지출은 임베딩 31 micros다. 중단 상태와 과거 하네스 1회 재집계를 기록하되 6절을 완료 처리하지 않는다. 월 한도를 올리거나 미정산 예약을 지우는 우회는 하지 않았다. 상세 증거와 해시는 `verification.md`에 둔다.

없음. 회차 수를 늘릴지는 첫 실측 결과를 본 뒤 비용 상한과 함께 다시 정한다. 스펙 · 구조 · task 분해는 바뀌지 않는다.
