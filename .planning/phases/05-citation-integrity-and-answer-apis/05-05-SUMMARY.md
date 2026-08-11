---
phase: 05-citation-integrity-and-answer-apis
plan: 05
subsystem: api
tags: [wiki, verification, graph, rls]
requires:
  - phase: 05-citation-integrity-and-answer-apis
    provides: wiki_graph_neighborhood RPC와 stamp_wiki_verification 트리거
provides:
  - Editor 이상 RLS 정책과 DB 감사 트리거를 재사용한 위키 검증 전이 API
  - RLS 범위와 fanout/total_limit 상한을 지키는 그래프 이웃 조회 API
  - API-04 잡 진행률 표면에 새 엔드포인트가 불필요하다는 문서화된 감사 결론
affects: [api, wiki, graph, dashboard]
actuals:
  tasks: 2
  commits: 2
key-files:
  created:
    - apps/api/src/api/routers/wiki.py
    - apps/api/src/api/routers/graph.py
    - apps/api/tests/test_graph_router.py
  modified:
    - apps/api/src/api/main.py
    - apps/api/tests/conftest.py
    - apps/api/tests/test_workspaces_isolation.py
requirements-completed: [QC-02, API-04]
completed: 2026-08-12
status: complete
---

# Phase 05 Plan 05: Citation Integrity and Answer APIs Summary

**위키 검증 전이는 RLS와 DB 트리거가 보증하고, 그래프 조회는 요청 전에 엄격한 상한을 검증한다.**

## Accomplishments

- `PATCH /workspaces/{id}/wiki/{wiki_id}/verify`를 추가했다. 요청 본문은 검증 상태와 선택적 만료일만 받으며, `verified_by`/`verified_at`은 `stamp_wiki_verification()` 트리거가 기록한다.
- viewer의 같은 워크스페이스 검증 전이는 403이며 행 상태를 바꾸지 않고, foreign wiki도 동일한 403 계약을 유지한다.
- `GET /workspaces/{id}/graph`를 추가했다. `wiki_graph_neighborhood` RPC를 requester JWT로 호출하고 `fanout` 1..20, `total_limit` 1..200을 FastAPI 입력 경계에서 제한한다.
- API-04의 잡 진행률 요구는 기존 `list_source_jobs`의 `chain_position`/`chain_total`이 이미 충족한다는 결론을 graph router 모듈 문서에 기록했다.

## Task Commits

1. **Task 1: QC-02 위키 검증 전이 API** — `b292c8e`
2. **Task 2: API-04 제한 그래프 조회 API** — `1868e5a`

## Verification

- `uv run pytest apps/api/tests/test_workspaces_isolation.py -x` — 15 passed
- `uv run pytest apps/api/tests/test_graph_router.py -x` — 3 passed
- `uv run pytest apps/api/tests/test_workspaces_isolation.py apps/api/tests/test_graph_router.py -x` — 18 passed
- `uv run pytest` — 399 passed

## Deviations from Plan

그래프의 실제 두 간선은 owner `UserDb.insert_one()`가 아니라 local service-role 테스트 fixture로 만들었다. `wiki_links`는 의도적으로 사용자 경로에서 SELECT 전용이며 INSERT RLS 정책이 없어서, 계획의 owner-JWT 삽입 방식은 403이 된다. 프로덕션 권한을 넓히지 않고 테스트 데이터 준비에만 service-role을 사용했으며, API 호출 자체와 교차 테넌트 RPC 검증은 모두 requester JWT로 수행했다.

## Next Phase Readiness

다음 Phase 05 계획은 두 API surface를 직접 소비하거나 대시보드에 연결할 수 있다.

## Self-Check: PASSED

- verification router는 별도 역할 확인 없이 `UserDb.update_one()`과 기존 `wiki_pages_update_editor` RLS를 사용한다.
- 검증 응답은 내부 위키 내용·별칭을 노출하지 않는 좁은 계약이다.
- graph router는 비정상 RPC 응답을 502로 처리하며, 입력 상한 밖의 요청은 RPC 전에 422로 끝난다.
