---
phase: 02-security-spine-and-shared-domain
plan: 01
subsystem: database
tags: [pgvector, hnsw, postgrest, rls, asyncpg, supabase, explain, spike]

# Dependency graph
requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: "docs/ops/rtt-baseline.md의 결과 문서 골격, health_check.py의 트랜스포트 교체 지점(D-11), 로컬 Supabase 스택"
provides:
  - "DB 트랜스포트 결정 확정 — rpc(SECURITY INVOKER 함수 + 요청자 JWT), checklists.json > decisions.db_transport에 잠금"
  - "재현 가능한 스파이크 하네스: 고정 시드 합성 코퍼스 SQL, SECURITY INVOKER 검색 함수 2종 + 진단 함수 1종, 양 경로 러너"
  - "0007 섹션 1 검색 함수의 시그니처 원형과 GUC 3종 배치 형태"
  - "Phase 4 RTV-08 EXPLAIN 회귀 테스트의 계획 파싱 원형(walk_plan / has_hnsw_index_scan)"
  - "권한 공백 발견 — anon·authenticated·service_role이 public 9개 테이블에 arwd 부재, 0004 정책이 현재 무력"
affects: [02-03 UserDb, 02-06 마이그레이션 0007, Phase 4 검색 융합, RTV-08]

actuals:
  tokens: 16847
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: ["asyncpg==0.31.0 (일회성 러너 의존성, 워크스페이스 고정 의존성 아님)"]
  patterns:
    - "SECURITY INVOKER + 함수 정의 set 절에 hnsw GUC 3종을 박는 검색 함수 형태"
    - "EXPLAIN 계획 트리를 재귀 순회해 인덱스 '이름'까지 대조하는 판정"
    - "고정 시드 · 병렬 끄기로 재현 가능한 합성 코퍼스"

key-files:
  created:
    - supabase/spike/0001_transport_corpus.sql
    - supabase/spike/0002_search_fn_rpc.sql
    - supabase/spike/README.md
    - scripts/spike_db_transport.py
    - docs/ops/db-transport-spike.md
  modified:
    - checklists.json

key-decisions:
  - "DB 트랜스포트는 rpc — 판정 3조건이 겨냥한 실패 양상이 RPC 경로에서 하나도 관측되지 않았고, D-03의 '확실한 쪽으로 기운다' 지침과 일치"
  - "D-03의 기계적 3조건 규칙은 실제 질의 형태에서 변별력이 없다 — 두 트랜스포트가 노드 단위 동일 플랜을 내며 조건 2 실패는 플래너 비용 판단"
  - "권한 공백의 영구 수정은 0007의 최소권한 역할 × 테이블 × 동작 매트릭스로 (사용자 결정)"

patterns-established:
  - "판정 보조 진단: 원인이 둘 이상일 수 있는 관측은 하나를 차단해(enable_sort=off) 원인을 분리한 뒤 기록한다"
  - "스파이크 자산은 버리지 않는다 — 계획 파싱이 Phase 4 회귀 테스트로 이어진다"
  - "자격증명은 커밋 파일에 두지 않는다 — psql \\getenv + docker exec -e, 러너는 CLI/환경변수/supabase status만"

requirements-completed: [DOM-01]

coverage:
  - id: D1
    description: "DB 트랜스포트가 스파이크 실측으로 결정되고 checklists.json > decisions.db_transport에 잠겼다"
    requirement: DOM-01
    verification:
      - kind: integration
        ref: "node -e \"console.log(require('./checklists.json').decisions.db_transport.value)\""
        status: pass
    human_judgment: false
  - id: D2
    description: "50,000행 · 타깃 750행(1.5%) 고정 시드 코퍼스가 재현 가능하게 적재된다"
    requirement: DOM-01
    verification:
      - kind: integration
        ref: "supabase/spike/0001_transport_corpus.sql 내장 검사(총행수·타깃행수·HNSW 인덱스 존재) + embedding md5 회차 간 동일"
        status: pass
    human_judgment: false
  - id: D3
    description: "RPC·asyncpg 양 경로가 각각 3회 실행되고 회차 간 판정이 일치한다"
    requirement: DOM-01
    verification:
      - kind: integration
        ref: "uv run --with httpx --with 'asyncpg==0.31.0' python scripts/spike_db_transport.py --transport {rpc,asyncpg} --k 20 --repeat 3"
        status: pass
    human_judgment: false
  - id: D4
    description: "판정 3조건의 실측값이 경로별·회차별로 개별 기록되고 부분 충족이 통과로 적히지 않았다"
    requirement: DOM-01
    verification: []
    human_judgment: true
    rationale: "문서가 관측되지 않은 것을 관측된 것처럼 서술하지 않았는지는 사람이 읽어야 판정된다(플랜 prohibitions, check_kind: doc-review)"

# Metrics
duration: 1h 5m
completed: 2026-08-06
status: complete
---

# Phase 02 Plan 01: DB 트랜스포트 스파이크 Summary

**50,000행 중 타깃 750행(1.5%) 적대적 코퍼스에서 RPC와 asyncpg를 각각 3회 실측해 트랜스포트를 rpc로 확정했고, 그 과정에서 `authenticated`·`service_role`이 9개 테이블에 DML 권한을 전혀 갖고 있지 않아 `0004`의 RLS 정책이 현재 무력하다는 사실을 발견했다**

## Performance

- **Duration:** 1h 5m
- **Started:** 2026-08-06T04:30:00Z
- **Completed:** 2026-08-06T05:10:00Z
- **Tasks:** 3 (체크포인트 2건 경유)
- **Files modified:** 6

## Accomplishments

- **트랜스포트 확정 (DOM-01).** `checklists.json > decisions.db_transport`에 `rpc`를 잠갔다. 근거는 문서가 아니라 실측이며 `docs/ops/db-transport-spike.md`가 경로 × 회차별 다섯 관측 열을 개별로 담는다.
- **ROADMAP 성공기준 3의 실측 답을 얻었다.** `create function ... SET hnsw.iterative_scan`이 Supabase RPC로 **실제 적용된다.** 강제 HNSW 계획에서 GUC 3종 · HNSW Index Scan · `k=20` 전부 충족했고, `Filter: … is_workspace_member(workspace_id)`가 RLS가 함께 걸렸음을 직접 보인다. STATE.md의 해당 블로커를 해소로 갱신했다.
- **D-03 규칙의 한계를 드러냈다.** 실제 질의 형태에서 두 트랜스포트는 노드 단위로 동일한 계획을 냈다. 조건 2가 깨진 원인은 트랜스포트가 아니라 플래너 비용(btree+sort `233` vs HNSW `349,657`, 타깃 750행)이다. 규칙을 문자 그대로 적용하면 asyncpg가 되지만 그 탈락 사유는 asyncpg의 장점과 무관하다 — 이 사실을 판정 절에 명시했다.
- **권한 공백 발견.** `pg_default_acl`이 세 롤에 `Dxtm`만 부여해 `anon`·`authenticated`·`service_role` 모두 `public` 9개 테이블에 `arwd`가 없다. RLS는 이미 가진 권한을 좁힐 뿐이므로 `0004`의 정책 20여 개가 현재 무력하고, 요청자 JWT 경로와 워커 경로 모두 실제 질의에서 `42501`로 떨어진다.
- **하네스가 남았다.** 계획 파싱(`walk_plan` / `has_hnsw_index_scan`)이 Phase 4 RTV-08 회귀 테스트의 원형이며 버리는 코드가 아니다.

## Task Commits

1. **Task 1 (tracer): 얇은 한 경로 관통 — 요청자 JWT에서 EXPLAIN 계획까지** - `bf021cb` (feat)
2. **Task 2: 적대적 코퍼스 50,000행 확장 + 양 경로 3회 반복 실측** - `04a0a69` (feat)
3. **Task 3: 결정을 checklists.json에 잠그고 결과 문서 확정** - `d6dcf56` (docs)

## Files Created/Modified

- `supabase/spike/0001_transport_corpus.sql` - 고정 시드 합성 코퍼스. 행 수를 psql 변수로 받아 얇은 관통과 본 판정이 같은 스크립트를 쓴다. 총행수·타깃행수·HNSW 인덱스 존재를 스스로 검사하고 어긋나면 예외로 죽는다
- `supabase/spike/0002_search_fn_rpc.sql` - `spike_search_chunks`(security invoker, stable, GUC 3종), 동일 인자·GUC의 `spike_explain_search_chunks`, 진단용 `spike_explain_search_chunks_forced`
- `supabase/spike/README.md` - 실행 순서, 판정 기준표, 알려진 사실
- `scripts/spike_db_transport.py` - RPC/asyncpg 양 경로 러너. 3회 반복 판정 불일치 시 non-zero 종료
- `docs/ops/db-transport-spike.md` - 측정 일시·방법·결과·판정 4절, 나중 페이즈용 5개 요약, 다운스트림 소비자 문단
- `checklists.json` - `decisions.db_transport` 잠금 + `open_questions` carry-forward 4건

## Decisions Made

- **트랜스포트는 rpc.** 판정 3조건이 겨냥한 실패 양상(GUC 미전달 · HNSW 미사용 · `k` 미충족)이 RPC 경로에서 하나도 관측되지 않았다. asyncpg는 측정된 이득 없이 D-04의 은밀한 격리 상실 위험(`set local role` / `set local request.jwt.claims` 중 하나만 빠져도 에러 없이 격리 해제)을 추가로 떠안는다. Phase 4에서 질의 변경마다 마이그레이션(`0008`, `0009`…)이 필요하다는 대가는 인지한 상태에서 감수했다.
- **권한 공백의 수정 형태는 최소권한 매트릭스** (사용자 결정, 소유자는 `0007`/02-06): `anon`은 실제로 필요하지 않으면 무권한, `authenticated`/`service_role`은 Phase 2의 실제 경로가 쓰는 테이블·동작만, 포괄적 `grant all` 금지, 함수 EXECUTE 명시하되 `claim_job` 계열의 기존 revoke 경계는 유지.
- **asyncpg는 `0.31.0`으로 핀 고정.** 버전 없는 `--with asyncpg`는 매 실행이 다른 것을 설치해 3회 반복 재현성 전제를 깬다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `create function ... set hnsw.*`가 `permission denied to set parameter`로 실패**
- **Found during:** Task 1 (검색 함수 생성)
- **Issue:** `hnsw.*` GUC는 `vector.so`가 백엔드에 적재된 뒤에야 정식 등록된다. 적재 전에는 미지의 placeholder 변수라 함수 정의의 `set` 절에서 거부되며, Supabase의 `postgres` 롤은 superuser가 아니라 `load 'vector'`도 허용되지 않는다
- **Fix:** 함수 생성 앞에 `select '[1,2,3]'::extensions.vector` 한 줄을 두어 입력 함수가 라이브러리를 적재하게 했다. ⚠️ 주석으로 근거를 남겼고 `0007` 다운스트림 문단에도 이 함정을 기록했다
- **Files modified:** `supabase/spike/0002_search_fn_rpc.sql`
- **Verification:** 두 함수 모두 `CREATE FUNCTION` 성공
- **Committed in:** `bf021cb`

**2. [Rule 3 - Blocking] `authenticated`에 `source_chunks` SELECT 권한 부재로 RPC가 42501**
- **Found during:** Task 1 (RPC 왕복 시험)
- **Issue:** `pg_default_acl`이 `public` 스키마 테이블에 세 롤 모두 `Dxtm`만 부여한다. RLS 정책은 이미 가진 권한을 좁힐 뿐이라 `0004`의 정책이 무력하다
- **Fix:** 스파이크 진행에 필요한 최소 권한(`grant select on public.source_chunks to authenticated`) 하나만 국소 부여하고 **비영구**임을 파일에 명시했다. 영구 조치는 `0007`의 몫이라 여기서 마이그레이션을 쓰지 않았다(Rule 4 — 아키텍처 결정)
- **Files modified:** `supabase/spike/0002_search_fn_rpc.sql`
- **Verification:** RPC가 20행 반환, 계획에 `is_workspace_member` 필터 확인
- **Committed in:** `bf021cb`

**3. [Rule 2 - Missing Critical] 자격증명을 커밋 파일에서 제거하기 위한 실행 명령 변경**
- **Found during:** Task 1 (코퍼스 SQL 작성)
- **Issue:** 스파이크 사용자 비밀번호를 SQL/러너에 기본값으로 두면 커밋된 파일에 자격증명이 영구히 남는다(T-02-01)
- **Fix:** psql `\getenv`로 `SPIKE_USER_PASSWORD`를 읽고 8자 미만이면 예외로 죽게 했다. 그 결과 플랜의 리터럴 명령에 `-e SPIKE_USER_PASSWORD`가 추가로 필요하다 — README에 명시
- **Files modified:** `supabase/spike/0001_transport_corpus.sql`, `supabase/spike/README.md`
- **Verification:** `grep -cE 'sb_secret_|postgres:[A-Za-z0-9]' scripts/spike_db_transport.py` = 0
- **Committed in:** `bf021cb`

**4. [Rule 2 - Missing Critical] 판정 조건 2의 원인을 분리하는 진단 추가**
- **Found during:** Task 2 (본 판정 실측)
- **Issue:** 기본 계획에서 `has_hnsw_index_scan`이 양쪽 모두 거짓인데, 그것만으로는 "GUC가 전달되지 않았다"와 "플래너가 HNSW를 고르지 않았다"를 구분할 수 없다. 구분 없이 기록하면 플랜의 prohibitions가 금지한 "관측되지 않은 것을 관측된 것처럼 서술"에 해당한다
- **Fix:** `enable_sort = off`를 건 진단 함수 `spike_explain_search_chunks_forced`와 러너 `--forced-hnsw` 플래그를 추가해 원인을 분리하고 양 경로에서 3/3을 관측했다. 진단 전용이며 `0007`로 승격하지 말라는 ⚠️ 주석을 달았다
- **Files modified:** `supabase/spike/0002_search_fn_rpc.sql`, `scripts/spike_db_transport.py`
- **Verification:** 강제 시 rpc·asyncpg 모두 `all_conditions_met: true`
- **Committed in:** `04a0a69`

**5. [Rule 1 - Bug] 임베딩 생성 서브쿼리가 InitPlan으로 끌어올려져 전 행이 동일 벡터가 될 뻔함**
- **Found during:** Task 1 (코퍼스 작성)
- **Issue:** 바깥 행을 참조하지 않는 서브쿼리는 플래너가 한 번만 평가한다. 1,000행 시험에서 distinct 벡터가 1개로 나왔다. 그 코퍼스에서는 HNSW가 무엇을 하든 판정이 통과해 스파이크가 아무것도 변별하지 못한다
- **Fix:** `0 * e.i`로 상관 참조를 강제했다. 1,000행에서 distinct 1,000 확인. ⚠️ 주석으로 이유를 남겼다
- **Files modified:** `supabase/spike/0001_transport_corpus.sql`
- **Verification:** `count(distinct vec)` = 행 수
- **Committed in:** `bf021cb`

**6. [Rule 1 - Bug] 병렬 스캔이 setseed 재현성을 깨뜨림 / psql 변수가 달러 인용 블록에서 치환되지 않음**
- **Found during:** Task 1
- **Issue:** (a) 병렬 워커가 붙으면 `random()` 호출 순서가 실행마다 달라져 고정 시드 전제가 무너진다. (b) psql은 `$$ ... $$` 안에서 `:변수`를 치환하지 않아 DO 블록이 구문 오류로 죽었다
- **Fix:** `max_parallel_workers_per_gather = 0` 설정, 파라미터를 `set_config`로 세션 GUC에 실어 DO 블록이 `current_setting`으로 읽게 했다
- **Files modified:** `supabase/spike/0001_transport_corpus.sql`
- **Verification:** 같은 스크립트 2회 실행 시 embedding 전체 md5 동일(`1a73cc826990b6c1f502efd95811aedc`)
- **Committed in:** `bf021cb`

---

**Total deviations:** 6 auto-fixed (3 blocking, 2 missing critical, 1 bug 범주 중복 포함)
**Impact on plan:** 전부 판정 자체의 성립이나 보안에 필요한 것이었다. 진단 함수 1개와 러너 플래그 1개가 계획에 없던 추가분이지만, 그것 없이는 판정 절이 "조건 2 거짓"의 원인을 말할 수 없어 prohibitions를 위반하게 된다. 스코프 확대는 없다.

## Issues Encountered

- **GoTrue가 SQL로 심은 사용자에 500을 반환.** `confirmation_token` 등 토큰 컬럼이 NULL이면 `converting NULL to string is unsupported`로 죽는다. 빈 문자열로 채우고 `auth.identities` 행을 함께 만들어 해결했고, 그 이유를 코퍼스 SQL에 ⚠️ 주석으로 남겼다.
- **50,000행 적재가 약 7분 30초 소요.** HNSW 증분 인덱스 유지 비용이며 일회성이라 최적화하지 않았다.
- **얇은 관통(200행)에서 `has_hnsw_index_scan`이 거짓.** 코퍼스가 작으면 판정이 변별력을 잃는다는 D-02 경고가 그대로 관측된 것이며 정상이다. README에 기록했다.

## Known Stubs

없음. Task 1이 남겼던 `run_asyncpg`의 `NotImplementedError` 스텁은 Task 2에서 실제 구현으로 교체되었다.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: privilege-gap | `supabase/migrations/0004_rls_policies.sql` | `anon`·`authenticated`·`service_role`이 `public` 9개 테이블에 `arwd` 권한을 갖고 있지 않아 RLS 정책 20여 개가 현재 무력하다. 파일 머리말 12-13행의 "이미 전권 GRANT를 가진다"는 전제가 현재 Supabase CLI 기본값에서 사실이 아니다. 영구 수정 소유자는 `0007`/02-06 |
| threat_flag: non-permanent-grant | `supabase/spike/0002_search_fn_rpc.sql` | 스파이크 진행용 `grant select on public.source_chunks to authenticated`가 로컬에 남아 있다. 로컬 전용이며 `supabase db reset`이 지운다 |

## User Setup Required

None - 로컬 스택과 환경변수 `SPIKE_USER_PASSWORD` 외에 외부 서비스 설정이 필요하지 않다.

## Next Phase Readiness

- **02-03(`UserDb`)이 진행 가능하다.** 트랜스포트가 rpc로 확정되어 asyncpg 커넥션 계층이 필요 없고, D-04가 asyncpg 채택 시 요구하던 "GUC 세팅 없이 쿼리할 수 있는 공개 API를 두지 않는다" 제약은 해소되었다. 쓰기 경로 0행 → 403 매핑(D-11)은 그대로 유효하다.
- **02-06(`0007`)이 진행 가능하다.** 섹션 1 검색 함수의 시그니처 원형이 `supabase/spike/0002_search_fn_rpc.sql`에 있다.
- ⚠️ **`0007`은 권한 매트릭스를 반드시 함께 닫아야 한다.** 닫지 않으면 새 검색 함수가 `authenticated`에게 `42501`을 던진다. 오케스트레이터가 Wave 3 디스패치 전에 02-06-PLAN에 이 요구사항을 반영하기로 되어 있다(02-01 스코프 밖이라 여기서 플랜을 고치지 않았다).
- ⚠️ **`0007`의 검색 함수 앞에 벡터 표현식 평가가 선행해야 한다.** 없으면 `set hnsw.*`가 `permission denied to set parameter`로 마이그레이션을 실패시킨다.
- **로컬 코퍼스 정리:** 50,000행은 로컬 전용이며 클라우드에 적재하지 않는다. `supabase db reset`(02-06-PLAN Task 2)이 지운다.

---
*Phase: 02-security-spine-and-shared-domain*
*Completed: 2026-08-06*
