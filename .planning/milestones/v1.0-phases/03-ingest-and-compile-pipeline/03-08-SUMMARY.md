---
phase: 03-ingest-and-compile-pipeline
plan: 08
subsystem: worker
tags: [queue, redaction, schema-contract, reaper, reprocessing]
requires:
  - "0009 queue RPCs and 03-09 pipeline chain"
provides:
  - "Sanitized provider errors and atomic dead-letter/cancel transitions"
  - "Startup enum-to-CHECK contract guard and periodic idle reaper"
  - "Live shrink-reprocess proof and measured reap timeout derivation"
requirements-completed: [COMP-02, COMP-07, COMP-08, OPS-01]
actuals:
  tasks: 3
  commits: 3
  completed: 2026-08-10
status: complete
---

# Phase 3 Plan 08: 운영 계약 마감 Summary

provider 본문과 자격증명이 `last_error`에 남지 않게 하고, 재시도 불가 실패·취소·스키마 불일치를 명시적 큐 전이 또는 기동 실패로 만들었다. 축소 재처리와 compile 지속시간도 실제 로컬 스택에서 관측했다.

## Task Commits

1. Queue failure handling — `e831070`
2. Startup schema contract guard and worker key cleanup — `e9e3494`
3. Idle reaper regression coverage — `ef3d0cc`
4. Task 3 live verification, duration instrumentation, and timeout record — this closeout commit

## Live observations

- 승인 환경 `baai/bge-m3` / `deepinfra/fp32`를 명령 실행 때만 주입했다.
- 축소 재처리: source chunks `5 → 1`, parse가 잔여 4행을 삭제; 각 wiki embedding의 `chunk_index` 연속성과 cascade 뒤 jobs `0`을 확인했다.
- compile 성공 2개 중 최대 `9,125.154 ms`(올림 10초). `max(4 × 10초, 900초)`에 따라 `REAP_TIMEOUT_SECONDS=900`을 유지했다.
- 마지막 pipeline smoke 비용: DeepInfra 임베딩 `1 + 1` micro-dollar, Anthropic compile `12,549` micro-dollar.

## Verification

- `bash scripts/verify_shrink_reprocess.sh` — 성공
- `bash scripts/smoke_pipeline.sh` — 성공
- `uv run pytest -q` — 317 collected, passed
- `uv run ruff check apps packages` · queue/search/pipeline SQL checks · `uv run pre-commit run --all-files` — 성공

## Notes

종료 RPC는 `locked_at`을 비우므로 terminal DB 행으로 claim→종료를 사후 계산할 수 없다. 워커가 monotonic handler duration을 구조화 로그로 남기고, shrink 스크립트가 그 값을 읽어 문서화했다.
