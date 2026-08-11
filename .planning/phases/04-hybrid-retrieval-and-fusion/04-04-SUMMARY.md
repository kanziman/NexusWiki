---
phase: 04-hybrid-retrieval-and-fusion
plan: 04
subsystem: testing
tags: [retrieval, benchmark, golden-set, pgvector, hnsw, rrf, governance]

requires:
  - phase: 04-hybrid-retrieval-and-fusion
    provides: 04-02 검색 RPC 계약(0011)과 HNSW GUC 고정
  - phase: 04-hybrid-retrieval-and-fusion
    provides: 04-03 5채널 오케스트레이션과 정책 계층 식별자
provides:
  - 고정 대표 코퍼스(12 chunks / 12 pages / 8 links)와 다국어 골든 36문항
  - 해시 게이트로 fail-closed 하는 재현 가능 벤치마크 CLI
  - 순서 모드·그래프 기본값 결정 기록 (측정 아님을 명시)
  - 정책 변경 증거 게이트 절차와 변경 이력 표
affects: [phase-05-answer-and-citation, phase-07-ops]

actuals:
  tokens: 4200
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "고정 입력 해시 + POLICY_VERSION + git SHA 스탬프로 벤치마크 비교 가능성을 강제"
    - "정책 변경은 코드 리뷰가 아니라 before/after 증거 게이트를 통과"

key-files:
  created:
    - packages/core/tests/fixtures/retrieval/representative_corpus.v1.json
    - packages/core/tests/fixtures/retrieval/golden_queries.v1.json
    - packages/core/tests/test_retrieval_golden.py
    - scripts/benchmark_retrieval.py
    - docs/ops/hnsw-order-benchmark.md
    - docs/ops/retrieval-policy-change-log.md
  modified:
    - .planning/WINDOWS.md
    - .planning/STATE.md

key-decisions:
  - "순서 모드 strict_order 유지 — 측정이 아니라 `.claude/CLAUDE.md:21` 제약과 이미 배포된 `0011:76,147`에 따른 유지"
  - "그래프 기본값 off 유지 — RTV-07이 요구하는 안전 기본값 상태 그 자체이며 승격 근거는 없음"
  - "12/12/8행 코퍼스에서 strict/relaxed 비교를 돌리지 않음 — 플래너가 HNSW를 고르지 않아 T-04-12(오도하는 튜닝)가 됨"
  - "정책 변경 게이트: POLICY_VERSION 상승 + 동일 조건 before/after 레코드 쌍 + 리뷰어 승인"

patterns-established:
  - "결정 기록이 근거 부재도 명시한다: `order_mode: not_measured_fixture_adapter`를 문서가 덮지 않음"
  - "미충족 수용 기준은 SUMMARY·WINDOWS·STATE 세 곳에 동일하게 남긴다"

requirements-completed: [RTV-06]

coverage:
  - id: D1
    description: "고정 대표 코퍼스와 30–50 다국어 evidence-label 골든 세트 (36문항: ko 10 / en 17 / mixed 9)"
    requirement: "RTV-06"
    verification:
      - kind: unit
        ref: "uv run pytest -q packages/core/tests/test_retrieval_golden.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "해시/버전/정책 불일치에 fail-closed 하고 전 스탬프를 남기는 재현 가능 벤치마크 CLI"
    requirement: "RTV-06"
    verification:
      - kind: integration
        ref: "uv run python scripts/benchmark_retrieval.py --verify (exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "정책 변경 증거 게이트 — POLICY_VERSION 상승 + 동일 조건 before/after 쌍 + 리뷰어 승인"
    requirement: "RTV-04"
    verification:
      - kind: manual_procedural
        ref: "docs/ops/retrieval-policy-change-log.md §필수 요건 세 가지 · §거부 조건"
        status: pass
    human_judgment: true
    rationale: "절차 문서는 실행이 아니라 합의다 — 리뷰어가 게이트를 실제로 집행할지는 사람이 판정한다"
  - id: D4
    description: "순서 모드 strict/relaxed 비교 기록 (동일 해시 위 raw run 참조 포함)"
    requirement: "RTV-04"
    verification: []
    human_judgment: true
    rationale: "미충족. 비교 실행 자체가 존재하지 않는다 — 프로덕션 유사 규모 환경이 Phase 4 범위 밖이다. WINDOWS #10 · STATE 블로커 참조"
  - id: D5
    description: "그래프 off/on 비교와 기본값 결정"
    requirement: "RTV-07"
    verification:
      - kind: manual_procedural
        ref: "docs/ops/hnsw-order-benchmark.md §결정 — 기본값 off 유지, 승격 없음"
        status: pass
    human_judgment: true
    rationale: "off/on 비교는 실행되지 않았다. 러너에 그래프 토글이 없고 골든 그래프 시나리오가 5개(g24–g28)뿐이다. 기본값 off 유지는 RTV-07이 지시하는 상태이므로 근거를 요구하지 않으나, 승격 판단은 사람이 별도 근거로 해야 한다"

duration: 12min
completed: 2026-08-11
status: complete
---

# Phase 4 Plan 04: 재현 가능한 검색 품질 기준선 Summary

**해시로 고정된 12/12/8 코퍼스와 다국어 골든 36문항 위에서 fail-closed 하는 벤치마크 CLI, 그리고 "측정하지 않았음"을 덮지 않는 순서 모드·그래프 결정 기록과 정책 변경 증거 게이트**

## Performance

- **Duration:** 약 12분 (연속 실행 세션 기준)
- **Tasks:** 3
- **Files modified:** 6 created

## Accomplishments

- 고정 대표 코퍼스(`source_chunks` 12 / `wiki_pages` 12 / `wiki_links` 8)와 evidence-label 골든 36문항(ko 10 · en 17 · mixed 9)을 sha256으로 핀 고정
- `scripts/benchmark_retrieval.py --verify`가 코퍼스·골든·정책 해시 불일치에 종료 코드 2로 거부하고, `POLICY_VERSION`·양쪽 sha256·git SHA·요청/반환 한계·순서 모드·그래프 설정을 전부 스탬프
- `docs/ops/hnsw-order-benchmark.md` — `strict_order`와 graph off를 **유지**하되 그 근거가 제약·안전 기본값이지 측정이 아님을 명시. 비교를 돌리지 않은 이유와 변경을 정당화할 정확한 실험 조건을 §한계에 기록
- `docs/ops/retrieval-policy-change-log.md` — 가중치·`k`·한계값·순서 모드·그래프 기본값 변경에 `POLICY_VERSION` 상승 + 동일 조건 before/after 레코드 쌍 + 리뷰어 승인을 요구하는 게이트와 초기 기준선 행

## Task Commits

1. **Task 1: 고정 대표 코퍼스와 다국어 골든 세트** — `bac5913` (test)
2. **Task 2: 벤치마크 러너와 fail-closed 평가 계약** — `1dd780a` (feat)
3. **Task 3: 순서 모드·그래프 결정 기록과 정책 변경 절차** — `be67bae` (docs)

## Files Created/Modified

- `packages/core/tests/fixtures/retrieval/representative_corpus.v1.json` — 출처가 기록된 버전 고정 코퍼스
- `packages/core/tests/fixtures/retrieval/golden_queries.v1.json` — 36문항, 필수 근거·허용 대안·최대 순위 라벨
- `packages/core/tests/test_retrieval_golden.py` — 스키마·해시·통과 술어 검증
- `scripts/benchmark_retrieval.py` — `--verify` 재현 가능 CLI, 기존 레코드 덮어쓰기 거부
- `docs/ops/hnsw-order-benchmark.md` — 순서 모드·그래프 결정 기록 (근거 부재 기록)
- `docs/ops/retrieval-policy-change-log.md` — 정책 변경 증거 게이트와 변경 이력 표

## Decisions Made

- **`strict_order` 유지.** 채택을 검토할 "변경"이 애초에 없다 — `.claude/CLAUDE.md:21`·`:300`의 상시 제약이고 `supabase/migrations/0011_retrieval.sql:76`·`:147`에 하드코딩되어 이미 원격에 적용됐다. RTV-04가 금지하는 것은 비교 불가능한 실행으로부터 **변경을 채택**하는 것이지, 배포된 안전 기본값을 유지하는 것이 아니다.
- **그래프 기본값 off 유지.** `retrieval_policy.py:38`이 이미 `graph_enabled = False`다. RTV-07이 금지하는 것은 근거 없는 승격이며, off 유지는 그 금지가 지시하는 상태 그 자체다.
- **비교 실행을 하지 않기로 함.** 12/12/8행에서는 플래너가 HNSW 인덱스를 고르지 않는다 — Phase 2가 btree+sort 233 대 HNSW 349,657로 정확히 관측했다. 그 규모의 strict/relaxed 수치는 다른 플랜을 잰 잡음이면서 기록에 남는 순간 근거처럼 보인다. 이것이 이 플랜이 막으려고 존재하는 T-04-12다.
- **환경 조달은 Phase 7 OPS.** HNSW가 관여하려면 10⁴–10⁵ 청크가 필요하고, 그 임베딩 비용은 남은 OpenRouter 예산(약 $4.95)과 Railway Hobby $5/mo에서 나온다. Phase 2 선례상 클라우드 프로브 데이터는 사실상 영구다(`jobs`에 어느 롤에도 DELETE 없음).

## Deviations from Plan

Task 3의 `<action>`은 strict/relaxed와 graph off/on 두 비교를 실행하도록 지시했다. 실행하지 않았다. 위 §Decisions Made의 사유로 사람이 체크포인트에서 "변경 채택 없음"으로 종결했고, 결정 기록·정책 변경 절차만 산출했다. 정책 기본값과 `0011_retrieval.sql`은 한 줄도 바꾸지 않았다.

## 미충족 수용 기준

**Task 3 수용 기준 #1 — 미충족.**

> "Decision record compares strict and relaxed on identical corpus/golden/policy hashes and includes raw run references."

동일 해시 위 strict/relaxed 비교 기록이 **존재하지 않는다.** `docs/ops/hnsw-order-benchmark.md`는 비교 결과가 아니라 비교 부재의 기록이다. 지연·재현율·run ID를 하나도 지어내지 않았고, 러너 레코드의 `order_mode`는 `not_measured_fixture_adapter` 그대로다.

Task 3 수용 기준 #2는 부분 충족 — 기본값이 off로 남는다는 것은 명시했으나 off/on 비교 자체는 없다. 기준 #3(정책 변경 게이트)은 충족.

**요구사항 표기:**

- `RTV-06` — **완료.** 골든 세트와 재현 가능 러너가 자동 검증으로 증명된다.
- `RTV-04` — **미완료로 남긴다.** 절차 게이트(D3)는 섰지만 순서 모드 비교 근거(D4)가 없다. 이 플랜이 만족시키지 못한 요구사항을 완료로 표시하지 않는다.
- `RTV-07` — **미완료로 남긴다.** 안전 기본값은 유지되지만 요구된 off/on 기록 증거가 없다.

**이월:** `.planning/WINDOWS.md` #10 (`unrun-verify`, phase 04) · `.planning/STATE.md` Blockers/Concerns 말미. 대상은 Phase 7 OPS.

## Issues Encountered

Task 3의 `<precondition>`("Local Supabase corpus is populated … production-like hardware details are available")이 충족되지 않아 체크포인트로 중단됐다. 사람이 "변경 채택 없음"으로 종결했고, 환경 조달 대신 근거 부재를 정확히 기록하는 방향으로 마무리했다.

## Verification

- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q packages/core/tests/test_retrieval_golden.py` — `4 passed` (exit 0)
- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run python scripts/benchmark_retrieval.py --verify` — exit 0, `strict_query_pass_rate 1.0` / `recall_at_k 1.0`, `order_mode: not_measured_fixture_adapter`
- `scripts/verify_retrieval_contract.sh` — 미실행. 로컬 Docker 스택이 이 세션에서 기동돼 있지 않다(04-03과 동일 사유).

## User Setup Required

없음.

## Next Phase Readiness

- Phase 5(답변·이중 인용)는 고정 골든 세트를 회귀 기준선으로 그대로 쓸 수 있다.
- Phase 7 OPS가 받아야 할 것: 10⁴–10⁵ 규모 코퍼스에서의 strict/relaxed 비교, 그리고 `scripts/benchmark_retrieval.py`의 graph off/on 토글 추가. 언더필과 플랜 형태는 합성 1024차원 벡터로 로컬에서 예산 없이 선행 관측할 수 있다 — 프로덕션 하드웨어를 진짜로 요구하는 것은 지연 항목 하나뿐이다.

## Self-Check: PASSED

- `docs/ops/hnsw-order-benchmark.md` — 존재
- `docs/ops/retrieval-policy-change-log.md` — 존재
- 커밋 `bac5913` · `1dd780a` · `be67bae` — 전부 `git log`에서 확인

---
*Phase: 04-hybrid-retrieval-and-fusion*
*Completed: 2026-08-11*
