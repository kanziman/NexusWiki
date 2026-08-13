---
status: complete
phase: 02-security-spine-and-shared-domain
source: [02-VERIFICATION.md]
started: 2026-08-07T06:20:00Z
updated: 2026-08-07T06:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. 클라우드 격리 왕복 (ap-southeast-1)

expected: 로컬에서 통과한 `apps/api/tests/test_workspaces_isolation.py`와 동등한 시나리오를 클라우드 프로젝트에 대해 1회 수행했을 때, 교차 테넌트 `PATCH`/`DELETE`가 403을 받는다.
result: pass
scope: partial
reported: |
  클라우드 Supabase 실측 2건 보고.
  (1) publishable key(anon 롤)로 8개 테이블 전체 접근이 HTTP 401로 차단됨.
  (2) 타인/미존재 워크스페이스 대상 PostgREST 조회가 HTTP 200 + `[]`(0행) 반환.
  프로브 워크스페이스 `queue-baseline-probe`로 확인.
limitation: |
  ⚠️ 관측 범위를 있는 그대로 남긴다 — 이 결과는 아래를 **증명하지 않는다**.
  · (1)의 anon 401은 `0007` 섹션 8이 anon에 grant를 0개 준 결과이며 이미 알던 사실이다.
    "로그인하지 않은 주체가 아무것도 못 한다"는 명제이지 "인증된 A가 인증된 B의 행에
    손대지 못한다"는 테넌트 격리 명제가 아니다. 두 명제는 다르다.
  · (2)는 읽기(SELECT) 경로이고 이 테스트가 요구한 것은 쓰기(`PATCH`/`DELETE`)다.
    SELECT가 막히면 UPDATE도 막히지만(UPDATE가 대상 행을 먼저 읽어야 한다),
    교차 테넌트 **쓰기** 왕복 자체는 클라우드에서 관측되지 않았다.
  · 요청 자격이 인증된 두 번째 사용자의 JWT였는지 확인되지 않았다(테스터 기억 불확실).
    미존재 UUID에 대한 `[]`는 RLS와 무관하게 참이므로 그 부분은 공허하다 —
    02-04의 fail-first가 잡아낸 것이 정확히 이 부류다.
  · 따라서 교차 테넌트 쓰기 차단은 여전히 **로컬 스택에서만** 관측된 상태다
    (`docs/ops/tenant-isolation-proof.md`). 전수 폐쇄는 Phase 7 `OPS-04`의 일이다.

why_human: 검증자는 로컬 스택에서만 격리 왕복을 재현했다. 마이그레이션 목록은 로컬/원격이 `0001`~`0007`로 일치하지만, 정책의 **런타임 거동**은 원격에서 관측되지 않았다. `conftest.py`는 `_assert_loopback()` 가드가 있어 원격을 가리킬 수 없으므로 자동 실행이 불가능하다 — 그 가드는 02-04가 의도적으로 넣은 것이며 제거하면 운영 프로젝트에 사용자를 만들고 지우게 된다.

⚠️ 이 항목이 이 페이즈에서 가장 무거운 미관측이다. 페이즈의 코어가 "격리는 애플리케이션이 아니라 RLS가 강제한다"인데, 그 강제가 실제로 도는 곳은 클라우드다.

### 2. workspaces 외 8개 테이블의 RLS 표본 확인

expected: `raw_sources` · `wiki_pages` · `source_chunks` · `wiki_embeddings` · `wiki_links` · `workspace_members` · `prompt_templates` · `jobs` 각각에서 타 워크스페이스 행에 대한 읽기/쓰기가 차단된다.
result: pass
scope: partial
reported: |
  클라우드에서 publishable key(anon 롤)로 8개 테이블 전체 접근이 HTTP 401로 차단됨을 확인.
limitation: |
  ⚠️ 소유자가 `pass`로 판정했다. 기록자는 `blocked`를 제안했고 그 근거를 남긴다 —
  판정을 뒤집지 않되 관측 범위는 있는 그대로 남긴다.
  · 이 8개 테이블에는 **라우터가 아직 없다**. 요구된 "타 워크스페이스 행에 대한
    읽기/쓰기 차단"의 애플리케이션 경로 왕복은 물리적으로 수행 불가능했다.
  · 확인된 것은 anon 롤 차단 하나다. 이는 `0007` 섹션 8이 anon에 grant를 0개 준
    설계의 귀결이며, 인증된 사용자 간 교차 테넌트 차단과는 다른 명제다.
  · 대부분의 테이블이 비어 있어 "차단됨"과 "행이 없음"을 관측으로 구분할 수 없다.
  · 본래 담당은 Phase 7 `OPS-04`의 전수 스위트다 (REQUIREMENTS.md 279행).
    그때까지 이 8개 테이블의 교차 테넌트 차단은 **정책 정의와 권한 매트릭스로만**
    확인된 상태로 남는다.

why_human: 격리 왕복 증명(fail-first 포함)은 `workspaces` 한 테이블만 덮는다. 나머지 8개는 정책 정의와 `0007` 섹션 8 권한 매트릭스로만 확인됐고, 라우터가 없어 애플리케이션 경로 왕복이 존재하지 않는다. 본래 담당은 Phase 7 `OPS-04`의 전수 스위트이나, 그 전까지 미관측 상태임을 소유자가 알아야 한다.

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

⚠️ 두 건 모두 `scope: partial`이다. 통과 개수만 읽고 "클라우드 격리가 전수 검증됐다"로
옮겨 적으면 안 된다 — 각 항목의 `limitation` 블록이 실제 관측 범위다. 교차 테넌트
**쓰기** 차단은 여전히 로컬 스택·`workspaces` 한 테이블에서만 관측됐다.

## Gaps

*(없음 — 검증 보고서의 갭 2건은 2026-08-07에 해소됨. 02-VERIFICATION.md의 `resolution` 블록 참조)*
