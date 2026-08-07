---
status: testing
phase: 02-security-spine-and-shared-domain
source: [02-VERIFICATION.md]
started: 2026-08-07T06:20:00Z
updated: 2026-08-07T06:20:00Z
---

## Current Test

number: 1
name: 클라우드(ap-southeast-1)에서 교차 테넌트 쓰기가 403으로 막히는지 실제 왕복으로 확인
expected: |
  로컬과 동일하게 교차 테넌트 `PATCH`/`DELETE /workspaces/{id}`가 403을 받는다.
awaiting: user response

## Tests

### 1. 클라우드 격리 왕복 (ap-southeast-1)

expected: 로컬에서 통과한 `apps/api/tests/test_workspaces_isolation.py`와 동등한 시나리오를 클라우드 프로젝트에 대해 1회 수행했을 때, 교차 테넌트 `PATCH`/`DELETE`가 403을 받는다.
result: [pending]

why_human: 검증자는 로컬 스택에서만 격리 왕복을 재현했다. 마이그레이션 목록은 로컬/원격이 `0001`~`0007`로 일치하지만, 정책의 **런타임 거동**은 원격에서 관측되지 않았다. `conftest.py`는 `_assert_loopback()` 가드가 있어 원격을 가리킬 수 없으므로 자동 실행이 불가능하다 — 그 가드는 02-04가 의도적으로 넣은 것이며 제거하면 운영 프로젝트에 사용자를 만들고 지우게 된다.

⚠️ 이 항목이 이 페이즈에서 가장 무거운 미관측이다. 페이즈의 코어가 "격리는 애플리케이션이 아니라 RLS가 강제한다"인데, 그 강제가 실제로 도는 곳은 클라우드다.

### 2. workspaces 외 8개 테이블의 RLS 표본 확인

expected: `raw_sources` · `wiki_pages` · `source_chunks` · `wiki_embeddings` · `wiki_links` · `workspace_members` · `prompt_templates` · `jobs` 각각에서 타 워크스페이스 행에 대한 읽기/쓰기가 차단된다.
result: [pending]

why_human: 격리 왕복 증명(fail-first 포함)은 `workspaces` 한 테이블만 덮는다. 나머지 8개는 정책 정의와 `0007` 섹션 8 권한 매트릭스로만 확인됐고, 라우터가 없어 애플리케이션 경로 왕복이 존재하지 않는다. 본래 담당은 Phase 7 `OPS-04`의 전수 스위트이나, 그 전까지 미관측 상태임을 소유자가 알아야 한다.

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

*(없음 — 검증 보고서의 갭 2건은 2026-08-07에 해소됨. 02-VERIFICATION.md의 `resolution` 블록 참조)*
