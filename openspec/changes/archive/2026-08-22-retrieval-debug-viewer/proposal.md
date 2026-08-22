## Why

개발자가 답변에 근거가 부족하거나 이상해 보일 때, 그 원인이 검색 단계(어느 채널이 무엇을 얼마나 순위 매겼는지)인지 LLM 단계인지 구분할 방법이 없다. `/w/[workspaceId]/ask`는 LLM 답변까지 거친 최종 결과만 보여주고, 4채널(wiki_vector · source_vector · wiki_lexical · source_lexical) 각각의 원시 순위나 RRF 융합 기여 점수는 화면 어디에도 노출되지 않는다. 백엔드에는 이미 이 데이터를 반환하는 순수 검색 엔드포인트가 있는데, 그걸 눈으로 확인할 화면이 없다.

## What Changes

- 워크스페이스 로그인 세션으로 실제 검색 파이프라인을 조회해, 질의 하나에 대해 4채널 원시 결과와 RRF 융합 랭킹을 나란히 보여주는 개발자 전용 화면을 신설한다.
- 이 화면은 로컬 개발 서버(`NODE_ENV === "development"`)에서만 렌더링되고, 배포된 환경(Vercel 프로덕션·프리뷰)에서는 무조건 404를 반환한다 — `/preview`가 쓰는 것과 같은 환경 게이트를 별도 라우트에 재사용한다.
- 백엔드 변경은 없다. 이미 존재하는 `POST /workspaces/{id}/retrieval`(LLM 답변 생성 없이 evidence + meta만 반환)을 그대로 호출한다.

**이 change에서 하지 않는 것**
- `/preview` 트리를 건드리지 않는다. `local-product-preview`는 "실제 워크스페이스를 조회하지 않는다"를 명시적으로 요구하는데, 이 화면은 정반대로 실제 워크스페이스를 조회해야 의미가 있어 같은 트리에 둘 수 없다(design.md 참고).
- 배포 환경(스테이징 등)에서의 접근을 다루지 않는다. 이번 게이트는 로컬 개발 서버로 한정한다 — 배포된 환경에서 특정 계정에게만 허용하는 요구는 다른 접근 제어(역할 기반)가 필요한 별개 결정이라 범위 밖이다.
- `scripts/benchmark_retrieval.py`(CLI 골든 질의 일괄 검증)를 대체하지 않는다. 이 화면은 질의 하나씩 대화식으로 살펴보는 용도이고, 그 스크립트는 회귀 검증용으로 계속 쓰인다.

## Capabilities

### New Capabilities
- `retrieval-debug-viewer`: 개발자가 로컬 개발 서버에서 실제 워크스페이스에 질의를 던져 4채널 원시 검색 결과와 RRF 융합 랭킹(채널별 기여 점수)을 확인하는 화면

### Modified Capabilities
없음 — `POST /workspaces/{id}/retrieval` 응답 계약을 그대로 소비할 뿐 백엔드 요구사항은 바뀌지 않는다.

## Impact

- **신설**: `apps/dashboard/app/w/[workspaceId]/debug/retrieval/` (route + layout 환경 게이트 + 페이지)
- **재사용**: `apps/dashboard/lib/api-client.ts`의 `apiFetch` (변경 없음), `POST /workspaces/{id}/retrieval` (변경 없음)
- **영향 없음**: 백엔드 코드, 마이그레이션, RLS 정책, 기존 라우트(`/ask`, `/preview` 등) — 전부 그대로
- 배포 번들에는 포함되지만 `layout.tsx`의 환경 게이트가 프로덕션 요청을 막는다(⚠️ `/preview`와 동일하게, middleware matcher와 독립적으로 라우트 자체가 막아야 한다 — `local-product-preview` design.md의 같은 판단을 따른다)
