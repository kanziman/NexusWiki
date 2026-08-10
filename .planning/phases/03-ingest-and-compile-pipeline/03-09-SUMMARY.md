---
phase: 03-ingest-and-compile-pipeline
plan: 09
subsystem: worker
tags: [openrouter, embeddings, wiki-links, idempotency, smoke]
requires:
  - "03-04 tracer pipeline and worker service client"
  - "03-06 extraction paths"
provides:
  - "parse → compile → link_sync → embed production chain"
  - "Fixed-provider source and wiki embeddings with reprocessing cost guard"
  - "Live OpenRouter smoke observations and cascade cleanup proof"
affects:
  - "03-08 enum/dead-letter validation"
  - "Phase 4 embedding retrieval"
actuals:
  tasks: 3
  commits: 4
tech-stack:
  added: []
  patterns:
    - "Current embedding_version rows are excluded before an OpenRouter request."
    - "The smoke injects embedding configuration only at invocation time."
key-files:
  created: []
  modified:
    - apps/worker/src/worker/db/service.py
    - apps/worker/src/worker/handlers/embed.py
    - apps/worker/tests/test_handlers.py
    - apps/worker/tests/test_service_client.py
    - scripts/smoke_pipeline.sh
    - docs/ops/openrouter-contract-record.md
key-decisions:
  - "OpenRouter response display name DeepInfra is compared to the requested deepinfra/fp32 host component."
  - "Wiki vectors at the active embedding_version are never resent during reprocessing."
requirements-completed: [COMP-04, COMP-05, COMP-06, COMP-07]
metrics:
  completed: 2026-08-10
status: complete
---

# Phase 3 Plan 09: 링크·양방향 임베딩 Summary

`parse → compile → link_sync → embed` 체인을 완성하고, source/wiki 양쪽 임베딩과 재처리 비용 0을 실제 OpenRouter 스모크로 확인했다.

## Accomplishments

- `link_sync`가 위키 링크·레드 링크를 동기화하고 `embed`가 source 및 wiki 청크를 고정 공급자로 임베딩한다.
- 현재 `embedding_version`의 wiki 행을 먼저 조회해 재처리에서 OpenRouter 호출과 usage event가 늘지 않게 했다.
- 스모크는 두 embed 잡, 1024차원, 단일 embedding version, 레드 링크, 행·비용 멱등성 및 workspace cascade 뒤 jobs 0행을 검사한다.

## Task Commits

1. **Task 1: 링크 동기화와 compile 체인** — `8e2a19d`
2. **Task 2a: source 임베딩** — `f3b24b0`
3. **Task 2b: wiki 임베딩·축소 처리** — `268e737`
4. **Task 3 및 실스모크 회귀 수정: 확장 스모크·문서·현재 version 비용 가드** — `519d5a5`

## Live Observation

- 승인된 일회성 환경: `baai/bge-m3` / `deepinfra/fp32`; `.env`에는 기록하지 않았다.
- 응답: `DeepInfra`, `BAAI/bge-m3`; source 76 tokens·1 micro-dollar, wiki 92 tokens·1 micro-dollar.
- source/wiki 모두 1024차원, wiki embedding version 1개, 재처리 후 embedding usage events 2개로 불변이었다.

## Verification

- `bash scripts/smoke_pipeline.sh` (일회성 임베딩 환경 주입) — 성공; `smoke_pipeline: ok`
- `uv run pytest -rs` — 309 passed
- `uv run ruff check apps packages` — 성공
- `bash scripts/ci_check_service_usage.sh` — 성공
- `uv run pre-commit run --all-files` — 성공

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] wiki 재처리가 이미 같은 version인 벡터를 다시 호출했다**
- **Found during:** Task 3 live smoke
- **Issue:** 재처리 후 embedding usage events가 `2 → 3`으로 늘었다.
- **Fix:** `list_wiki_embeddings()`로 현재 version 인덱스를 읽고, 누락 청크만 임베딩한다.
- **Verification:** 새 회귀 테스트와 최종 실스모크에서 이벤트 수·행 수가 모두 불변이었다.
- **Committed in:** `519d5a5`

**Total deviations:** 1 auto-fixed bug.

## Issues Encountered

PATH에 `pre-commit` 이진 파일이 없었으므로 프로젝트 도구 경로인 `uv run pre-commit run --all-files`를 사용했다.

## User Setup Required

None. 실스모크를 다시 실행할 때만 `EMBEDDING_MODEL`과 `EMBEDDING_PROVIDER`를 명시적으로 환경에 주입한다.

## Next Phase Readiness

03-08만 남았다. 이 플랜은 페이즈 완료 마킹이나 페이즈 검증을 수행하지 않았다.

---
*Phase: 03-ingest-and-compile-pipeline*
*Completed: 2026-08-10*
