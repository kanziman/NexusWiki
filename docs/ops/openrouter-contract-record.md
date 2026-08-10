# OpenRouter 계약 관측 기록 (COMP-01 · COMP-06)

## 관측 일시

- 2026-08-08 KST
- 하네스: `scripts/smoke_pipeline.sh` (채팅) · 일회성 `POST /v1/embeddings` 프로브 (임베딩)
- 관련 태스크: P2-LLM-01 · 플랜 `03-04-PLAN.md`

이 문서는 `checklists.json > decisions.llm.openrouter_slug`의 `TODO`와 `open_questions`의
"OpenRouter의 정확한 모델 슬러그 확인"을 닫는 관측 기록이다. 근거를 재서술하지 않고
**관측한 값만** 적는다.

## 기계가 읽는 줄

아래 세 줄은 `03-04-PLAN.md`의 acceptance criteria가 `grep`으로 읽는 계약이다.
사람이 읽는 산문은 그 아래에 따로 둔다.

observed_embedding_provider: DeepInfra
observed_embedding_dimensions: 1024
observed_embedding_usage_fields: present

## 1. 채팅 모델 슬러그 — 확정

| 항목 | 값 |
| --- | --- |
| 확정 슬러그 | `anthropic/claude-sonnet-4.6` |
| 확인처 | `GET https://openrouter.ai/api/v1/models` (200, 400개 모델) |
| 가격 | prompt `0.000003` / completion `0.000015` USD per token |
| 응답 `provider` | `Anthropic` |
| 응답 `model` | `anthropic/claude-sonnet-4.6` |

⚠️ **`.env`와 `.env.sample`에 있던 `anthropic/claude-3.5-sonnet`은 더 이상 존재하지 않는다.**
그 슬러그로 `POST /chat/completions`를 부르면 **404**가 돌아온다. 이 사실은 tracer 스모크가
드러냈다 — `parse`는 succeeded인데 `compile`이 `ProviderError: openrouter 호출 실패
(kind=chat_completion, status=404)`로 실패했다. 슬러그 오류가 배포가 아니라 첫 end-to-end
실행에서 드러난 것이 tracer를 이 페이즈 앞에 둔 이유 그 자체다.

`checklists.json > decisions.llm.default_model`의 `claude-sonnet-4-6`과 그 `openrouter_slug`
추정("`anthropic/claude-sonnet-4.6` 형태로 추정")은 **맞았다**. 추정이 맞았다는 것도
관측으로만 알 수 있다.

## 2. `response_format` 능력 탐지 — 통과했다

요청 본문에 `response_format={"type":"json_schema", "json_schema":{..., "strict":true}}`와
`provider={"require_parameters":true}`를 함께 실었고, **1회차가 그대로 200으로 돌아왔다.**

- 폴백 경로(`worker.llm_structured_output_unsupported`)는 이 모델·이 엔드포인트에서
  **한 번도 타지 않았다.**
- 스키마 위반 재시도(`worker.llm_schema_violation`)도 **한 번도 타지 않았다** — 1회차 출력이
  `CompileResult`를 그대로 만족했다.

⚠️ 그래도 프롬프트 + Pydantic 검증 + 3회 재시도는 그대로 돈다. `response_format`은
엔드포인트별 지원이라 **선택적 최적화**이고, 필수 백스톱은 그와 무관하게 항상 있어야 한다
(`checklists.json > decisions.structured_output`). 폴백 경로 자체는
`apps/worker/tests/test_llm.py::test_a_4xx_on_the_structured_request_falls_back_to_prompt_only`가
고정한다 — 실호출에서 타지 않았다고 코드에서 지우면, 모델을 바꾸는 날 조용히 깨진다.

## 3. 채팅 호출 1회의 실제 사용량과 비용

`scripts/smoke_pipeline.sh`가 만든 워크스페이스의 `usage_events` 한 행(실측):

| 항목 | 값 |
| --- | ---: |
| `provider` | `Anthropic` |
| `model` | `anthropic/claude-sonnet-4.6` |
| `prompt_tokens` | 3,230 |
| `completion_tokens` | 196 |
| `cost_micros` (올림 후) | **12,504** |

⚠️ 응답의 `cost` 원값은 기록하지 않았다 — 워커는 올림한 정수만 `usage_events`에 남기고
원값을 로그에도 싣지 않기 때문이다. 위 정수로부터 역산하면 실제 값은
`0.012503 < cost <= 0.012504` USD 구간에 있다. 같은 워크스페이스의 두 번째 컴파일은
`cost_micros = 12,492`였다(출력 길이가 조금 달랐다).

올림 변환은 `math.ceil(dollars * 1_000_000)`이다. 내림하면 상한 판정이 지출을 **과소평가하는**
방향으로 틀려 상한을 넘긴 뒤에야 걸린다. 과대평가 방향의 오차는 상한을 조금 일찍 걸 뿐이다.

⚠️ 요청 본문에 `"usage": {"include": true}`를 명시적으로 싣는다. 이 키가 없으면 응답에 비용
필드가 없을 수 있고, 그러면 `cost_micros = 0`이 기록되어 `0009`의 월 상한($5.00)이 **영원히
걸리지 않는다**(T-03-27). 상한이 있는데 걸리지 않는 것은 상한이 없는 것보다 나쁘다 —
있다고 믿게 만들기 때문이다.

한 소스(3,230 프롬프트 토큰)당 약 **$0.0125**다. 기본 월 상한 $5.00은 이 크기의 소스
**약 400건**에 해당한다.

## 4. 임베딩 계약 — 일회성 프로브

`POST https://openrouter.ai/api/v1/embeddings`를 **딱 한 번** 불렀다. 요청:

```
model            = baai/bge-m3
input            = "이 문장은 임베딩 계약을 관측하기 위한 한 줄이다."  (한 개)
encoding_format  = float
provider         = {"order": ["deepinfra/fp32"], "allow_fallbacks": false, "data_collection": "deny"}
```

응답(200):

| 항목 | 관측값 |
| --- | --- |
| 최상위 키 | `data` · `id` · `model` · `object` · `provider` · `usage` |
| `provider` | **`DeepInfra`** |
| `model` | `BAAI/bge-m3` |
| `len(data)` | 1 |
| `len(data[0].embedding)` | **1024** |
| `usage` | `{"prompt_tokens": 18, "total_tokens": 18, "cost": 1.8e-07, "is_byok": false, "cost_details": {...}}` |

### 4a. 1024차 — `0008`과 일치한다

**`0008_embedding_dimension.sql`이 하드코딩한 `extensions.vector(1024)`가 실제 응답과
같다.** 이 확인이 wave 4에 있는 이유는 `0008`이 wave 1에서 **이미 클라우드에 push되어
되돌릴 수 없기** 때문이다. 임베딩 엔드포인트의 첫 실호출은 원래 03-09(wave 6)인데, 거기서
차원이 어긋났다면 그 발견이 되돌릴 수 없는 마이그레이션 **뒤에서** 일어나고 이 페이즈 안에
구제 경로가 없다. 한 번의 호출로 그 창을 닫았다.

### 4b. 공급자 슬러그의 두 형태 — 플랜 가정의 정정

⚠️ **요청에 싣는 슬러그와 응답이 돌려주는 이름이 다르다.**

| 방향 | 값 |
| --- | --- |
| 요청 (`provider.order` 원소, `.env`의 `EMBEDDING_PROVIDER`) | `deepinfra/fp32` |
| 응답 (`provider` 필드) | `DeepInfra` |

`03-04-PLAN.md`의 acceptance criteria는 이 둘이 **같은 문자열일 것**을 전제했다
(`observed_embedding_provider`가 `.env.sample`의 `EMBEDDING_PROVIDER`와 같다). 실제 API는
그렇지 않다. 그래서 위 「기계가 읽는 줄」에는 **관측한 그대로** `DeepInfra`를 적었다 —
게이트를 통과시키려고 관측하지 않은 값을 적는 것은 이 저장소가 금지한 것이다.

플랜이 실제로 확인하려던 것("요청한 호스트가 실제로 서빙했다")은 **참이다**:
`allow_fallbacks: false`로 `deepinfra/fp32`를 고정했고 DeepInfra가 서빙했다. 다른 호스트가
서빙했다면 `allow_fallbacks: false` 때문에 200이 아니라 오류가 왔을 것이다.

03-09의 임베딩 핸들러는 이 두 형태를 **둘 다** 알아야 한다 —
`EmbeddingProviderMismatch`(`worker/errors.py`)의 비교는 응답의 표시명과 요청 슬러그를
직접 문자열 비교하면 항상 불일치로 판정한다. 매핑을 그 플랜이 소유한다.

`baai/bge-m3`의 엔드포인트는 관측 시점에 둘이다:

| provider_name | tag | context_length | prompt 가격 |
| --- | --- | ---: | --- |
| DeepInfra | `deepinfra/fp32` | 8,192 | 0.00000001 |
| Parasail | `parasail` | 8,194 | 0.00000001 |

`/fp32` 접미를 붙여 **양자화까지 고정한 것은 의도**다. 같은 호스트가 fp16으로 서빙하면
벡터가 미묘하게 달라질 수 있고, 섞인 벡터는 재임베딩 외에 복구 수단이 없다 (D-05).

### 4c. 임베딩 비용

18 프롬프트 토큰에 `1.8e-07` USD = 0.18 micro-dollar → 올림 **1 micro-dollar**.
채팅 대비 무시할 수준이며(같은 워크로드에서 채팅이 4~5자리 크다) 상한 판정에서 임베딩은
사실상 반올림 오차다. 그럼에도 `usage_events`에 `kind='embedding'`으로 남긴다 — 기록이
없으면 나중에 "무시해도 되는지"를 다시 관측해야 한다.

## 5. 이 플랜의 총 OpenRouter 지출

| 항목 | 값 |
| --- | ---: |
| tracer 개발 중 스모크 실행 | 3회 (1회는 404로 컴파일 0건) |
| 실제 성공한 채팅 완성 | 4회 (스모크 2회 × 각 2 컴파일) |
| 채팅 비용 합 | 약 $0.050 |
| 임베딩 프로브 | 1회, 약 $0.0000002 |
| **이 플랜 총계** | **약 $0.05** |

계정 잔액은 이 플랜 시작 시점에 **$5.00**이었고 그것이 프로젝트 전체 예산이다. 남은 약
$4.95가 wave 5~7(03-05 · 03-06 · 03-07 · 03-08 · 03-09)과 Phase 4~5의 실호출 전부를
덮어야 한다. 한 소스당 $0.0125라는 실측이 그 계획의 유일한 기준선이다.

## 6. 03-09 파이프라인 임베딩 관측 — 2026-08-10 KST

`EMBEDDING_MODEL=baai/bge-m3`, `EMBEDDING_PROVIDER=deepinfra/fp32`를 **스모크 실행에만**
주입해 `scripts/smoke_pipeline.sh`를 실행했다. `.env`에는 이 값을 쓰지 않았다.

| 경로 | 응답 `provider` | 응답 `model` | prompt tokens | `cost_micros` |
| --- | --- | --- | ---: | ---: |
| source chunks | `DeepInfra` | `BAAI/bge-m3` | 76 | 1 |
| wiki chunks | `DeepInfra` | `BAAI/bge-m3` | 92 | 1 |

스모크 SQL 관측값은 source·wiki 모두 `vector_dims(embedding)=1024`,
`count(distinct embedding_version)=1`, source chunk의 null embedding 0행, wiki embedding
1행이었다. `cost_micros`는 워커가 `ceil(cost_usd * 1_000_000)`로 기록한 정수다.

같은 `raw_source_id`의 parse를 다시 인큐한 뒤에도 source chunks=1, wiki pages=1,
wiki links=1, wiki embeddings=1 및 `kind='embedding'` usage events=2로 모두 동일했다.
즉, 같은 `embedding_version`의 위키 행을 다시 OpenRouter에 보내던 결함을 수정한 뒤
재처리 비용 0과 행 멱등성을 실제 스택에서 확인했다. 워크스페이스 삭제 cascade 뒤 jobs=0도
관측했다.

## 한계

이 문서가 **관측하지 않은 것**을 명시한다. 없는 관측을 추론으로 메우지 않는다.

1. **공급자를 고정해 가용성을 의도적으로 희생했다** (D-05). `allow_fallbacks: false`이므로
   DeepInfra에 장애가 나면 임베딩 잡이 **실패한다**. 폴백을 허용하면 잡은 항상 성공하지만
   워크스페이스 안에 섞인 벡터가 남고 그건 재임베딩 외에 복구 수단이 없다. 복구 가능한
   실패를 복구 불가능한 성공보다 택했다. 장애 시 동작은 관측하지 않았다.

2. **`search_tsv`를 tracer가 비워 두었다.** `worker.handlers.parse`는 `source_chunks`에
   `search_tsv`와 `tsv_tokenizer_version`을 쓰지 않는다 — `tsvector` 값을 만드는
   `to_tsvector`를 애플리케이션이 PostgREST로 부를 수 없기 때문이다. 어휘 채널(RTV)은
   Phase 4의 범위이며, 그때 `0010`이 색인용 RPC를 추가하는 것이 "검색 쿼리는 마이그레이션이
   소유한다"(`decisions.db_transport`)와 일치한다.
   ⚠️ **그때까지 수집된 청크는 어휘 검색에 잡히지 않는다.** Phase 4는 색인 RPC를 만든 뒤
   기존 행의 소급 색인을 함께 계획해야 한다.

3. **컴파일 입력은 `COMPILE_MAX_INPUT_TOKENS`(기본 24,000)에서 잘릴 수 있다.** 잘림은
   `worker.compile_input_truncated` 경고로만 드러나고 잡은 성공으로 기록된다. 긴 소스의
   뒷부분이 위키에 반영되지 않는 이 경계는 관측된 적이 없다 — 스모크의 본문이 청크 1개다.
   여러 청크에 걸친 긴 소스의 컴파일 품질은 이 플랜이 확인하지 않았다.

4. **공급자 고정의 장애 경로는 관측하지 않았다.** 03-09는 source·wiki 영속화와 같은
   `embedding_version` 재처리 비용 0을 실제로 확인했지만, DeepInfra 장애 시 `embed` 잡만
   실패하고 compile은 계속되는 동작, 다중 입력 배치의 순서 보장, 네트워크 재시도는 아직
   실호출로 확인하지 않았다. `embedding_version`을 바꾸면 모든 청크를 다시 임베딩해야 하며,
   비용은 청크 수에 선형으로 늘어난다.

5. **1회차 출력이 스키마를 만족했으므로 되먹임 재시도의 실효는 실호출로 확인되지 않았다.**
   재시도가 같은 본문의 반복이 아니라는 것은 단위 테스트가 고정하고 있고(위 §2), 실제
   모델이 오류 되먹임을 받고 **고쳐 내는지**는 아직 모른다.

6. **컴파일 산출은 페이지 1개짜리 한 사례뿐이다.** `COMPILE_MAX_PAGES`(8) 상한, 한 배치 안의
   슬러그 충돌(`-2` 접미), `pages: []`(빈 결과) 경로는 전부 코드와 단위 테스트에만 있고
   실제 모델 출력으로 확인되지 않았다.
