# Spec Conformance 리뷰 — retrieval-debug-viewer r2

- 판정: pass
- 대상: `git diff main...HEAD` (321d000 + 4166a6f, HEAD=4166a6fd3b0f63676de747d018d609feca20cb3c, 브랜치 `feat/retrieval-debug-viewer`)
- 일시: 2026-08-22T04:20:04Z

## r1 지적 항목 재검증

r1이 `needs_fix`로 지적한 항목은 단 하나: "A channel returns no results or fails" 시나리오에서 `RetrievalDebugViewer.tsx`가 존재하지 않는 `meta.reason`을 읽어 채널 실패 사유(`error_code`)가 절대 노출되지 않고, 테스트 픽스처도 실제 계약과 다른 필드(`reason`)를 주입해 거짓으로 통과하던 문제.

수정 커밋 4166a6f를 확인한 결과:

- `apps/dashboard/components/RetrievalDebugViewer.tsx:33` — `ChannelMeta.reason` → `ChannelMeta.error_code`로 타입 변경
- `apps/dashboard/components/RetrievalDebugViewer.tsx:404-405` — 렌더링 코드가 `meta.reason ?? ...`에서 `meta.error_code ?? ...`로 변경, 실패 시 `status: unknown` 폴백 대신 실제 오류 코드를 표시
- 백엔드 계약 재확인: `apps/api/src/api/services/retrieval.py:358-369` `_failed_meta`가 `"error_code": error_code` 키로 응답을 채움, `packages/core/src/nexuswiki_core/rrf.py:77` `ChannelMeta.error_code: str | None`도 동일 — 프런트가 읽는 필드명이 백엔드 응답 스키마와 정확히 일치함
- `apps/dashboard/tests/RetrievalDebugViewer.test.tsx:63` — 픽스처가 `reason: "rpc_unavailable"` 대신 `error_code: "rpc_unavailable"`을 주입하도록 수정, 실제 계약과 일치
- `apps/dashboard/tests/RetrievalDebugViewer.test.tsx:132` — `within(rawSection!).getByText("rpc_unavailable")` 어서션이 실제 DOM 렌더 결과에서 문자열을 찾아 통과함(픽스처 필드명이 잘못돼도 통과하던 이전 상태와 달리, 지금은 컴포넌트가 실제로 `meta.error_code`를 읽어야만 통과하는 구조)
- 실행 확인: `pnpm vitest run tests/RetrievalDebugViewer.test.tsx` → `PASS (5) FAIL (0)`

필드명 수정 외에 카드 렌더링 조건(`isUnavailable || hitIds.length === 0`, `RetrievalDebugViewer.tsx:396`)과 상태 라벨("채널을 사용할 수 없음" / "반환 결과 0건") 로직은 손대지 않아, "silently omitting" 금지 요건도 그대로 유지된다.

## 시나리오 판정 (델타 스펙 전체 재대조)

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Development-only retrieval debug route / Developer opens the debug route in a local dev server | 충족 | `apps/dashboard/app/w/[workspaceId]/debug/retrieval/layout.tsx:16-20` — r1 이후 무변경(`git diff --stat main...4166a6f`에 이 파일 없음). `NODE_ENV === "development"`면 추가 게이트 없이 `children` 렌더링 |
| Development-only retrieval debug route / A deployed environment receives a request for the debug route | 충족 | `layout.tsx:16-18` — `NODE_ENV !== "development"`면 `notFound()` 호출. 무변경 |
| Authenticated live-workspace retrieval query / Developer submits a query | 충족 | `RetrievalDebugViewer.tsx:187-194`(`apiFetch`로 요청자 세션만 사용) — 무변경. 테스트 `tests/RetrievalDebugViewer.test.tsx:91-109` |
| Per-channel evidence and fused ranking display / Developer reviews channel results and fused ranking | 충족 | `RetrievalDebugViewer.tsx:374-467`(4채널 카드), `totalContribution()`(77-82행)이 `evidence.contributions` 합산으로 파생 — 무변경. 테스트 `tests/RetrievalDebugViewer.test.tsx:136-150` |
| Per-channel evidence and fused ranking display / A channel returns no results or fails | 충족(수정 확인됨) | `RetrievalDebugViewer.tsx:33,404-405`가 백엔드 계약 필드 `error_code`를 읽어 실제 실패 사유를 노출. 백엔드 `apps/api/src/api/services/retrieval.py:358-369`, `packages/core/src/nexuswiki_core/rrf.py:77`와 필드명 일치. 테스트 `tests/RetrievalDebugViewer.test.tsx:63,132`가 실제 계약 필드로 픽스처를 구성하고 렌더된 DOM에서 값을 검증 |

## 조치가 필요한 항목

없음.

## 판정 근거

r1이 지적한 유일한 미충족 시나리오("A channel returns no results or fails")는 프런트엔드 타입·렌더링 코드와 테스트 픽스처를 백엔드 실제 응답 스키마(`error_code`)에 맞춰 수정함으로써 해소됐다. 수정은 필드명 정정 하나에 국한되어 있고, `git diff --stat main...4166a6f` 기준으로 이 change에서 변경된 파일은 r1 검증 시점과 동일(레이아웃 게이트, API 호출 경로, 융합 랭킹 파생 로직 등)하여 다른 4개 Scenario에 회귀가 없음을 확인했다. 테스트도 실제로 필드명이 맞아야만 통과하는 구조로 바뀌어 "거짓 통과" 문제도 해소됐다. 델타 스펙 5개 Scenario 전부 코드 경로와 테스트 증거로 충족이 확인되어 `pass`로 판정한다.
