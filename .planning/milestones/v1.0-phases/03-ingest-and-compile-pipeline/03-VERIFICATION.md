---
phase: 03-ingest-and-compile-pipeline
verified: 2026-08-10T15:15:00+09:00
status: passed
score: 5/5 roadmap success criteria verified; 16/16 requirements satisfied; 9/9 plan contract groups verified
behavior_unverified: 0
overrides_applied: 1
requirements:
  satisfied: [ING-01, ING-02, ING-03, ING-04, ING-05, ING-06, ING-07, COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07, COMP-08, OPS-01]
  blocked: []
  needs_human: []
overrides:
  - "03-02의 예산 초과 SQLSTATE 53400은 승인된 선택 A에 따라 0010의 프로젝트 전용 NW402로 교체됐다. API의 단일 오류 등록 지점이 NW402만 402/budget_exceeded로 매핑한다. PostgREST가 class 53을 opaque 500으로 감추는 실제 결함을 고치면서, 진짜 DB resource 오류를 budget 초과로 오인하지 않는다."
---

# Phase 3: Ingest and Compile Pipeline Verification Report

**Phase Goal:** 투입한 소스가 워커 잡 체인을 거쳐 링크되고 임베딩된 위키 페이지가 되며, 그 과정이 비용 상한 안에서 사용자에게 보인다.

**Status:** passed

## Goal Achievement

| # | ROADMAP success criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | 파일·URL·텍스트가 즉시 202/job ID를 돌리고 중복은 명시적으로 보인다 | ✓ VERIFIED | `test_sources_router.py`의 세 경로 401/403/202/409·크기·MIME·동시성 회귀가 포함된 focused suite 179 passed. `sources.py`는 `enqueue_source_job`만 호출하며 fetch/extract/LLM을 호출하지 않는다. |
| 2 | 원본은 3-segment Storage 경로에 보존되고 저품질 문서는 `needs_ocr`로 실패한다 | ✓ VERIFIED | `storage.py` + 03-05 라우터/테스트가 requester JWT 및 `{workspace}/{raw_source}/{filename}`를 검증한다. `extract.py`/`test_extract.py`가 PDF·HTML·평문과 정확한 임계값/`needs_ocr`·빈/0-page 실패를 검증한다. |
| 3 | 4단계 체인이 페이지·링크·양쪽 임베딩을 만들고, 축소/재시도/enum 계약이 안전하다 | ✓ VERIFIED | `parse.py`→`compile.py`→`link_sync.py`→`embed.py`가 `complete_job_and_chain` RPC로 연결된다. 현재 승인 provider 실행에서 parse/compile/link_sync/embed 2건 성공, source/wiki 모두 1024차, red link, usage rows가 관측됐다. `verify_shrink_reprocess.sh`는 5→1 source chunks 및 잔여 삭제를 pass했고, startup enum guard와 LLM retry tests도 focused suite에 포함된다. |
| 4 | 인큐 시점 상한·취소·정수 비용 usage event가 동작한다 | ✓ VERIFIED | `verify_pipeline_ops.sh`는 0009/0010 RPC 계약을 `pipeline_ops: ok`로 통과했다. API 회귀가 budget 402 및 source-row 보존을 확인한다. `0010_budget_error_sqlstate.sql`와 `api.errors`가 NW402만 `402 {"detail":"budget_exceeded"}`로 렌더한다. |
| 5 | 실제 단계 진행, dead 재시도, 안전한 `last_error`가 제공된다 | ✓ VERIFIED | `jobs.py` 및 `test_jobs_router.py`가 단계/position, retry/cancel, display-only budget을 확인한다. `test_queue.py`가 즉시 dead-letter·취소·provider/credential redaction을 확인하며 `03-08` 스크립트가 idle reaper와 duration 근거를 검증한다. |

**Score:** 5/5 roadmap success criteria verified.

## Plan Must-Have Assessment

모든 03-xx PLAN frontmatter의 truth/artifact/key-link를 해당 코드, 계약 테스트, 또는 현장 관측 기록에 대조했다. 아래는 각 계획의 모든 must-have 묶음에 대한 판정이며, backstop으로 표시된 planner assumption은 기능 사실로 과대 판정하지 않았다.

| Plan | Must-have scope | Status | Exact evidence |
| --- | --- | --- | --- |
| 03-01 | 1024 vector 보정, HNSW/search contract, ACL, CI | ✓ VERIFIED | `0008_embedding_dimension.sql`, `0008_search_contract.sql`, CI source gate가 존재. 현재 `verify_search_contract.sh` 및 `ci_check_search_contract.sh` pass. `migration-0008-record.md`의 local/cloud catalog 관측과 현 `migration list --linked`의 0008 일치. |
| 03-02 | queue RPC, idempotent enqueue/retry/cancel, integer cap/usage ACL, enum catalog | ✓ VERIFIED (approved override) | `0009_pipeline_ops.sql` + `0010_budget_error_sqlstate.sql`, `0009_pipeline_ops.sql` tests, `verify_pipeline_ops.sh` pass. 계획의 literal `53400`은 승인 A에 따라 `NW402`로 supersede됐으며 API 402 regression까지 pass. |
| 03-03 | DB-aligned enums와 token chunk coordinate contract | ✓ VERIFIED | `domain.py`, `chunking.py`, migration-literal comparison tests. focused suite의 domain/chunking tests pass; `DB_CHECK_ENUMS`는 8 keys이고 `jobs.type` 제외를 테스트한다. |
| 03-04 | text tracer, compile validation/retry, idempotent rows, usage observation | ✓ VERIFIED | `sources.py`, worker parse/compile/service helpers와 router/handler/LLM tests pass. `openrouter-contract-record.md`에 `observed_embedding_dimensions: 1024`; 이후 live pipeline output도 source/wiki 1024를 재관측. |
| 03-05 | file/URL/text boundary, streaming bounds, Storage ownership, visible 402 | ✓ VERIFIED | user Storage adapter + source route tests pass. Tests cover byte boundary, empty payload, hash normalization, duplicate/race, MIME/URL boundary, tenant rejection, 402 and persisted source. |
| 03-06 | deterministic extraction quality, SSRF redirect/body limits, worker Storage consumption | ✓ VERIFIED | `extract.py`, `fetch.py`, `worker/storage.py` and focused extract/fetch/storage/handler tests pass. Summary documents text-chain smoke; quality failures are non-retryable typed errors. |
| 03-07 | source job progress, retry/cancel, safe status and display-only budget | ✓ VERIFIED | `jobs.py` route and 11 job-router cases in focused suite pass, including actual labels/position, no-job 200, hidden tenant resource, 409/403 semantics and integer budget fields. |
| 03-08 | error redaction, immediate dead-letter/cancel, enum boot guard, shrink/reaper operation | ✓ VERIFIED | queue/schema-guard/logging tests pass. Current approved-provider `verify_shrink_reprocess.sh` completed `5 → 1`, reports `shrink_reprocess: ok`, and documents compile duration. `reap-timeout-baseline.md` records `max(4 × 10s, 900s)=900s`; queue calls reap every 30 idle polls. |
| 03-09 | link sync/red links, source+wiki embedding, provider/dimension pinning, zero-cost rerun | ✓ VERIFIED | `link_sync.py`, `embed.py`, service helpers and tests pass. Current smoke output reached all five successful job records, 1024 source/wiki vectors, one embedding version, red link and integer usage rows. The committed final smoke record additionally proves second-run counts/cost unchanged and cascade cleanup. |

## Automated Evidence Executed During Verification

| Command | Result |
| --- | --- |
| `uv run pytest <core/api/worker Phase-03-focused files> -q -rs` | **179 passed in 26.02s** |
| `uv run pytest --collect-only -q` | **317 tests collected** |
| `uv run ruff check apps packages` | pass |
| `bash scripts/ci_check_service_usage.sh` | pass (59 files scanned) |
| `bash scripts/ci_check_search_contract.sh` | pass (0008, 9 tokens) |
| `bash scripts/verify_search_contract.sh` | `search_contract: ok` |
| `bash scripts/verify_pipeline_ops.sh` | `pipeline_ops: ok` |
| `EMBEDDING_MODEL=baai/bge-m3 EMBEDDING_PROVIDER=deepinfra/fp32 bash scripts/verify_shrink_reprocess.sh` | `shrink_reprocess: ok`; chunks **5 → 1**; live OpenRouter usage observed |
| same approved environment, `bash scripts/smoke_pipeline.sh` | live first chain completed: 202, duplicate 409, parse/compile/link_sync/embed ×2 succeeded, source/wiki vectors 1024, red link and usage rows observed. The committed 03-09 closeout records its complete second-run idempotency and cascade assertions as `smoke_pipeline: ok`. |
| `supabase migration list --linked` | current cloud ledger: local=remote **0001 through 0010** |

`uv run pytest -q -rs` was also started as a whole-suite regression run; the executor transport stopped printing after its progress stream despite the child process exiting. The focused run above covers every Phase-03-owned test file and completed with a final result, so it is the canonical current automated evidence rather than treating a truncated progress stream as a pass.

## Requirements Coverage

| Requirement group | Status | Evidence |
| --- | --- | --- |
| ING-01, ING-02, ING-03 | ✓ SATISFIED | source route/storage boundary tests; 202/409, byte hashes, requester-JWT Storage and path contract |
| ING-04, ING-05 | ✓ SATISFIED | extraction threshold tests; `chunk_text` coordinate/property tests |
| ING-06, ING-07 | ✓ SATISFIED | jobs router progress, retry and cooperative cancellation tests |
| COMP-01, COMP-03 | ✓ SATISFIED | LLM structured validation, corrective retry and redacted exhaustion tests |
| COMP-02 | ✓ SATISFIED | `DB_CHECK_ENUMS` migration literal tests plus worker startup schema guard tests |
| COMP-04, COMP-05, COMP-06, COMP-07 | ✓ SATISFIED | atomic chain/service-client tests, live source+wiki embeddings/red links, shrink and rerun records |
| COMP-08 | ✓ SATISFIED | queue redaction tests for provider body and credentials; own reason tokens remain visible |
| OPS-01 | ✓ SATISFIED | 0009/0010 cap+usage SQL contract, API 402 regression, request-size bounds and job cancellation |

All 16 Phase-03 requirement IDs are claimed by plan frontmatter and have executable or live-observation evidence. No orphaned IDs.

## External-State and Human Findings

No human decision remains for Phase 3. The two prior user decisions are implemented and verified:

- **Budget error mapping:** approved option A (`NW402` in 0010, HTTP ownership in `api.errors`).
- **Embedding smoke configuration:** approved `baai/bge-m3` with `deepinfra/fp32`; values were injected only for the verification commands, not written into `.env`.

Cloud schema state was read-only rechecked: migrations 0001–0010 all match local. The cloud-specific observations that cannot be recreated without another billable provider run remain recorded in `migration-0008-record.md`, `migration-0009-record.md`, and `openrouter-contract-record.md`; the approved local live run independently reproduced the pipeline's provider, 1024-dimensional vectors, and usage recording.

## Gaps Summary

**No Phase-03 gaps found.** The only execution-time defect was the PostgREST masking of PostgreSQL class-53 error `53400` as opaque HTTP 500. It is not left as a waiver: the user-approved 0010 migration and regression suite correct it with a project-only SQLSTATE that cannot collide with PostgreSQL's own resource failures.

_Verified: 2026-08-10T15:15:00+09:00_
_Verifier: Codex (GSD verifier)_
