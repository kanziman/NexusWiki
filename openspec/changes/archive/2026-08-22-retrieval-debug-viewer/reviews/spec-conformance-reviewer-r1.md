# Spec Conformance 리뷰 — retrieval-debug-viewer r1

- 판정: needs_fix
- 대상: `git diff main...HEAD` (321d000035c4f434e54987a98e6217bbb8479c96)
- 일시: 2026-08-22T04:16:18Z

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Development-only retrieval debug route / Developer opens the debug route in a local dev server | 충족 | `apps/dashboard/app/w/[workspaceId]/debug/retrieval/layout.tsx:16-20` — `NODE_ENV === "development"`면 `children`을 그대로 렌더링. `/w/[workspaceId]/layout.tsx`가 이미 워크스페이스 인증(RLS 멤버십)을 처리하므로 이 layout은 추가 게이트를 얹지 않음. 자동 테스트 없음(수동 확인은 tasks.md 4.3) |
| Development-only retrieval debug route / A deployed environment receives a request for the debug route | 충족(자동 테스트 없음) | `layout.tsx:16-18` — `NODE_ENV !== "development"`면 `notFound()` 호출, `middleware.ts`의 matcher(`/w/:path*`)와 무관하게 layout 레벨에서 막음(요구사항의 "independent of middleware routing configuration" 충족). 다만 같은 패턴을 쓰는 `apps/preview/layout.tsx`는 `apps/dashboard/tests/preview-layout.test.tsx`로 dev/prod 분기를 자동 검증하는 반면, 이 change는 동등한 자동 테스트가 없다 — tasks.md 4.3은 수동 확인(`pnpm build && pnpm start`)만 요구하므로 task 완료 처리 자체는 스펙 위반이 아니나, 회귀에 취약하다 |
| Authenticated live-workspace retrieval query / Developer submits a query | 충족 | `RetrievalDebugViewer.tsx:187-194`에서 `apiFetch<RetrievalResponse>(/workspaces/{workspaceId}/retrieval, {method:"POST", body:{query, requested_k}})` 호출. `apiFetch`(`apps/dashboard/lib/api-client.ts:52-56`)는 `createClient().auth.getSession()`으로 얻은 요청자 세션 토큰만 사용, service_role 미사용. 백엔드 `apps/api/src/api/routers/retrieval.py:44-51,54-77`도 `_user_db`로 요청자 JWT만 사용해 `RetrievalService.retrieve`를 호출 — RLS 우회 없음. 테스트 `tests/RetrievalDebugViewer.test.tsx:91-109` |
| Per-channel evidence and fused ranking display / Developer reviews channel results and fused ranking | 충족 | 채널별 카드: `RetrievalDebugViewer.tsx:374-467`(4채널을 `RETRIEVAL_CHANNELS` 고정 순회, `meta.<channel>.raw_hit_ids` 기반 원시 랭킹). 융합 표: `RetrievalDebugViewer.tsx:470-531`, 정렬 키는 `totalContribution()`(77-82행)이 `evidence.contributions` 값을 합산해 파생 — 응답의 사전 계산 총점을 가정하지 않음(스펙의 "MUST derive... rather than assuming a precomputed total" 충족, 백엔드 `retrieval.py` `RetrievalResponse`에도 총점 필드 없음 확인). 테스트 `tests/RetrievalDebugViewer.test.tsx:136-150` |
| Per-channel evidence and fused ranking display / A channel returns no results or fails | 부분 충족(결함 있음) | `layout` 카드는 `meta.status !== "ok"` 이거나 `hitIds.length === 0`일 때 카드를 숨기지 않고 상태 블록을 렌더링(`RetrievalDebugViewer.tsx:382,396-406`) — "silently omitting" 금지 자체는 지켜짐. 다만 실패 사유 표시에 쓰는 `meta.reason`(`RetrievalDebugViewer.tsx:404`, 타입은 34행 `ChannelMeta.reason`)은 실제 백엔드 응답에 존재하지 않는 필드다 — 백엔드는 `error_code`를 보낸다(`apps/api/src/api/services/retrieval.py:358-369` `_failed_meta`가 `"error_code": error_code`만 채우고 `reason` 키를 쓰지 않음; `packages/core/src/nexuswiki_core/rrf.py:72-77` `ChannelMeta`도 필드명이 `error_code`). 실제 운영 응답에서는 `meta.reason`이 항상 `undefined`가 되어 폴백인 `status: failed` 같은 일반 텍스트만 노출되고, `rpc_unavailable` 같은 실제 원인은 화면에 절대 나타나지 않는다. 테스트(`tests/RetrievalDebugViewer.test.tsx:59-64,132`)는 픽스처에 실제 계약에 없는 `reason: "rpc_unavailable"` 필드를 직접 주입해 통과하므로, 실제 API 계약과 어긋난 채로 "검증됨"처럼 보인다 |

## 조치가 필요한 항목

1. **채널 실패 사유 필드명 불일치(`meta.reason` vs 백엔드 `error_code`)** — `RetrievalDebugViewer.tsx`의 `ChannelMeta` 타입과 렌더링 코드(34, 404행)가 `reason`을 읽지만, 백엔드(`apps/api/src/api/services/retrieval.py:358-369`, `packages/core/src/nexuswiki_core/rrf.py:72-77`)는 `error_code`를 보낸다. 근거 Scenario: "A channel returns no results or fails" — 카드 자체는 숨기지 않아 스펙 문구는 지켜지지만, design.md가 이 화면의 존재 이유로 든 "왜 이 채널이 기여하지 않았는가"를 실제로는 보여주지 못하고 `status: failed`라는 일반 텍스트로만 폴백된다. 제안: `ChannelMeta.reason`을 `error_code`로 바꾸고 렌더링도 `meta.error_code`를 읽도록 수정, 테스트 픽스처(`tests/RetrievalDebugViewer.test.tsx:59-64`)도 `error_code` 필드로 교체해 실제 API 계약과 일치시킨다.
2. **Requirement "Development-only retrieval debug route"의 두 Scenario에 대한 자동 테스트 부재** — `layout.tsx`의 dev/prod 분기 로직 자체는 코드상 올바르나(위 표 참고), 같은 패턴을 쓰는 `/preview/layout.tsx`와 달리 `preview-layout.test.tsx`에 대응하는 `retrieval-debug-layout.test.tsx` 류의 자동 테스트가 없다. tasks.md 4.3이 수동 확인만 요구하므로 task 완료 처리 자체는 스펙 위반이 아니지만, 이 change의 design.md도 "이 게이트가 핵심 안전장치"라고 명시한 만큼 회귀 방지를 위한 자동 테스트 추가를 권고한다(필수는 아님).

## 판정 근거

델타 스펙 5개 Scenario 중 4개는 코드 경로와 테스트로 명확히 확인됐다. 다섯 번째("A channel returns no results or fails")도 카드를 숨기지 않는다는 문구 자체는 지켜지지만, 실패 사유를 표시하는 코드가 실제 백엔드 응답 스키마(`error_code`)가 아니라 존재하지 않는 필드(`reason`)를 읽고 있어 항상 폴백 문구만 보여준다. 이는 스펙 범위 안에서 필드명 하나를 고치면 해결되는 결함이라 `blocked`가 아니라 `needs_fix`로 판정한다. tasks.md 3.6("내용 보기" 토글)은 design.md Decision 5에 근거가 있고, evidence.kind/channels별 테이블 매핑(`resolveContentTarget`, `RetrievalDebugViewer.tsx:111-125`)이 백엔드의 `_wiki_vector_hit`/`_wiki_lexical_hit`/`_source_hit` 및 `EvidenceHit.wiki`의 `evidence_id` 파생 규칙(`packages/core/src/nexuswiki_core/rrf.py:50-68`)과 정확히 일치하며, 기존 3개 Requirement의 시나리오(특히 채널별 원시 결과·융합 랭킹 표시)를 가리거나 대체하지 않고 순수 추가로만 붙어 있어 모순이 없다.
