---
status: complete
phase: 04-hybrid-retrieval-and-fusion
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md]
started: 2026-08-11T00:00:00Z
updated: 2026-08-11T12:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: 로컬 스택 리셋이 `0001`~`0011`을 전부 적용하고 오류 없이 끝난다. 리셋 직후 PostgREST 응답, 마이그레이션 원장에 `0011`이 정확히 한 번.
result: pass

### 2. 검색 계약 스크립트가 실제로 통과한다
expected: `scripts/verify_retrieval_contract.sh`가 `retrieval_contract: ok`를 출력하고 exit 0. (04-02 후반·04-03·04-04 세 세션 연속 Docker 부재로 미실행 상태였다 — 이번이 첫 실행)
result: pass

### 3. 인증된 검색 왕복
expected: 유효한 사용자 JWT로 `POST /workspaces/{id}/retrieval`에 질의를 보내면 200과 함께 `evidence[]` + `meta`가 온다. 각 evidence에 `kind`·`document_id`·`channels`·`contributions`가 있다.
result: pass

### 4. Phase 5 경계가 지켜진다
expected: 검색 응답에 answer·citation·streaming 필드가 **없다**. 증거와 안전한 관측 메타만 나온다 — 답변 생성과 이중 Citation은 Phase 5의 것이다.
result: pass

### 5. 그래프가 기본으로 꺼져 있다
expected: 정책 기본값(`graph_enabled=False`)으로 호출하면 그래프 2차 웨이브가 돌지 않고, 응답 meta가 그것을 드러낸다. 그래프 채널 기여도가 붙은 증거가 없다.
result: pass

### 6. query-embedding 경계
expected: API 설정에 `OPENROUTER_API_KEY`가 **없고**, 워커 리스너에 public 라우트가 없다. `scripts/ci_check_query_embedding_boundary.sh`가 통과한다.
result: pass

### 7. [D3] 정책 변경 증거 게이트가 실제로 집행될 것인가
expected: `docs/ops/retrieval-policy-change-log.md`의 절차(POLICY_VERSION 상승 + 동일 조건 before/after 쌍 + 리뷰어 승인)가 앞으로 실제로 지켜질 만한 형태인지 사람이 판정한다. 절차 문서는 실행이 아니라 합의다.
result: pass

### 8. [D4] strict/relaxed 비교 기록 — 미충족을 확인
expected: 이 항목은 **충족되지 않았다.** 비교 실행 자체가 존재하지 않는다(프로덕션 유사 규모가 Phase 4 범위 밖). `docs/ops/hnsw-order-benchmark.md`가 "측정하지 않음"으로 정직하게 적혀 있고 WINDOWS #10·STATE 블로커로 Phase 7에 이월된 것이 받아들일 만한 처리인지 판정한다.
result: pass
note: 미충족 자체는 유지된다 — 사용자가 승인한 것은 "미충족을 미충족으로 남기고 Phase 7로 이월한 처리"이지 수용기준 충족이 아니다. RTV-04는 Pending으로 남는다.

### 9. [D5] graph off/on 비교 — 미실행을 확인
expected: off/on 비교는 실행되지 않았다(러너에 토글 없음, 골든 그래프 시나리오 5개뿐). 기본값 off 유지는 RTV-07이 지시하는 상태라 근거가 필요 없다는 판단이 받아들일 만한지 확인한다.
result: pass
note: 비교 미실행은 유지된다 — RTV-07은 Pending으로 남고, 그래프 승격 판단에는 여전히 별도 근거가 필요하다.

### 10. [D1] 고정 대표 코퍼스와 다국어 골든 세트 (36문항: ko 10 / en 17 / mixed 9)
expected: 고정 대표 코퍼스와 30–50 다국어 evidence-label 골든 세트
result: pass
source: automated
coverage_id: D1

### 11. [D2] 재현 가능 벤치마크 CLI (해시/버전/정책 불일치에 fail-closed)
expected: 해시/버전/정책 불일치에 fail-closed 하고 전 스탬프를 남기는 재현 가능 벤치마크 CLI
result: pass
source: automated
coverage_id: D2

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — 이 세션은 코드 결함을 하나도 찾지 못했다]

## 이 UAT가 닫지 않는 것

UAT 통과가 아래를 충족으로 바꾸지 않는다. Test 8·9의 `pass`는 **"미충족을 정직하게
미충족으로 남긴 처리"에 대한 승인**이지 수용기준 충족이 아니다.

| 항목 | 상태 | 이월처 |
|---|---|---|
| RTV-04 — strict/relaxed 비교 기록 | Pending (비교 미실행) | WINDOWS #10 · STATE 블로커 · Phase 7 OPS |
| RTV-07 — graph off/on 비교 | Pending (비교 미실행, 기본값 off는 안전 상태로 유지) | 같음 |
| 04-04 Task 3 수용기준 #1 | 미충족 | 04-04-SUMMARY.md §미충족 수용 기준 |
