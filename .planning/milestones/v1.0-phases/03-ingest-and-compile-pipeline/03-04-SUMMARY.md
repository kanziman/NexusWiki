---
phase: 03-ingest-and-compile-pipeline
plan: 04
subsystem: pipeline
tags: [tracer, llm, openrouter, job-chain, upsert, idempotency, cost-accounting, prompt-injection]
requires:
  - "supabase/migrations/0006_seed_prompts.sql (컴파일 프롬프트 · {{변수}} 규약 · 빈 pages 유효)"
  - "supabase/migrations/0007_search_and_queue_extensions.sql §2 §3 §8 (jobs_dedup_idx · complete_job_and_chain · 최소권한 매트릭스)"
  - "supabase/migrations/0009_pipeline_ops.sql (enqueue_source_job · usage_events · 53400/42501)"
  - "packages/core/src/nexuswiki_core/chunking.py · slug.py · tokenizer.py · domain.py (03-03 산출물)"
  - "apps/worker/src/worker/queue.py (핸들러 예외 → fail_job 경로)"
  - "apps/api/src/api/routers/workspaces.py (라우터 템플릿) · errors.py (단일 등록 지점)"
provides:
  - "worker.errors — ProviderError · LlmSchemaError · EmbeddingProviderMismatch"
  - "worker.llm — openrouter_client · render_template · complete_structured · LlmResult"
  - "worker.handlers.parse — PARSE_JOB_TYPE · handle_parse · run_parse · SourceNotExtractedError"
  - "worker.handlers.compile — COMPILE_JOB_TYPE · handle_compile · run_compile · CompiledPage · CompileResult"
  - "ServiceDb 도메인 헬퍼 11종 + complete_job_and_chain RPC 헬퍼"
  - "api.routers.sources — POST /workspaces/{id}/sources/text (202 · 409 · 402 · 413)"
  - "api.errors — SourceAlreadyIngested · BudgetExceeded · TextTooLarge + 렌더 3종"
  - "api.db.user — insert_one · rpc (요청자 JWT로 definer RPC)"
  - "ApiSettings.MAX_TEXT_CHARS · WorkerSettings 컴파일/임베딩 설정 5종"
  - "scripts/smoke_pipeline.sh (end-to-end, 출력 토큰 smoke_pipeline: ok)"
  - "docs/ops/openrouter-contract-record.md (관측 기록 + 한계 6건)"
affects:
  - "03-05 파일 수집 — insert_one · content_hash 규칙(바이트 해싱은 다른 규칙)이 이 라우터 위에 선다"
  - "03-06 URL·추출 — parse의 SourceNotExtractedError 분기와 update_raw_source_content가 그 자리"
  - "03-07 잡·예산 라우터 — UserDb.rpc가 request_job_cancel/retry_dead_job의 통로"
  - "03-08 워커 기동 가드·마스킹 — sanitize_error의 provider 마스킹, OPENAI_API_KEY 제거"
  - "03-09 link_sync·embed — complete_job_and_chain에 인자 두 개 · parse에 enqueue 한 줄 · EMBEDDING_* 설정 소비"
  - "Phase 4 어휘 채널 — source_chunks.search_tsv가 비어 있어 소급 색인이 필요하다"
tech-stack:
  added: []
  patterns:
    - "클라이언트 팩토리는 settings를 인자로 받고 모듈 전역을 두지 않는다 (openrouter_client가 service_client 형태를 그대로 따름)"
    - "핸들러는 얇은 진입점(handle_*)과 db 주입 본체(run_*)로 나눠 네트워크 없이 테스트 가능하게 둔다"
    - "프롬프트 치환은 re.sub 콜백 단일 스캔 — 치환 결과를 재스캔하지 않는 것이 프롬프트 인젝션 완화의 실물"
    - "예외 클래스에 응답 본문을 담을 필드를 두지 않는다 — 마스킹보다 앞선 1차 방어선"
    - "비용은 정수 micro-dollar로 올림 — 과소평가는 상한을 넘긴 뒤에 걸리고 과대평가는 조금 일찍 걸 뿐"
    - "설정 테스트의 불변식은 '필드 개수 0'이 아니라 'secret 부재' + 명시적 허용 목록"
key-files:
  created:
    - apps/worker/src/worker/errors.py
    - apps/worker/src/worker/llm.py
    - apps/worker/src/worker/handlers/parse.py
    - apps/worker/src/worker/handlers/compile.py
    - apps/api/src/api/routers/sources.py
    - apps/worker/tests/test_llm.py
    - apps/api/tests/test_sources_router.py
    - scripts/smoke_pipeline.sh
    - docs/ops/openrouter-contract-record.md
  modified:
    - apps/worker/src/worker/settings.py
    - apps/worker/src/worker/db/service.py
    - apps/worker/src/worker/handlers/__init__.py
    - apps/worker/tests/test_handlers.py
    - apps/worker/tests/test_service_client.py
    - apps/api/src/api/settings.py
    - apps/api/src/api/errors.py
    - apps/api/src/api/db/user.py
    - apps/api/src/api/main.py
    - apps/api/tests/conftest.py
    - packages/core/tests/test_settings.py
    - .env.sample
    - checklists.json
    - .planning/WINDOWS.md
decisions:
  - "D-P7 컴파일 산출은 소스 1건 → 페이지 0..N, COMPILE_MAX_PAGES(8) 상한 — 상한 없는 페이지 목록은 상한 없는 청구서다"
  - "D-P8 같은 (workspace_id, slug)는 내용 덮어쓰기 + sources 합집합 — 통째로 덮으면 다른 소스의 역참조가 사라져 이중 Citation이 끊긴다"
  - "D-P9 슬러그는 앱이 소유한다 — LLM의 slug 필드는 받되 쓰지 않고, taken에 기존 슬러그를 넣지 않는다(넣으면 재컴파일마다 -2가 붙어 증식)"
  - "D-P10 잡 4종 dedup 키 규약 기록 (embed만 <rsid>:source / <rsid>:wiki)"
  - "EMBEDDING_MODEL/PROVIDER는 코드 기본값 없이 None — 소비자가 없는 설정을 필수로 만들면 CI와 스모크가 값을 지어내야 한다"
  - "요청 슬러그(deepinfra/fp32)와 응답 provider 표시명(DeepInfra)은 다른 문자열 — 게이트를 맞추려 관측값을 바꾸지 않았다"
  - "ApiSettings에 필드를 더할 때 SEC-01 단언은 secret 부재 + 허용 목록으로 정정한다 (느슨하게 만들지 않는다)"
metrics:
  duration: "1h05m"
  completed: 2026-08-08
actuals:
  tokens: 41800
  tasks: 2
  commits: 2
status: complete
---

# Phase 3 Plan 04: 수집→컴파일 tracer Summary

텍스트 한 건이 `POST /sources/text`에서 202로 접수되어 `parse → compile` 체인을 지나 실제
`wiki_pages` 행이 되는 **가장 얇은 실제 경로**를 실제 OpenRouter 호출과 함께 끝까지 뚫었고,
그 과정에서 `.env`가 들고 있던 모델 슬러그가 죽어 있다는 사실과 `0008`이 못 박은 임베딩
1024차가 맞다는 사실이 함께 드러났다.

## 무엇을 했나

| Task | 내용 | 커밋 |
|---|---|---|
| 1 (tracer) | 예외 3종 · LLM 클라이언트 · 핸들러 2종 · 도메인 헬퍼 11종 · 인큐 라우터 · 스모크 | `0472223` |
| 2 (TDD) | 계약 테스트 27종 + OpenRouter 미확정 값 3건의 관측 종결 | `82f9970` |

## 관측 결과

### end-to-end가 실제로 돈다

```
smoke_pipeline: 202 job=… raw_source=…
smoke_pipeline: 409 already_ingested
smoke_pipeline: 잡 체인 완료 — parse=succeeded compile=succeeded
smoke_pipeline: chunks=1 pages=1 usage_events=1
usage: Anthropic anthropic/claude-sonnet-4.6 prompt=3230 completion=196 cost_micros=12504
smoke_pipeline: 멱등 확인 — chunks=1 pages=1
smoke_pipeline: ok
```

마지막 두 줄이 이 tracer의 핵심 관측이다. 같은 `parse` 잡을 한 번 더 인큐해 체인을 통째로
다시 돌렸을 때 **청크도 페이지도 늘지 않았다** — at-least-once 큐에서 재처리가 정상 경로라는
전제가 코드가 아니라 실행으로 참이 됐다.

### tracer가 즉시 드러낸 것 — 죽은 모델 슬러그

`.env`·`.env.sample`·`checklists.json`이 들고 있던 `anthropic/claude-3.5-sonnet`은 OpenRouter에
**더 이상 존재하지 않는다**. 첫 스모크에서 `parse`는 succeeded인데 `compile`이 404로 실패했다.

이것이 tracer를 페이즈 앞에 두는 이유의 실물이다. 층을 하나씩 완성해 올라갔다면 이 404는
`link_sync`와 임베딩까지 구현한 wave 6에서 처음 드러났을 것이고, 그때는 이미 그 위에 세 층이
커밋되어 있었을 것이다. 실제로 잃은 것은 조회 한 번과 값 하나였다.

확정: **`anthropic/claude-sonnet-4.6`** (`GET /api/v1/models`, 200, 400개 모델 중).
`checklists.json`의 추정("`anthropic/claude-sonnet-4.6` 형태로 추정")은 맞았지만, 맞았다는
것도 관측으로만 알 수 있다.

### 임베딩 계약 — 되돌릴 수 없는 마이그레이션과 일치한다

일회성 프로브 한 번(`POST /v1/embeddings`, 약 $0.0000002):

| 기계가 읽는 줄 | 값 |
|---|---|
| `observed_embedding_dimensions` | **1024** |
| `observed_embedding_provider` | `DeepInfra` |
| `observed_embedding_usage_fields` | `present` |

`0008_embedding_dimension.sql`이 하드코딩한 `extensions.vector(1024)`가 실제 응답과 같다.
`0008`은 wave 1에서 이미 클라우드에 push되어 되돌릴 수 없고, 임베딩의 첫 실호출은 원래
03-09(wave 6)였다. 어긋났다면 그 발견이 되돌릴 수 없는 마이그레이션 **뒤에서** 일어나고 이
페이즈 안에 구제 경로가 없었다. 한 번의 호출로 그 창을 닫았다.

### `response_format` 능력 탐지는 통과했다

`response_format(json_schema, strict)` + `provider.require_parameters=true`를 실은 1회차가 그대로
200으로 돌아왔고, 폴백(`worker.llm_structured_output_unsupported`)도 스키마 재시도
(`worker.llm_schema_violation`)도 **실호출에서는 한 번도 타지 않았다.** 그래도 두 경로 모두
코드와 단위 테스트로 남아 있다 — `response_format`은 엔드포인트별 지원이라 선택적 최적화이고,
Pydantic 3회 재시도는 그와 무관한 필수 백스톱이다.

### 비용 기준선

| 항목 | 값 |
|---|---:|
| 소스 1건(프롬프트 3,230토큰 · 완성 196토큰)당 | **약 $0.0125** |
| 이 플랜의 총 OpenRouter 지출 | **약 $0.05** (채팅 4회 + 임베딩 프로브 1회) |
| 남은 계정 잔액 | **약 $4.95** |

⚠️ **$5.00이 프로젝트 전체 예산이고 그것이 `0009`의 워크스페이스 월 상한과 같은 값이다.**
남은 $4.95가 wave 5~7(03-05·06·07·08·09)과 Phase 4~5의 실호출을 전부 덮어야 한다.
소스 1건당 $0.0125라는 실측이 그 계획의 유일한 기준선이며, 기본 월 상한은 이 크기의 소스
약 400건에 해당한다.

### 게이트

`bash scripts/smoke_pipeline.sh` exit 0 (`smoke_pipeline: ok`) · `uv run pytest -rs`
**200 passed** (기존 173 + 신규 27) · `uv run ruff check apps packages` exit 0 ·
`bash scripts/ci_check_service_usage.sh` exit 0 (52 files) ·
`pre-commit run --all-files` 통과 · `sorted(HANDLERS) == ['compile','noop','parse']` ·
`grep -c '^observed_embedding_dimensions: 1024$'` = 1.

**테스트가 red가 되는 것까지 확인했다.** 되먹임 턴 두 줄을 제거하자 `test_llm.py` 2종이,
`get_wiki_page_by_slug`에서 `workspace_id` 필터를 빼자 스코프 단언이 실제로 깨졌다.
통과가 조용한 통과가 아니다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `LLM_MODEL` 슬러그가 404였다**

- **Found during:** Task 1 (첫 스모크 실행)
- **Issue:** `.env`·`.env.sample`의 `anthropic/claude-3.5-sonnet`이 OpenRouter에 없어
  `compile` 잡이 `ProviderError(status=404)`로 실패했다. 슬러그 확정은 플랜상 Task 2의 일인데
  Task 1의 스모크가 그 값 없이는 통과할 수 없다 — 순서 의존이 실행에서 드러난 형태다.
- **Fix:** `GET /api/v1/models`로 `anthropic/claude-sonnet-4.6`을 확인해 `.env`와 `.env.sample`을
  정정했다. Task 2가 그 관측을 `docs/ops/openrouter-contract-record.md`와 `checklists.json`에 기록했다.
- **Files modified:** `.env.sample` (`.env`는 gitignore)
- **Commit:** `0472223`

**2. [Rule 2 - Missing critical functionality] 요청에 `usage: {include: true}`를 명시**

- **Found during:** Task 1 (`_chat_body` 작성)
- **Issue:** 플랜은 "비용 필드가 없으면 `cost_micros = 0`으로 두되 경고"까지만 지시했다. 그런데
  `cost_micros = 0`이 기록되면 `0009`의 월 상한($5.00)은 **영원히 걸리지 않는다** — 인큐 시점
  판정이 `sum(cost_micros) >= cap`이기 때문이다. 경고 로그는 남지만 상한은 사라지고, 상한이
  있는데 걸리지 않는 것은 상한이 없는 것보다 나쁘다(있다고 믿게 만든다).
- **Fix:** 요청 본문에 `"usage": {"include": true}`를 실어 비용 회계를 **명시적으로 요청**한다.
  실측에서 `cost` 필드가 실제로 돌아와 `cost_micros=12504`가 기록됐다. 0 폴백과 경고는
  그대로 남겨 뒀다 — 공급자가 바뀌면 다시 없어질 수 있는 필드다.
- **Files modified:** `apps/worker/src/worker/llm.py`
- **Commit:** `0472223`

**3. [Rule 3 - Blocking] 플랜의 헬퍼 목록에 `prompt_templates`·`source_chunks` 조회가 없었다**

- **Found during:** Task 1 (compile 핸들러 작성)
- **Issue:** 플랜 (f)는 "`prompt_templates`에서 기본 템플릿을 워크스페이스 우선·전역 폴백으로
  읽는다"와 "`source_chunks`를 순서대로 이어 붙인다"를 지시했으나, (d)의 헬퍼 목록에 두 조회가
  없다. 헬퍼 없이 쓰려면 핸들러가 `_select`를 직접 부르게 되고 그것은
  `test_service_client.py`의 분류 단언(모든 공개 헬퍼는 `TABLE_HELPERS`나 `RPC_HELPERS`)을
  우회하는 경로를 만든다.
- **Fix:** `get_default_prompt_template(*, workspace_id, target_type)`와
  `list_source_chunks(*, workspace_id, raw_source_id)`를 `TABLE_HELPERS`에 등록해 추가했다.
  둘 다 `workspace_id` keyword-only·무기본값이며 전역 템플릿 폴백도 `workspace_id=is.null`을
  명시적으로 싣는다.
- **Files modified:** `apps/worker/src/worker/db/service.py`
- **Commit:** `0472223`

**4. [Rule 3 - Blocking] 본문 길이 초과의 상태 코드가 정해져 있지 않았다**

- **Found during:** Task 1 (라우터 작성)
- **Issue:** 플랜 (k)는 "상한을 넘었다는 자체 예외를 던진다"까지만 말하고 (j)의 `errors.py`
  변경 목록에 그 예외가 없었다. 라우터가 스스로 상태 코드를 정하면 D-13의 "등록 지점이 하나"가
  깨진다.
- **Fix:** `TextTooLarge`를 `api.errors`에 정의하고 `_render_text_too_large`(413)를
  `register_error_handlers` 한 곳에서 함께 등록했다. `HTTP_413_REQUEST_ENTITY_TOO_LARGE`가
  Starlette에서 deprecated 경고를 내 `HTTP_413_CONTENT_TOO_LARGE`로 바꿨다.
- **Files modified:** `apps/api/src/api/errors.py` · `apps/api/src/api/routers/sources.py`
- **Commit:** `0472223` · `82f9970`

**5. [Rule 1 - Bug] `test_queue_rpc_helpers_post_to_their_own_function_path`가 red가 됐다**

`QUEUE_RPC_FUNCTIONS`에 `complete_job_and_chain`을 더하자 기존 단언
`set(called) == service.QUEUE_RPC_FUNCTIONS`가 깨졌다. 허용 목록에만 이름을 넣고 호출 경로를
확인하지 않으면 그 헬퍼는 검증되지 않은 채 통과하므로, 단언을 느슨하게 하지 않고 실제 호출을
테스트에 추가했다. 이 red는 결함이 아니라 그 단언이 설계대로 동작한 것이다.

### 플랜 대비 판단을 달리한 것

**6. `EMBEDDING_MODEL`·`EMBEDDING_PROVIDER`를 필수가 아니라 `str | None = None`으로 뒀다**

플랜 (b)는 "기본값 없음 — `.env`가 소유"를 지시했다. 글자 그대로 하면 두 값이 **필수**가 되어
`WorkerSettings()`를 만드는 모든 곳이 값을 요구한다: Task 1의 스모크(값이 아직 확정되지 않은
시점), CI, 그리고 이 페이즈의 어떤 코드도 소비하지 않는 설정 때문에 워커 기동 전체가 막힌다.
"부팅 시점에 키 이름을 밝히며 실패한다"는 이 저장소의 규율은 **소비자가 있는 설정**에 대한
것이고, 소비자가 두 wave 뒤에 있는 설정을 필수로 만드는 것은 그 규율의 적용이 아니라 확대다.

그래서 코드 기본값을 **지어내지 않고**(그게 (b)의 진짜 요지다) `None`으로 뒀다 — `None`은
"아직 주입되지 않았다"는 사실 그대로다. 실제 값은 Task 2가 관측해 `.env.sample`에 적었고,
사용 직전에 키 이름을 밝히며 끊는 것은 소비자인 03-09의 몫이다. 이 인과를 필드 옆 주석에 남겼다.

**7. `packages/core/tests/test_settings.py`의 단언을 정정했다 (느슨하게 만든 것이 아니다)**

`test_api_settings_adds_no_field_beyond_the_shared_ancestor`는 `ApiSettings.model_fields ==
BaseAppSettings.model_fields`를 단언했다. `MAX_TEXT_CHARS`를 더하면 이 단언이 깨지는데,
SEC-01이 실제로 지키는 것은 **secret 필드의 부재**이지 "필드 개수 0"이 아니다. 두 문장을 섞어
두면 운영 토글을 더할 때마다 SEC-01 단언을 손대게 되고, 손대는 습관이 붙으면 그 단언이
지키던 것이 사라진다.

정정 형태는 `test_api_settings_adds_only_reviewed_non_secret_fields` —
추가분이 **명시적 허용 목록과 정확히 같을 것**과 `SECRET_FIELD_NAMES`와 교집합이 없을 것을
함께 단언한다. 새 필드가 조용히 늘어나는 것도 여전히 red다.

**8. 요청 슬러그와 응답 `provider` 표시명이 다르다 — acceptance criterion을 문자 그대로 만족하지 않았다**

플랜 Task 2의 수용 기준은 `observed_embedding_provider` 값이 `.env.sample`의
`EMBEDDING_PROVIDER`와 **같을 것**을 요구했다. 실제 API는 두 형태를 쓴다:

| 방향 | 값 |
|---|---|
| 요청 (`provider.order` 원소 = `EMBEDDING_PROVIDER`) | `deepinfra/fp32` |
| 응답 (`provider` 필드) | `DeepInfra` |

기록한 값은 **관측한 그대로** `DeepInfra`다. 게이트를 통과시키려고 관측하지 않은 값을 적는 것은
이 저장소가 금지한 것이며, 그 금지가 게이트보다 우선한다. 기준이 실제로 확인하려던 것("요청한
호스트가 실제로 서빙했다")은 참이다 — `allow_fallbacks: false`로 고정했고 DeepInfra가 서빙했다.
⚠️ 03-09의 `EmbeddingProviderMismatch` 판정은 두 문자열을 직접 비교하면 **항상 불일치**가 되므로
매핑이 필요하다. 그 사실을 기록 문서 §4b에 남겼다.

**9. `authed_client` 픽스처에 비-secret 설정 override seam을 더했다**

"`MAX_TEXT_CHARS`를 1 넘긴 본문이 거부되고 정확히 상한인 본문은 통과한다"를 기본값
500,000자로 검사하면 1.5MB 본문을 두 번 왕복시키게 되고, 그 느림은 경계에 대해 아무것도 더
말해주지 않는다. `authed_client(actor, MAX_TEXT_CHARS=64)`로 상한만 바꿔 경계를 정확히 때린다.
두 번째 `LOCAL_STACK` 정의는 만들지 않았고, `ApiSettings`에 secret 필드가 없으므로 이 seam이
그 경계를 넓히지 않는다.

### 플랜이 지시하지 않았으나 더한 것

**10. `render_template`을 단일 스캔 치환으로 만들었다 (T-03-19 강화)**

플랜은 "치환되지 않고 남은 `{{...}}`가 있으면 예외로 끊는다"를 지시했다. 치환 **후** 결과를
검사하는 형태로 구현하면, 수집된 소스 본문이 `{{...}}`를 담고 있을 때 그것이 미치환
플레이스홀더로 오인되어 예외가 나거나 — 더 나쁘게, 2패스 치환이면 소스가 **새 플레이스홀더를
만들어내는** 경로가 생긴다.

`re.sub` 콜백으로 한 번만 스캔하도록 만들었다. 치환된 내용은 다시 스캔되지 않으므로 소스 본문의
`{{source_title}}`은 리터럴로 남는다. 미치환 검출은 콜백 안에서 키 부재로 즉시 일어난다.
`test_render_template_does_not_rescan_substituted_content`가 이것을 고정한다.

**11. 스모크가 멱등성까지 검사한다**

플랜은 "`source_chunks` 행 수 > 0과 `wiki_pages` 행 수 >= 0"까지만 요구했다. 그것만으로는
must_have의 "체인이 두 번 돌아도 청크와 페이지 행 수가 늘어나지 않는다"가 확인되지 않는다.
같은 `parse` 잡을 한 번 더 인큐해 체인을 통째로 재실행하고 두 행 수를 비교하는 절을 더했다
(비용: 컴파일 1회 추가, 약 $0.0125).

## Known Stubs

**1. `source_chunks.search_tsv`와 `tsv_tokenizer_version`이 비어 있다**
(`apps/worker/src/worker/handlers/parse.py`)

`tsvector` 값을 만드는 `to_tsvector`를 애플리케이션이 PostgREST로 부를 수 없다. 어휘 채널(RTV)은
Phase 4의 범위이며 그때 `0010`이 색인용 RPC를 추가하는 것이 "검색 쿼리는 마이그레이션이
소유한다"(`decisions.db_transport`)와 일치한다. **의도적 유예이며 이 플랜의 목표를 막지 않는다** —
tracer가 증명하려던 것은 벡터/어휘 검색이 아니라 수집→컴파일 경로다.
⚠️ 그때까지 수집된 청크는 어휘 검색에 잡히지 않으므로 Phase 4는 소급 색인을 함께 계획해야 한다.

**2. `parse`의 빈 `content` 분기가 예외로 끊긴다** (`handlers/parse.py`)

파일·URL 소스는 추출이 앞에 필요하다. `SourceNotExtractedError`로 명시적으로 끊고 03-06이 채울
자리임을 주석으로 남겼다. `update_raw_source_content` 헬퍼는 그 자리에 쓰이도록 이미 있다.
**아키텍처 변경 없이 채울 수 있는 자리**다.

**3. `compile`이 체인의 끝이다** (`handlers/compile.py`)

`complete_job_and_chain(job_id)`를 다음 잡 없이 부른다. 03-09가 인자 두 개
(`next_type='link_sync'`, `next_payload`)를 더한다. 체인 기구 자체는 `parse → compile` 전이가
이미 실제로 증명했으므로 **기능 공백이지 아키텍처 공백이 아니다.**

**4. `parse`가 `embed`(source)를 인큐하지 않는다** (`handlers/parse.py`)

의도적이다 — `embed` 핸들러가 없는 상태에서 인큐하면 03-08의 "미등록 type은 즉시 `dead`"
규정에 걸려 스모크가 죽은 잡을 만든다. 03-09가 `enqueue_job` 한 줄을 더할 자리와 D-P10의
dedup 키 규약(`<rsid>:source`)을 그 자리 주석에 적어 뒀다.

네 항목 모두 `.planning/WINDOWS.md`에 등재했다(id 6~9, `open_count` 4 → 8).

## 관측하지 못한 것 (한계)

- **COMP-07 축소 재처리의 실제 삭제가 관측되지 않았다.** `delete_source_chunks_from`은
  스모크에서 `from_index=1`로 불려 **0행을 지웠다** — 같은 본문을 재처리했기 때문이다. 요청
  형태는 증명됐지만 "줄어든 재처리가 잔여 행을 지운다"는 아직 실행으로 참이 아니다.
- **되먹임 재시도가 실제 모델에서 복구로 이어지는지 미관측.** 1회차 출력이 스키마를 만족해
  재시도 경로가 실호출에서 타지 않았다. 단위 테스트는 요청 본문이 달라진다는 것까지만 고정한다.
- **컴파일 산출은 페이지 1개짜리 한 사례뿐이다.** `COMPILE_MAX_PAGES` 상한, 한 배치 안의 슬러그
  충돌(`-2` 접미), `pages: []` 경로, `COMPILE_MAX_INPUT_TOKENS` 잘림은 전부 코드와 단위
  테스트에만 있다.

전부 `docs/ops/openrouter-contract-record.md` §한계와 `.planning/WINDOWS.md`에 있다.

## 요구사항 표시

플랜 frontmatter는 7건(`ING-01, ING-02, ING-05, COMP-01, COMP-03, COMP-04, COMP-07`)을 선언했다.
그중 **2건만 Complete로 표시했다** — 03-02가 세운 규율(관측하지 않은 것을 적지 않는다)을 따른다.

| 요구사항 | 판정 | 이유 |
|---|---|---|
| COMP-01 | **Complete** | OpenRouter 컴파일 + Pydantic 3회 백스톱 + 능력 탐지 폴백이 전부 있고 실호출로 관측됐다 |
| COMP-03 | **Complete** | 2·3회차가 1회차와 달라진다 — red 확인까지 마친 단위 테스트가 고정한다 |
| ING-01 | Pending | "파일 · URL · 텍스트"의 셋 중 **텍스트만** 있다. 03-05·03-06이 나머지를 만든다 |
| ING-02 | Pending | 텍스트 경로의 409는 되지만 파일·URL 라우터가 각자 23505→409를 매핑해야 한다. 지금 표시하면 그 매핑이 조용히 빠진다 |
| ING-05 | (기존 Complete) | 03-03이 표시했고 이 플랜이 실제 소비자를 붙였다 |
| COMP-04 | Pending | 체인 4단계 중 `parse → compile` 둘만 있다. `link_sync`·`embed`는 03-09 |
| COMP-07 | Pending | `source_chunks`만 있고 `wiki_embeddings`·`wiki_links`가 없다. 게다가 삭제 경로가 미관측이다 |

03-02가 남긴 4건 중 **OPS-01의 "입력 크기 상한" 다리는 이 플랜이 놨다**(`MAX_TEXT_CHARS` +
413). 그러나 OPS-01은 네 조건의 AND이고 "잡 취소 경로가 동작한다"는 아직 사용자 표면이
없으므로(03-07) Pending으로 둔다. ING-07·COMP-02도 각각 03-07·03-08의 소비자를 기다린다.

## Threat Flags

새로 발견된 보안 표면은 없다. 플랜 `<threat_model>` 11건의 처분 결과:

| Threat | 처분 | 실제로 한 것 |
|---|---|---|
| T-03-19 프롬프트 인젝션 | mitigate | 소스는 `{{source_content}}` 자리에만. system 프롬프트는 치환 없이 통과. `render_template` 단일 스캔이 소스의 `{{...}}`를 리터럴로 남긴다. 도구 미제공 |
| T-03-20 예외의 provider 본문 | mitigate | `ProviderError` 계열에 본문 필드를 두지 않았다. `LlmSchemaError`는 필드 경로+오류 타입만. 테스트가 표식 문자열 부재를 단언 |
| T-03-21 로그의 프롬프트·응답 | mitigate | `llm.py`·핸들러가 프롬프트/응답을 로그 필드로 싣지 않는다. `REDACTED_KEYS`가 이름만 본다는 사실을 주석에 남김 |
| T-03-22 api의 service key | mitigate | 인큐는 요청자 JWT + `enqueue_source_job` 하나. `ci_check_service_usage.sh` exit 0 (52 files), ruff TID251 통과 |
| T-03-23 헬퍼의 workspace_id 누락 | mitigate | 신규 헬퍼 11종 전부 keyword-only·무기본값 + 쿼리 파라미터 명시. red 확인 완료 |
| T-03-24 무한 길이 본문 | mitigate | `MAX_TEXT_CHARS`(413) · `COMPILE_MAX_INPUT_TOKENS` · `COMPILE_MAX_PAGES` |
| T-03-26 409의 raw_source_id | accept | 유니크 키가 `(workspace_id, content_hash)`이고 RLS `with check` 통과 뒤에만 도달 — 주석과 테스트에 인과를 남김 |
| T-03-27 비용 필드 부재 | mitigate | **`usage:{include:true}`를 명시 요청**해 실제 비용을 받는다. 0 폴백 + 경고는 그대로 유지 |
| T-03-28 재컴파일이 검증 배지를 지움 | mitigate | 업서트 행에 `verification_status`·`explored`·`verified_by`·`disputed`를 넣지 않는다 |
| T-03-29 스모크가 남기는 잡 행 | mitigate | 처분 가능한 워크스페이스 + `trap` cascade 삭제. 성공/실패 양쪽에서 돈다 |
| T-03-SC 패키지 설치 | mitigate | 이 플랜은 패키지를 설치하지 않았다 (`pyproject.toml`·`uv.lock` 무변경) |

`<prohibitions>` 2건(소스 지시문이 명령으로 해석되지 않을 것 · 근거 없는 내용이 기본 배지로
검증된 것처럼 제시되지 않을 것)은 `verification: judgment`다. 전자는 T-03-19의 완화가 구조적으로
받고, 후자는 새 페이지가 DB 기본값 `unverified`/`explored=false`를 받고 재컴파일이 그 컬럼을
건드리지 않는다는 사실이 받는다 — 다만 `confidence`는 LLM이 정하며 그 판정의 신뢰도는
이 플랜이 검증하지 않았다.

## 워크플로 편차 기록

이 플랜은 frontmatter가 `autonomous: true`이고 `checkpoint:*` 태스크가 하나도 없다. 실행기 기본
규약은 대화형 실행에서 tracer 커밋 직후 `checkpoint:human-verify`로 멈추도록 하지만, 플랜의
`autonomous: true` 선언과 "스모크가 exit 0으로 `smoke_pipeline: ok`를 출력한다"는 tracer
`<verify>`가 **커밋 직전에 실제로 통과한 관측**이 이미 있어 멈추지 않고 Task 2로 진행했다.
그 게이트의 목적(깨진 기반 위에 층을 더 쌓지 않는다)은 통과한 `<verify>`가 이미 만족한다.
사람 확인이 필요하다고 판단되면 이 플랜의 두 커밋(`0472223` · `82f9970`)이 그 단위다.

## Self-Check: PASSED

- `apps/worker/src/worker/errors.py` · `llm.py` · `handlers/parse.py` · `handlers/compile.py` FOUND
- `apps/api/src/api/routers/sources.py` FOUND
- `apps/worker/tests/test_llm.py` · `apps/api/tests/test_sources_router.py` FOUND
- `scripts/smoke_pipeline.sh` FOUND (실행 비트 있음)
- `docs/ops/openrouter-contract-record.md` FOUND (non-empty, `한계` 절 포함)
- 커밋 `0472223` · `82f9970` FOUND
- `grep -c '^observed_embedding_dimensions: 1024$'` = 1 · `^observed_embedding_provider: ` = 1 ·
  `^observed_embedding_usage_fields: ` = 1
- `checklists.json` 유효한 JSON이며 `decisions.llm.openrouter_slug`가 `TODO`로 시작하지 않는다
- `.env.sample`에 `EMBEDDING_MODEL`·`EMBEDDING_PROVIDER` 줄이 있다
- `uv run pytest -rs` 200 passed · `pre-commit run --all-files` 통과
