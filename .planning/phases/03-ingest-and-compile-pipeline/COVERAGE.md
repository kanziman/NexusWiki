# API Coverage — OpenRouter (LLM 채팅 + 임베딩)

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
>
> Phase 3의 외부 API 표면은 **OpenRouter 하나**다. `03-CONTEXT.md > D-04`가 임베딩
> 공급자를 OpenRouter로 닫으면서 LLM(COMP-01)과 임베딩(COMP-06)이 같은 `base_url`과
> 같은 `OPENROUTER_API_KEY`를 쓰게 되었다. 두 번째 공급자는 이 페이즈에 없다.
>
> ⚠️ 이 표는 **뺄셈의 기록**이다. 모든 능력은 INTEGRATE에서 시작하고, OPT-OUT은
> 한 줄 사유를 반드시 동반한다. 사유 없는 OPT-OUT은 결정되지 않은 구멍이며 이 게이트가
> 닫으려는 실패 양상 그 자체다.

## 1. Chat Completions — `POST https://openrouter.ai/api/v1/chat/completions`

| capability | decision | reason |
|---|---|---|
| `POST /chat/completions` (비스트리밍) | INTEGRATE | |
| `model` 슬러그 선택 (`LLM_MODEL`) | INTEGRATE | |
| `response_format: {type:"json_schema"}` | INTEGRATE | |
| `provider: { require_parameters: true }` (능력 탐지) | INTEGRATE | |
| 응답 `usage` (prompt/completion/total tokens) | INTEGRATE | |
| 응답 `usage.cost` / 비용 필드 | INTEGRATE | |
| 응답 `provider` (실제 서빙 공급자) | INTEGRATE | |
| `GET /models` (모델 목록·능력 조회) | INTEGRATE | |
| `stream: true` (SSE 스트리밍) | OPT-OUT | 컴파일은 워커 배치 잡이라 스트리밍 소비자가 없다 — 답변 스트리밍은 Phase 5 API-01의 범위 |
| tool calling / function definitions | OPT-OUT | 컴파일러가 모델에게 도구를 주지 않는다 — 소스는 데이터이지 실행 권한이 아니다 |
| 프롬프트 캐싱 (Anthropic 네이티브) | OPT-OUT | OpenRouter 경유로 네이티브 캐싱을 쓸 수 없다 (CLAUDE.md Constraints) — 비용 재검토는 P4-OPS-01 |
| Predicted Outputs (prefill 지연 최적화) | OPT-OUT | 지연이 아니라 정확도가 컴파일의 제약이다 |
| Assistant prefill | OPT-OUT | not needed — 구조화 출력은 `response_format` + Pydantic 검증이 담당 |
| 플러그인 — web search | OPT-OUT | explicitly out of scope — 위키는 투입된 소스만으로 컴파일된다 (이중 Citation의 전제) |
| 플러그인 — PDF parsing | OPT-OUT | PDF는 `pypdf`로 로컬 추출한다 — provider 파싱은 원문 `char_start`/`char_end` 좌표를 주지 않아 이중 Citation이 성립하지 않는다 |
| 플러그인 — response healing / context compression | OPT-OUT | 스키마 위반 복구는 COMP-03의 오류 되먹임 재시도가 소유한다 (`decisions.llm`의 필수 백스톱) |
| 멀티모달 입력 (image / audio / video) | OPT-OUT | 스캔본은 `needs_ocr`로 실패시키는 것이 ING-04의 결정이다 — 이미지 경로를 열면 그 게이트가 무의미해진다 |
| reasoning tokens | OPT-OUT | not needed yet — 컴파일 품질 튜닝은 Phase 4 골든 세트 이후 |
| `logit_bias` / penalties / `top_k` | OPT-OUT | not needed — 기본 샘플링으로 충분하고 파라미터마다 재현성 축이 하나씩 늘어난다 |
| `GET /generation?id=` (생성 통계) | OPT-OUT | 응답 본문의 `usage`가 이미 토큰·비용을 준다 — 추가 왕복은 같은 값을 두 번 사는 것 |
| `GET /credits` · `GET /key` (계정 잔액·키 정보) | OPT-OUT | 예산의 단위가 다르다 — OPS-01은 **워크스페이스별** 월 상한이고 `usage_events`가 그것을 소유한다. 계정 잔액은 워크스페이스를 구분하지 않아 상한 판정에 쓸 수 없다 |
| Model routing fallback (`models: [...]` 배열) | OPT-OUT | 모델이 바뀌면 컴파일 산출물의 성격이 바뀐다 — `LLM_MODEL` 단일 슬러그가 재현성의 축이다 |
| BYOK (Bring Your Own Key) | OPT-OUT | not needed — 단일 `OPENROUTER_API_KEY` |

## 2. Embeddings — `POST https://openrouter.ai/api/v1/embeddings`

| capability | decision | reason |
|---|---|---|
| `POST /embeddings` | INTEGRATE | |
| `model` (`baai/bge-m3`) | INTEGRATE | |
| `input` 배열 배치 | INTEGRATE | |
| `encoding_format: "float"` | INTEGRATE | |
| `provider.order: [...]` | INTEGRATE | |
| `provider.allow_fallbacks: false` | INTEGRATE | |
| `provider.data_collection: "deny"` | INTEGRATE | |
| 응답 `usage` (토큰·비용) | INTEGRATE | |
| 응답 `provider` 대조 (요청한 호스트와 같은지) | INTEGRATE | |
| `dimensions` (차원 축소 요청) | OPT-OUT | `0008`이 컬럼을 `extensions.vector(1024)`로 못 박았다 — 요청 측 축소는 스키마와 어긋나고 `embedding_version`이 기록하는 축을 하나 더 늘린다 |
| 멀티모달 임베딩 (image content array) | OPT-OUT | Phase 3는 dense 텍스트 1024차만 다룬다 (`03-CONTEXT.md > <deferred>`) |
| bge-m3 sparse / multi-vector 출력 | OPT-OUT | `open_questions`가 Phase 4 RTV-06 골든 질의 세트로 판정하기로 이미 정했다 |

## 3. 미확정 값 (구현 시점에 확인하고 기록할 것)

두 값은 이 표의 결정이 아니라 **아직 관측되지 않은 사실**이다. 값을 지어내지 말 것.

| 값 | 확인처 | 기록처 |
|---|---|---|
| `LLM_MODEL` 슬러그 (`checklists.json > decisions.llm.openrouter_slug`가 `TODO`) | `GET https://openrouter.ai/api/v1/models` | `.env.sample` · `checklists.json` · `docs/ops/openrouter-contract-record.md` |
| `EMBEDDING_PROVIDER` 호스트 슬러그 (D-05의 `provider.order` 원소) | `https://openrouter.ai/baai/bge-m3` 공급자 목록 | `.env.sample` · `docs/ops/openrouter-contract-record.md` |
