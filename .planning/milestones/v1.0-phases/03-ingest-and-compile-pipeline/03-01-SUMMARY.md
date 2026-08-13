---
phase: 03-ingest-and-compile-pipeline
plan: 01
subsystem: database
tags: [migration, pgvector, embedding, rls, ci, contract-test]
requires:
  - "supabase/migrations/0007_search_and_queue_extensions.sql (search_chunks 정의 · 권한 방향)"
  - "supabase/migrations/0002_search_schema.sql (embedding 컬럼 2개 · HNSW 인덱스 2개)"
  - "supabase/tests/0007_queue_functions.sql · scripts/verify_queue_functions.sh (계약 러너 관례)"
provides:
  - "extensions.vector(1024) 임베딩 컬럼 2종 (로컬 + 클라우드)"
  - "1024차 전제 위의 public.search_chunks (7개 계약 유지)"
  - "supabase/tests/0008_search_contract.sql + scripts/verify_search_contract.sh (검색 계약 러너)"
  - "scripts/ci_check_search_contract.sh + ci.yml 잡 search-contract (DB 없는 PR 게이트)"
  - "docs/ops/migration-0008-record.md (로컬·클라우드 관측 기록)"
affects:
  - "Phase 3의 나머지 8개 플랜 전부 — 임베딩 코드가 1024차 전제 위에서 시작한다"
  - "Phase 4 검색 경로 — search_chunks 시그니처와 hnsw GUC 3종"
tech-stack:
  added: []
  patterns:
    - "단일 트랜잭션 마이그레이션 (0007이 세운 관례)"
    - "SQL 계약 러너 = supabase/tests/*.sql + scripts/verify_*.sh (ON_ERROR_STOP=1 + 출력 grep)"
    - "DB 없이 도는 소스 수준 CI 게이트 (탐색 대상 0개는 fail)"
key-files:
  created:
    - supabase/migrations/0008_embedding_dimension.sql
    - supabase/tests/0008_search_contract.sql
    - scripts/verify_search_contract.sh
    - scripts/ci_check_search_contract.sh
    - docs/ops/migration-0008-record.md
    - .planning/phases/03-ingest-and-compile-pipeline/deferred-items.md
  modified:
    - .github/workflows/ci.yml
decisions:
  - "함수 인자의 typmod는 저장되지 않으므로 차원 계약은 카탈로그가 아니라 행동으로 단언한다"
  - "D-08의 CI 요구를 psql 러너 대신 소스 수준 토큰 게이트로 이행 — 러너에 Supabase 스택을 세우지 않는다는 ci.yml의 기존 결정을 지킨다"
  - "클라우드의 service_role EXECUTE 정정은 0009로 미룬다 — 0008은 이미 push되어 소급 수정 불가"
metrics:
  duration: "15m"
  completed: 2026-08-08
actuals:
  tokens: 11800
  tasks: 3
  commits: 3
status: complete
---

# Phase 3 Plan 01: 임베딩 차원 1024 보정 Summary

`0008`이 두 임베딩 컬럼·HNSW 인덱스 2종·`search_chunks`를 1024차로 옮겼고, 로컬 `db reset`과 클라우드
`db push`까지 이 플랜 안에서 끝났다 — 재임베딩 창이 0건일 때 닫았다.

## 무엇을 했나

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | `supabase/migrations/0008_embedding_dimension.sql` — 단일 트랜잭션, 7개 계약 이전 + ACL 복원 | `c0eed04` |
| 2 | SQL 계약 러너 한 쌍 + DB 없이 도는 CI 5번째 잡 `search-contract` | `9361332` |
| 3 | 로컬 reset · 계약 러너 2종 · 클라우드 push · 관측 기록 + 실측이 드러낸 계약 2건 정정 | `058b983` |

## 관측 결과

로컬·클라우드 양쪽에서 동일하게 관측된 것:

- `source_chunks.embedding` · `wiki_embeddings.embedding` = `vector(1024)`
- `public.search_chunks` 개수 `1` · `prosecdef=false` · `provolatile=s`
- `proconfig` = `search_path=public | hnsw.iterative_scan=strict_order | hnsw.ef_search=200 | hnsw.max_scan_tuples=40000`
- `has_function_privilege('authenticated', …)` = `true`, `('anon', …)` = `false`
- HNSW 인덱스 2종 = `hnsw / vector_cosine_ops` (이름·연산자 클래스 유지)
- `migration list` 원격 열 `0001`~`0008` 전부 일치
- 두 임베딩 컬럼의 비-null 행 수 클라우드 `0` — 되돌리기 비용이 `0`인 상태에서 적용됐다

게이트: `verify_search_contract.sh` exit 0 (`search_contract: ok`, 단언 9종) · `verify_queue_functions.sh`
exit 0 (기존 회귀 없음) · `ci_check_search_contract.sh` exit 0 (대상 0개에서 `2`, 토큰 누락에서 `1`) ·
`uv run pytest -rs` 147 passed · `pre-commit run --all-files` 통과.

전체 관측값 표와 방법은 `docs/ops/migration-0008-record.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 함수 인자의 typmod는 저장되지 않는다 — 계약 5를 행동 단언으로 교체**

- **Found during:** Task 3 (첫 계약 러너 실행)
- **Issue:** 플랜은 `pg_get_function_arguments`가 `vector(1024)`를 담는지 단언하라고 했으나, Postgres는 함수 **인자**의 typmod를 저장하지 않아 실제 반환값은 `p_query vector`다. 단언이 구조적으로 참이 될 수 없었다. 파생해서 `03-CONTEXT.md > D-01(4)`의 전제("시그니처에 1536이 박혀 있어 `create or replace`로는 바뀌지 않는다")도 사실이 아니며, `0008`의 섹션 2 주석이 그 거짓을 그대로 옮겨 적고 있었다.
- **Fix:** 계약 5를 카탈로그 단언에서 **행동 단언**으로 교체 — 1024차 질의는 5행을 돌려주고 1536차 질의는 거부된다(차원을 실제로 강제하는 것은 컬럼 타입이며 그 강제는 호출 시점에만 나타난다). `0008` 섹션 2 주석을 사실로 고치고 drop 후 create를 유지한 이유(D-01(4)의 형태 준수 + "함수는 정확히 하나"를 무조건 참으로)를 명시. `0008`은 이 시점에 아직 push 전이었다.
- **Files modified:** `supabase/tests/0008_search_contract.sql`, `supabase/migrations/0008_embedding_dimension.sql`
- **Commit:** `058b983`

**2. [Rule 1 - Bug] 계약 9(EXPLAIN)가 `enable_seqscan=off`만으로는 성립하지 않는다**

- **Found during:** Task 3
- **Issue:** 30행 픽스처에서는 `workspace_id` btree(`0002:108`) + Sort가 순차 스캔보다 싸서, HNSW 인덱스가 멀쩡해도 계획에 나타나지 않았다. 또 실패 메시지가 계획 JSON 전문을 인쇄해 1024차 질의 벡터가 통째로 쏟아져 읽을 수 없었다.
- **Fix:** `set local enable_sort = off` 추가(이 단언이 묻는 것은 "운영 계획"이 아니라 "인덱스가 이 컬럼·이 연산자에 쓰일 수 있는가"임을 주석으로 명시) + 실패 메시지를 `regexp_matches`로 뽑은 사용 인덱스명만 출력하도록 축약.
- **Files modified:** `supabase/tests/0008_search_contract.sql`
- **Commit:** `058b983`

**3. [Rule 2 - Missing critical functionality] 계약 러너가 실패 시 진단을 잃었다**

- **Found during:** Task 3
- **Issue:** analog(`scripts/verify_queue_functions.sh`)를 그대로 복사한 결과, `set -e` 하에서 명령 치환 대입이 실패하면 `printf` 이전에 종료해 psql 출력이 통째로 사라지고 종료 코드 `3`만 남았다. 어느 단언이 깨졌는지 알 수 없는 게이트다.
- **Fix:** 종료 코드를 받아 두었다가 출력을 먼저 인쇄한 뒤 판정. 판정은 그대로 non-zero이고 `ON_ERROR_STOP=1`도 유지. analog와 다른 유일한 지점이므로 이유를 주석으로 남겼다.
- **Files modified:** `scripts/verify_search_contract.sh`
- **Commit:** `058b983`

### 플랜 대비 형태를 바꾼 것

**4. [D-08 이탈] CI 게이트를 psql 계약 러너가 아니라 소스 수준 토큰 검사로 이행**

`03-CONTEXT.md > D-08`은 `Claude's Discretion` 블록 안에서 "PR 게이트에 추가"를 요구했다. 러너에 Supabase
스택을 세우지 않는다는 것은 `.github/workflows/ci.yml` 155-169행의 명시적 결정이므로, `search-contract` 잡은
`search_chunks`를 마지막으로 정의한 마이그레이션에서 계약 토큰 9종이 살아 있는지 소스로 본다. psql 러너는
로컬·수동 게이트로 남는다. 이유와 남는 사각은 `scripts/ci_check_search_contract.sh` 헤더와
`docs/ops/migration-0008-record.md` § 한계 4에 기록했다.

**5. [precondition] `SUPABASE_ACCESS_TOKEN`은 설정되어 있지 않다**

Task 3의 precondition은 토큰이 셸에 있을 것을 요구했으나 환경변수는 없었다. CLI의 저장된 세션으로
`supabase migration list --linked`가 비대화형으로 응답했고(원격 원장 마지막 항목이 `0007`임을 확인),
`0007` 적용 때와 같은 조건이다. precondition의 실제 의도(비대화형 원격 접근 + 원장 상태)는 충족됐으므로
진행했다.

## Known Stubs

없음. 이 플랜은 스텁을 남기지 않았다.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: elevation-of-privilege | `supabase/migrations/0008_embedding_dimension.sql` | ⚠️ **클라우드에서 `service_role`이 `public.search_chunks` EXECUTE를 갖는다** (로컬은 `false`). 클라우드의 `pg_default_acl`(schema `public`, objtype `f`, owner `postgres`)이 `anon,authenticated,service_role`에 EXECUTE를 주는데 로컬에는 그 항목이 없어, `0008`의 `revoke all … from public, anon`이 `service_role`을 걷어내지 못했다. T-03-02의 완화가 클라우드에서 부분 실패한 상태다. `0007`이 만든 상태를 `0008`이 재현한 것이며 `0008`은 push되어 소급 수정 불가 — 정정은 `0009`의 `revoke execute … from service_role` 한 줄. 심각도는 "열린 문"이 아니라 다층 방어 한 겹 상실(service_role 키 보유자는 이미 BYPASSRLS)이고 `search_chunks`를 부르는 코드는 아직 없다. |
| threat_flag: generalized-trap | `supabase/migrations/` 전체 | ⚠️ 위 항목의 일반형. `0007` §8이 **테이블**에 대해 적은 "새 객체는 `pg_default_acl`에서 기본 권한을 물려받으므로 revoke/grant 쌍을 반복하라"가 **함수에도, 클라우드에서만 더 넓게** 걸린다. `0009`+ 의 새 함수는 `revoke all … from public, anon, authenticated, service_role` 후 필요한 롤에만 grant할 것. `dead_letter_job()`(D-03)이 첫 적용 대상. |

## Self-Check: PASSED

- `supabase/migrations/0008_embedding_dimension.sql` FOUND
- `supabase/tests/0008_search_contract.sql` FOUND
- `scripts/verify_search_contract.sh` FOUND (실행 비트 있음)
- `scripts/ci_check_search_contract.sh` FOUND (실행 비트 있음)
- `docs/ops/migration-0008-record.md` FOUND
- `.planning/phases/03-ingest-and-compile-pipeline/deferred-items.md` FOUND
- 커밋 `c0eed04` · `9361332` · `058b983` FOUND
