# Tasks — retrieval-evidence-ablation

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/232

## 1. 근거 범위 3종을 본문 벡터로 검색 측정한다 (https://github.com/kanziman/NexusWiki/issues/233)

의존성: 없음. 예상: 1일. 유료 호출: 질의 임베딩만(로컬 검증은 가짜 임베딩).

- [x] 1.1 `RetrievalPolicy`에 `enabled_channels`(기본 1차 4채널)와 검증을 추가하고, `RetrievalService`가 꺼진 채널을 호출하지 않고 "의도적 비활성" 메타로 기록하게 한다. 기본값일 때 `policy_content` 해시가 바뀌지 않게 하고, 기본값이 아닐 때만 해시 입력에 넣는다(설계 D3).
- [x] 1.2 `scripts/retrieval_ablation.py`에 `retrieve` 하위 명령을 만든다. 루프백이 아니면 거부하고, 보존된 수집 결과의 스냅샷 해시와 고정 입력 해시를 계산하고, 질의 벡터를 한 번 만들어 고정한 뒤 `source_only` · `wiki_only` · `both` × `body`를 측정해 `retrieval-ablation-v1` append-only 기록을 쓴다(설계 D1 · D4 · D5 · D6 · D8).

Given 기본 정책, When `policy_content_sha256`를 계산하면, Then 이 change 전과 같은 값이다.
Given `wiki_only` 범위, When 질문 하나를 검색하면, Then 순위에는 위키만 있고 원문 채널은 실패가 아니라 의도적 비활성으로 기록된다.
Given `both` 범위에서 벡터 채널 하나가 실패할 때, When 질문을 측정하면, Then 그 질문은 검색 미적중이 아니라 실행 장애로 분류된다.
Given 이미 있는 출력 경로나 루프백이 아닌 주소, When `retrieve`를 실행하면, Then 아무것도 쓰거나 요청하지 않고 멈춘다.
Given 같은 고정 입력으로 측정한 3조건, When 기록을 보면, Then `source_only` · `wiki_only`에는 `diagnostic: true`가 붙고 모든 조건의 고정 입력 해시가 같다.

검증: `uv run pytest packages/core/tests apps/api/tests/test_retrieval_service.py apps/worker/tests/test_retrieval_ablation_script.py && uv run ruff check . && uv run ruff format --check .`

## 2. 제목 머리말 벡터를 만들고 6조건 검색을 비교한다 (https://github.com/kanziman/NexusWiki/issues/234)

의존성: 1. 예상: 1일. 유료 호출: 제목 벡터 임베딩(상한 $0.10).

- [x] 2.1 로컬 전용 `ablation` 스키마와 실험 벡터 검색 함수를 스크립트가 만들고 `cleanup`으로 지우게 한다. `title_body-v1` 입력(`문서: <실제 제목>\n<본문>`)으로 원문·위키 청크 벡터를 만들고, `(kind, chunk_ref, input_format, embedding_version, text_sha256)`이 모두 같을 때만 재사용한다(설계 D1 · D4).
- [x] 2.2 측정 전에 `body` 벡터를 `ablation`에 복사해 운영 RPC와 채널별 순위·거리가 같은지 확인하고, 다르면 측정하지 않는다(설계 D2). 이후 `retrieve`가 6조건을 측정하게 한다.
- [x] 2.3 `compare` 하위 명령을 만든다. 고정 입력 해시가 다르면 다른 항목을 이름으로 보이고 거부하며, 같은 범위의 `body` → `title_body`와 같은 입력의 `source_only` → `both` 문항별 복구·회귀를 표로 낸다(설계 D5 · D6).

Given 제목이 "배송 정책"인 원문 청크, When `title_body` 입력을 만들면, Then 임베딩 텍스트는 `문서: 배송 정책`과 줄바꿈 뒤 원래 본문이고, 저장된 청크 본문과 인용 좌표는 바뀌지 않는다.
Given 본문은 같고 제목만 바뀐 청크, When 벡터를 준비하면, Then 기존 벡터를 재사용하지 않고 새로 만든다.
Given 실험 함수와 운영 RPC의 순위가 한 질의라도 다를 때, When `retrieve`를 실행하면, Then 측정하지 않고 다른 질의와 채널을 보이며 멈춘다.
Given 질의 벡터 해시가 다른 두 기록, When `compare`를 실행하면, Then 비교를 거부하고 질의 벡터 항목을 이름으로 보인다.
Given 실험 벡터가 있는 상태, When 운영 Ask나 검색 API를 호출하면, Then 결과는 실험 전과 같다.

검증: `uv run pytest apps/worker/tests/test_retrieval_ablation_script.py && uv run ruff check . && uv run ruff format --check .`, 로컬 스택에서 가짜 임베딩으로 `retrieve` → `compare` → `cleanup` 왕복

## 3. 사전 등록한 조건만 답변을 재생하고 진단 판정을 기록한다 (https://github.com/kanziman/NexusWiki/issues/235)

의존성: 2. 예상: 1일. 유료 호출: 이 slice의 테스트에서는 없음(가짜 LLM 스트림).

- [x] 3.1 `register` 하위 명령으로 설계 D7의 선택 규칙과 비용 상한을 검색 측정 전에 기록하고, `answer` 하위 명령이 사전 등록이 검색 기록보다 늦거나 상한이 없으면 거부하게 한다. 조건 선택은 규칙을 검색 기록에 적용해 자동으로 정한다.
- [x] 3.2 `answer`가 `AskService`를 프로세스 안에서 만들어 조건별 `RetrievalService`를 주입하고, 상한에 닿기 전에 멈추며 남은 문항을 "미실행"으로 기록하게 한다. 기대 사실 포함 · 위조 앵커를 모든 조건에, 이중 인용 판정은 `both`에만 붙인다(설계 D6 · D7).
- [x] 3.3 기록에 `publishable` 객체(조건별 집계, 문항 id별 판정·분류, 비용 합계, 한계 문장)를 채우고 `experiment` 식별자가 다른 기록과의 요약을 거부한다(설계 D8).

Given 검색 기록보다 늦게 만든 사전 등록, When `answer`를 실행하면, Then 재생을 거부한다.
Given 다음 턴이 비용 상한을 넘길 때, When 재생이 진행되면, Then 그 전에 멈추고 남은 문항을 미실행으로, 이유를 상한으로 기록한다.
Given 원문만 인용하고 기대 사실을 포함한 `source_only` 답변, When 판정하면, Then 사실 포함으로 세고 진단으로 표시하며 이중 인용 누락으로 표시하지 않는다.
Given 기록의 `publishable`, When 읽으면, Then 질문 원문 · 답변 본문 · 근거 본문 · 워크스페이스 id · 토큰이 없다.
Given 재검색 OFF/ON 실험 기록, When 이 실험 기록과 함께 요약하면, Then 거부한다.

검증: `uv run pytest apps/worker/tests/test_retrieval_ablation_script.py apps/api/tests/test_ask_router.py && uv run ruff check . && uv run ruff format --check .`

## 4. 실제 6조건 실험을 실행하고 결과를 운영 문서에 남긴다 (https://github.com/kanziman/NexusWiki/issues/236)

의존성: 3. 예상: 0.5일. ⚠️ 유료 실행은 시작 전에 사용자 승인을 따로 받는다. 상한 합계 $3.10(설계 D7).

- [x] 4.1 보존된 546xx 수집 결과로 스택을 띄우고 스냅샷 해시를 RRF v2 기록과 대조한다(이탈: RRF 기록에 해시가 없어 워크스페이스 id·문서 제목으로 대조. `verification.md`). 다르면 멈추고 보고한다. 재생 DB 월 한도가 모자라면 사용자 승인 후 재생 전용 로컬 한도를 일시 조정하고 끝난 뒤 복원한다.
- [x] 4.2 `register` → `retrieve`(6조건) → `answer`(선택된 조건) → `compare`를 실행하고 원본 기록을 Git 밖 보존 폴더에 두며 `cleanup`과 스택 정리를 한다.
- [x] 4.3 `docs/ops/ask-sample-replay.md`에 결과 · 해석 · 한계(합성 8문서 · 30문항, 1회 답변 변동, 진단 조건은 제품 통과율과 비교 불가)를, `docs/ops/evaluation-map.md`에 위키 기여 측정 행을 추가한다. 기록 해시는 change의 `verification.md`에 둔다.

Given 승인된 실행, When 실험이 끝나면, Then 6조건 검색 기록과 선택 조건 답변 기록이 같은 고정 입력 해시로 남고 실제 비용이 상한 이하다.
Given 결과 문서, When 위키만 · 원문만 수치를 읽으면, Then "진단"으로 표시되고 이중 인용 통과율과 나란히 비교되지 않는다.
Given 실험 종료, When 로컬 DB를 확인하면, Then `ablation` 스키마가 없고 운영 임베딩 행은 실험 전 해시와 같다.

검증: `openspec validate retrieval-evidence-ablation --strict`, 기록 파일 해시가 `verification.md`와 일치, 보존 폴더 확인

## 5. 마무리 검증

- [x] 5.1 새로 실행: `packages/core` · API 검색/Ask 서비스 · 실험 스크립트 테스트 · ruff check · ruff format --check · `openspec validate retrieval-evidence-ablation --strict` · `openspec validate --specs`
