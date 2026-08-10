---
phase: 03-ingest-and-compile-pipeline
plan: 06
subsystem: worker-core
tags: [extraction, pdf, html, ssrf, storage, ingestion]
requires:
  - "03-04 parse→compile tracer and ServiceDb helpers"
  - "03-05 source Storage path ownership and enqueue boundaries"
provides:
  - "Pure PDF, HTML, plain-text extraction with deterministic quality gates"
  - "SSRF-guarded redirect-aware URL fetching and service-role Storage download"
  - "File and URL parse branches that update extracted raw-source content"
affects:
  - "03-08 non-retryable dead-letter routing"
  - "03-09 source embedding chain"
actuals:
  tokens: 22000
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns:
    - "Byte extraction stays network-free; fetch and Storage are explicit worker boundaries."
    - "Service-role Storage consumers validate the workspace path segment before download."
key-files:
  created:
    - packages/core/src/nexuswiki_core/extract.py
    - apps/worker/src/worker/fetch.py
    - apps/worker/src/worker/storage.py
  modified:
    - apps/worker/src/worker/handlers/parse.py
    - apps/worker/src/worker/errors.py
    - apps/worker/src/worker/settings.py
key-decisions:
  - "Extraction quality counts normalized non-whitespace code points and compares page density with integer multiplication."
  - "URL fetches manually follow at most a configured number of redirects, revalidating every target."
  - "Storage paths are consumed, not reconstructed; parse verifies the first segment against the job workspace."
requirements-completed: [ING-03, ING-04, ING-05]
coverage:
  - id: D1
    description: "PDF, HTML, plain-text extraction and boundary quality failures."
    requirement: ING-04
    verification:
      - kind: unit
        ref: "uv run pytest packages/core/tests/test_extract.py -q"
        status: pass
    human_judgment: false
  - id: D2
    description: "SSRF guards, redirect revalidation, capped response bodies, and service-role Storage path consumption."
    requirement: ING-03
    verification:
      - kind: unit
        ref: "uv run pytest apps/worker/tests/test_fetch.py apps/worker/tests/test_worker_storage.py -q"
        status: pass
    human_judgment: false
  - id: D3
    description: "File and URL parse branches extract content before retaining the existing chunk and compile chain."
    requirement: ING-04
    verification:
      - kind: integration
        ref: "uv run pytest apps/worker/tests -q"
        status: pass
      - kind: integration
        ref: "bash scripts/smoke_pipeline.sh"
        status: pass
    human_judgment: false
metrics:
  duration: "1h"
  completed: 2026-08-10
status: complete
---

# Phase 3 Plan 06: 원본 추출·SSRF·Storage 소비 Summary

PDF·HTML·평문 원본을 품질 게이트로 검증해 추출하고, URL과 Storage 원본을 테넌트·SSRF 경계 안에서 `parse` 파이프라인으로 연결했다.

## Accomplishments

- `pypdf`와 표준 HTML 파서로 네트워크 없는 바이트 추출을 만들고, 빈·저밀도 문서를 `needs_ocr` 등의 명시적 사유로 차단했다.
- URL 경로에 공개 주소 검사, 홉별 리다이렉트 재검사, MIME·본문 크기 상한을 적용했다.
- service-role Storage 다운로드가 업로드 경로를 재조립하지 않고, `parse`가 작업 워크스페이스와 첫 경로 세그먼트를 대조하도록 했다.
- 파일·URL 추출 후 기존 청킹과 compile 체인이 이어짐을 회귀 테스트와 로컬 스모크로 확인했다.

## Task Commits

1. **Task 1: `extract.py` — 바이트 → 평문과 품질 게이트** — `338e12c`
2. **Task 2: SSRF 가드 페치와 `service_role` Storage 다운로드** — `9c21057`
3. **Task 3: `parse` 핸들러를 파일·URL로 확장** — `3c33ae4`

## Verification

- `uv run pytest packages/core/tests/test_extract.py -q` — 13 passed
- `uv run pytest apps/worker/tests/test_fetch.py apps/worker/tests/test_worker_storage.py -q` — 15 passed
- `uv run pytest -rs` — 295 passed
- `uv run ruff check apps packages` · `uv run pre-commit run --all-files` — 성공
- `bash scripts/smoke_pipeline.sh` — 텍스트 경로 parse→compile 체인 성공

## Decisions Made

- 유효 문자는 `normalize()` 뒤 공백이 아닌 코드 포인트이며, 페이지 밀도는 나눗셈 없이 정수 곱셈으로 판정한다.
- DNS가 여러 주소를 돌려주면 하나라도 비공개 대역일 때 URL을 거부하고, 리다이렉트도 자동으로 따르지 않는다.
- `storage_path` 생성은 03-05 업로드 경로의 단일 책임으로 두고 워커는 해당 값을 그대로 소비한다.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

루트 셸에 `pre-commit` 실행 파일이 없었으나 프로젝트의 고정 dev 도구 경로인 `uv run pre-commit run --all-files`로 동일 훅을 실행해 통과했다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

03-08은 `NON_RETRYABLE_ERRORS`를 큐의 즉시 dead-letter 판정에 배선할 수 있고, 03-09는 추출된 파일·URL 원문에서 source 임베딩 체인을 추가할 수 있다.
