# Phase 3: Ingest and Compile Pipeline - Pattern Map

**Mapped:** 2026-08-07
**Files analyzed:** 24 (new/modified, derived from 03-CONTEXT.md — no RESEARCH.md exists)
**Analogs found:** 21 / 24

> ⚠️ 이 문서는 "무엇을 만드는가"가 아니라 "무엇을 베끼는가"만 정한다. 파일 목록은 CONTEXT.md의
> D-01~D-09 + `<code_context>` Integration Points + 위임된 3영역(COMP-01/07 · OPS-01 · ING-04/05)에서
> 유도한 것이며, planner가 조정할 수 있다. 조정하더라도 아래 **analog 배정**은 유지할 것.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `supabase/migrations/0008_embedding_dimension.sql` | migration | batch DDL | `supabase/migrations/0007_search_and_queue_extensions.sql` | exact |
| `supabase/migrations/0009_*.sql` (`dead_letter_job` · `usage_events` · 취소) | migration | batch DDL | `0007` §3·§4·§8 | exact |
| `supabase/tests/0008_search_contract.sql` | test (SQL 계약) | batch | `supabase/tests/0007_queue_functions.sql` | exact |
| `scripts/verify_search_contract.sh` | script | batch | `scripts/verify_queue_functions.sh` | exact |
| `docs/ops/migration-0008-record.md` | doc | — | `docs/ops/migration-0007-record.md` | exact |
| `.github/workflows/*.yml` (5번째 잡 추가) | config | CI | 기존 4잡 (02-09-PLAN) | modify |
| `apps/worker/src/worker/handlers/parse.py` | handler | file-I/O → transform | `apps/worker/src/worker/handlers/noop.py` | role-match |
| `apps/worker/src/worker/handlers/compile.py` | handler | request-response (LLM) | `handlers/noop.py` + `worker/rtt.py` (httpx) | role-match |
| `apps/worker/src/worker/handlers/link_sync.py` | handler | CRUD | `handlers/noop.py` | role-match |
| `apps/worker/src/worker/handlers/embed.py` | handler | batch → CRUD | `handlers/noop.py` | role-match |
| `apps/worker/src/worker/handlers/__init__.py` | registry | — | 자기 자신 (행 추가만) | modify |
| `apps/worker/src/worker/llm.py` (OpenRouter 채팅 + Pydantic 3회 재시도) | service | request-response | `worker/db/service.py` `service_client()` + `rtt.py` | role-match |
| `apps/worker/src/worker/embedding.py` (OpenRouter `/embeddings`, provider 고정) | service | request-response | 위와 동일 | role-match |
| `apps/worker/src/worker/db/service.py` | service (DB) | CRUD | 자기 자신 (도메인 테이블 헬퍼 추가) | modify |
| `apps/worker/src/worker/queue.py` | service (queue) | event-driven | 자기 자신 (`_dead_letter` 교체 · `sanitize_error` provider 마스킹) | modify |
| `apps/worker/src/worker/settings.py` | config | — | 자기 자신 (`OPENAI_API_KEY` 제거 · 임베딩 필드) | modify |
| `packages/core/src/nexuswiki_core/chunking.py` | utility | transform | `packages/core/src/nexuswiki_core/tokenizer.py` | exact |
| `packages/core/src/nexuswiki_core/extract.py` (PDF/URL 추출 + 품질 게이트) | utility | file-I/O | `tokenizer.py` (순수 함수 + 버전 상수 규약) | role-match |
| `apps/api/src/api/routers/sources.py` (ING-01 202 인큐) | router | request-response | `apps/api/src/api/routers/workspaces.py` | exact |
| `apps/api/src/api/routers/jobs.py` (ING-06 진행 · ING-07 재시도 · OPS-01 취소) | router | request-response | `routers/workspaces.py` | exact |
| `apps/api/src/api/db/user.py` | service (DB) | CRUD | 자기 자신 (`insert_one` 추가) | modify |
| `apps/api/src/api/settings.py` | config | — | `apps/worker/src/worker/settings.py` | exact |
| `apps/worker/tests/test_handlers_*.py` · `apps/api/tests/test_sources_router.py` | test | — | `apps/worker/tests/test_handlers.py` · `apps/api/tests/conftest.py` | exact |
| `.env.sample` | config | — | 자기 자신 (§3 키 정리) | modify |

---

## Pattern Assignments

### `supabase/migrations/0008_embedding_dimension.sql` (migration, batch DDL)

**Analog:** `supabase/migrations/0007_search_and_queue_extensions.sql`

**헤더 패턴** (`0007:1-32`) — 태스크 ID · 결정 키 · 상태 전이 다이어그램 · `⚠️` 부분적용 경고:
```sql
-- =============================================================================
-- NexusWiki 0007: 검색 함수 · 큐 확장 · 최소권한 매트릭스
--
-- 관련 태스크: P2-BE-01(섹션 1) · P2-JOB-01(섹션 2·3·4) · P2-QC-01(섹션 5)
-- 설계 근거:  checklists.json > decisions.db_transport   (섹션 1)
--             02-CONTEXT.md > D-21                       (섹션 1~6의 구성 순서)
-- ...
-- ⚠️ 이 파일은 저장소에서 처음으로 자기 자신을 begin/commit으로 감쌉니다.
-- =============================================================================
```
→ `0008`은 `설계 근거: checklists.json > decisions.embedding_model` + `03-CONTEXT.md > D-01, D-06, D-07`을
   같은 형식으로 쓴다. D-06이 요구한 "`0002:76` 주석 무효" 문장이 이 블록 안에 들어간다.

**트랜잭션 경계** (`0007:34`, `0007:390-392`) — D-07이 그대로 지시:
```sql
begin;
...
-- PostgREST 스키마 캐시 갱신. 갱신 전에는 새 함수 호출이 PGRST202로 떨어집니다.
notify pgrst, 'reload schema';

commit;
```

**컬럼 타입 변경 패턴** (`0007:308-312`) — "0002 원본은 수정하지 않고 앞으로 나아간다":
```sql
alter table public.source_chunks
  alter column tsv_tokenizer_version type text;
```
→ D-01(1)(2)는 `alter column embedding type extensions.vector(1024)`. ⚠️ 행이 0개라 `using` 절이 필요 없다는
   사실이 `0007:297-302`의 "창의 시점" 논거와 같은 자리에 기록되어야 한다.

**함수 재생성 시 옮겨야 하는 6가지 계약** (`0007:54-101`) — D-08이 단언으로 옮길 원본:
```sql
select '[1,2,3]'::extensions.vector as pgvector_warmup;   -- ⚠️ 지우면 set hnsw.*가 거부된다

create or replace function public.search_chunks(
  p_workspace_id uuid,
  p_query        extensions.vector(1536),   -- ← 1024로. 시그니처가 바뀌므로 drop 후 create
  p_k            int default 20
)
...
language sql
security invoker                       -- ⚠️ definer로 바꾸면 교차 테넌트 검색이 열린다
stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $$
  ...
  order by c.embedding operator(extensions.<=>) p_query   -- ⚠️ 연산자 수식 필수
  limit p_k;
$$;
```
⚠️ `create or replace`는 인자 타입이 바뀌면 **새 오버로드를 만든다**. `drop function public.search_chunks(uuid, extensions.vector, int)`
가 먼저 와야 하고, 그러면 `0007:386-387`의 revoke/grant도 **다시 실행해야 한다** (drop이 ACL을 함께 지운다).

**권한 방향** (`0007:373-387`) — 새 함수마다 반드시 반복:
```sql
revoke all on function public.release_job(uuid, text) from public, anon, authenticated;
grant execute on function public.release_job(uuid, text) to service_role;

-- 검색 함수만 방향이 반대입니다.
revoke all on function public.search_chunks(uuid, extensions.vector, int) from public, anon;
grant execute on function public.search_chunks(uuid, extensions.vector, int) to authenticated;
```

---

### `supabase/migrations/0009_*.sql` (`dead_letter_job` · `usage_events` · 잡 취소)

**Analog:** `0007` §3 (`complete_job_and_chain`) · §4 (`release_job`) · §8 (권한)

**락 소유자 술어를 가진 큐 함수** (`0007:212-233`) — D-03의 `dead_letter_job`이 **동형**으로 따를 형태:
```sql
create or replace function public.release_job(
  p_job_id    uuid,
  p_worker_id text
)
returns setof public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs j
  set status    = 'queued',
      attempts  = j.attempts - 1,
      locked_at = null,
      locked_by = null
  where j.id = p_job_id
    and j.status = 'running'
    and j.locked_by = p_worker_id     -- ⚠️ 이 술어가 D-03의 존재 이유
  returning j.*;
$$;

comment on function public.release_job(uuid, text) is
  '락 소유자 본인이 잡을 큐로 반납하고 ... locked_by가 다르거나 running이 아니면 0행 no-op이다. service_role 전용.';
```
→ `dead_letter_job(p_job_id, p_worker_id, p_error)`: `status = 'dead'`, `last_error = p_error`,
  `locked_at/locked_by = null` (⚠️ `jobs_lock_consistency` CHECK, `0003:65-68`), 같은 3술어 `where`.

**새 테이블(`usage_events`) 추가 시 반드시 반복할 것** (`0007:347-349`):
```sql
-- ⚠️ 이 매트릭스는 지금 존재하는 9개 테이블에만 걸립니다. 앞으로 만들 테이블은
--    pg_default_acl에서 다시 Dxtm을 물려받으므로, 테이블을 추가하는 마이그레이션은
--    자기 테이블에 대해 이 revoke/grant 쌍을 반드시 반복해야 합니다.
```
+ `0001`의 RLS 관례: 테이블 생성과 **같은 마이그레이션**에서 `enable row level security`를 켠 뒤 정책을 건다.

---

### `supabase/tests/0008_search_contract.sql` (test, SQL 계약)

**Analog:** `supabase/tests/0007_queue_functions.sql`

**헤더 + 트랜잭션 규약** (`0007_queue_functions.sql:1-19`):
```sql
-- ⚠️ 이 파일은 마이그레이션이 아닙니다. supabase/migrations/ 밖에 있으므로
--    supabase db reset이 적용하지 않으며 마이그레이션 순서에도 들어가지 않습니다.
--
-- 전체가 하나의 트랜잭션이고 마지막이 rollback이므로 픽스처 행은 남지 않습니다.
-- 남기면 jobs_dedup_idx(0007 섹션 2)가 다음 실행의 인큐를 막습니다.
--
-- 실행
--   cat supabase/tests/0007_queue_functions.sql \
--     | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
```

**단언 패턴 — `do $t0$ ... raise exception`** (`0007_queue_functions.sql:45-60`):
```sql
do $t0$
declare
  v public.jobs;
begin
  select * into v from public.claim_job('w1', array['noop']);

  if v.id is null then
    raise exception 'claim_job이 잡을 점유하지 못했습니다';
  end if;
  if v.attempts <> 1 or v.status <> 'running' or v.locked_by <> 'w1' then
    raise exception 'claim 직후 상태가 어긋났습니다 (attempts=%, status=%, locked_by=%)',
      v.attempts, v.status, v.locked_by;
  end if;
end
$t0$;
```
→ D-08의 6계약 단언은 이 형태로 `pg_proc`을 읽는다: `prosecdef = false` · `provolatile = 's'` ·
  `proconfig @> array['search_path=public','hnsw.iterative_scan=strict_order', ...]`.
  마지막 줄은 `select 'search_contract: ok';` (아래 스크립트가 grep한다).

**픽스처 고정 UUID 규약** (`:22-40`): `10000000-…` 사용자 / `20000000-…` 워크스페이스 / `30000000-…` 잡.

---

### `scripts/verify_search_contract.sh` (script, batch)

**Analog:** `scripts/verify_queue_functions.sh` — **전문이 그대로 템플릿이다**:
```bash
#!/usr/bin/env bash
set -euo pipefail

# ⚠️ ON_ERROR_STOP=1이 없으면 SQL 단언이 raise exception을 실행해도 psql이
#    성공 코드로 끝나 큐 함수 계약 회귀를 조용히 통과시킬 수 있습니다.
output="$({
  docker exec -i supabase_db_NexusWiki \
    psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f - \
    < supabase/tests/0007_queue_functions.sql
} 2>&1)"

printf '%s\n' "$output"
grep -q 'queue_functions: ok' <<< "$output"
```
→ 파일명과 grep 문자열 두 곳만 바꾼다. **`EXPLAIN`에서 `HNSW Index Scan` 확인**은
  `scripts/spike_db_transport.py`의 계획 파싱을 재사용한다 (CONTEXT `<canonical_refs>` 검증 자산).

---

### `apps/worker/src/worker/handlers/{parse,compile,link_sync,embed}.py` (handler, 각 data flow 상이)

**Analog:** `apps/worker/src/worker/handlers/noop.py` — 시그니처 계약의 유일한 실물

**전체 형태** (`noop.py:1-41`):
```python
"""부작용이 없는 성공 핸들러 — LLM 비용 0으로 큐 계약을 증명한다.

관련 태스크: P2-JOB-01
설계 근거: 02-CONTEXT.md > D-17
"""

from __future__ import annotations

from typing import Any, Final

from nexuswiki_core.logging import get_logger

__all__ = ["NOOP_JOB_TYPE", "handle_noop"]

NOOP_JOB_TYPE: Final[str] = "noop"

_logger = get_logger(__name__)


async def handle_noop(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
    ...
    _logger.info(
        "worker.noop_handled",
        job_id=job_id,
        workspace_id=workspace_id,
        payload_keys=sorted(payload),
    )
```
계약(변경 금지): **keyword-only 3인자**(`job_id` · `workspace_id` · `payload`) · `-> None` · 코루틴 ·
`workspace_id` 기본값 금지. 실패는 **예외로 던진다** — 재시도/데드레터 판정은 `queue.process_next_job`의 몫이다
(`queue.py:220-225`). 각 파일은 `<TYPE>_JOB_TYPE: Final[str]` 상수를 함께 내보내 `__init__.py`가 그것을 import한다.

⚠️ `noop.py:11-12`가 이미 명시: *"실제 파이프라인 핸들러(parse → compile → link_sync → embed, COMP-04)는
Phase 3이 `worker.handlers.HANDLERS`에 행을 더해 얹는다 — 이 파일을 고치는 것이 아니다."*

**체인 전이는 애플리케이션에서 두 번 왕복하지 않는다.** `complete_job_and_chain(p_job_id, p_next_type, p_next_payload)`
(`0007:153-187`)가 원자적 원시연산이다 — `ServiceDb`에 RPC 헬퍼로 추가하고 `queue.py`의 `db.complete_job(job_id)`
자리를 핸들러가 반환한 "다음 잡" 정보로 분기시킨다.

---

### `apps/worker/src/worker/handlers/__init__.py` (registry, 수정)

**Analog:** 자기 자신. 변경은 **딕셔너리 행 추가**로 끝나야 한다 (`__init__.py:58-61`):
```python
# 새 잡 종류는 이 딕셔너리에 행 하나를 추가하는 것으로 끝나야 한다.
HANDLERS: Final[dict[str, JobHandler]] = {NOOP_JOB_TYPE: handle_noop}
```
⚠️ `HANDLERS`가 사실상의 `jobs.type` 열거다 (`0003_jobs.sql:31-36`). `noop`은 **제거하지 않는다** —
`queue_baseline`과 `test_handlers.py`가 그것에 의존한다.

---

### `apps/worker/src/worker/{llm,embedding}.py` (service, request-response)

**Analog:** `apps/worker/src/worker/db/service.py`의 `service_client()` 팩토리 (02 D-08이 "임베딩·LLM
클라이언트도 같은 형태를 따를 것"이라고 명시) + `worker/rtt.py`의 httpx 사용법

**팩토리 패턴** (`db/service.py:40-70`) — 모듈 전역 싱글턴 금지:
```python
def service_client(
    settings: WorkerSettings,
    *,
    timeout_seconds: float = SERVICE_REQUEST_TIMEOUT_SECONDS,
) -> httpx.AsyncClient:
    """`WorkerSettings`를 인자로 받아야만 service key 클라이언트를 만든다.

    모듈 전역 싱글턴을 두지 않는다 — 두는 순간 import 부작용으로 키를 읽으려 시도하게
    되어 D-06의 인과("막히는 것은 import가 아니라 키다")가 흐려진다.
    """
    ...
    return httpx.AsyncClient(
        base_url=f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1",
        headers={"apikey": secret_key, "Authorization": f"Bearer {secret_key}", "Accept": "application/json"},
        timeout=httpx.Timeout(timeout_seconds),
    )
```
→ `openrouter_client(settings: WorkerSettings, *, timeout_seconds=...)`: `base_url="https://openrouter.ai/api/v1"`,
  `Authorization: Bearer {settings.OPENROUTER_API_KEY}`. **LLM과 임베딩이 같은 키·같은 base_url을 쓴다** (D-04).

**허용목록 상수 패턴** (`db/service.py:28-37`) — D-05의 provider 고정이 같은 형태로 산다:
```python
SERVICE_REQUEST_TIMEOUT_SECONDS: Final[float] = 10.0
TABLE_HELPERS: Final[frozenset[str]] = frozenset({"enqueue_job", "get_job", "list_jobs"})
```
→ `EMBEDDING_PROVIDER_ORDER: Final[tuple[str, ...]]` + `EMBEDDING_VERSION: Final[str]`.
  `EMBEDDING_VERSION`은 `tokenizer.TSV_TOKENIZER_VERSION = "bigram-nfkc-cf-v1"`과 **같은 규약**으로
  모델 + 실제 호스트 + 버전을 한 문자열에 인코딩한다 (D-05, 02 D-19).
  요청 본문에 `provider: {"order": [...], "allow_fallbacks": False}`를 **항상** 싣는다.

**Pydantic 3회 재시도** (`checklists.json > decisions.llm`, 신규 — 코드베이스에 analog 없음):
루프 상한을 `Final[int]`로 두고, 마지막 실패는 `sanitize_error`가 마스킹할 수 있는 자체 예외 타입으로 던진다.

---

### `apps/worker/src/worker/queue.py` (수정 — `_dead_letter` 교체 · provider 마스킹)

**Analog:** 자기 자신. 두 자리가 이미 Phase 3를 가리키고 있다.

**(1) `sanitize_error`** (`queue.py:88-100`) — COMP-08이 채울 자리가 주석으로 예약되어 있다:
```python
def sanitize_error(error: BaseException) -> str:
    """⚠️ 여기가 provider 원문 예외를 거르는 자리다. `last_error`는 워크스페이스
    멤버가 SELECT할 수 있고(0004) 프론트가 그대로 보여주므로 ... Phase 3(OPS)이 이
    함수 안에서 provider별 마스킹을 채운다.
    """
    text = f"{type(error).__name__}: {error}"
    if len(text) <= LAST_ERROR_MAX_CHARS:
        return text
    return text[: LAST_ERROR_MAX_CHARS - 1] + "…"
```

**(2) `_dead_letter`** (`queue.py:112-136`) — D-03이 대체할 인라인 한계 전문이 여기 있다:
```python
    """⚠️ 0003/0007의 함수 중 특정 잡을 한 번에 `dead`로 만드는 것은 없다. ...
    그래서 백오프를 0으로 보내 **대기 없이** 판정을 반복하게 만든다 ...
    한 번에 보내려면 `0008`에 `dead_letter_job()`이 필요하다.
    """
    row = await db.fail_job(job_id, error=reason, backoff=DEAD_LETTER_BACKOFF)
```
→ `await db.dead_letter_job(job_id, worker_id=worker_id, error=reason)` 한 줄로 대체.
  ⚠️ `QueueDb` Protocol(`queue.py:62-80`)에 시그니처를 함께 추가해야 한다 — Protocol이 이 루프가 요구하는
  계약의 실물이다. `worker_id`는 **keyword-only, 기본값 없음** (`release_job`, `db/service.py:182-191`과 동형).
  ⚠️ `_dead_letter` docstring이 "`0008`에 필요하다"고 적었으나 D-01/D-03이 `0009+`로 옮겼다 — 주석도 함께 고칠 것.

---

### `apps/worker/src/worker/db/service.py` (수정 — 도메인 테이블 헬퍼 추가)

**Analog:** 자기 자신. 클래스 docstring이 이미 이 페이즈를 지목한다 (`:83-84`):
> *"Phase 2가 실제로 쓰는 범위는 `jobs` 하나이며 도메인 테이블 헬퍼는 Phase 3의 일이다."*

**분류 계약** (`:30-37`, `:77-85`) — `apps/worker/tests/test_service_client.py`가 단언하므로
새 헬퍼는 반드시 두 집합 중 하나에 등록되어야 한다:
```python
TABLE_HELPERS: Final[frozenset[str]] = frozenset({"enqueue_job", "get_job", "list_jobs"})
QUEUE_RPC_FUNCTIONS: Final[frozenset[str]] = frozenset({"claim_job", "complete_job", "fail_job", "release_job"})
```
→ 테이블 헬퍼 추가 시 `workspace_id`는 **keyword-only, 기본값 없음** (`:73-76`의 ⚠️).
  RPC 추가 시 `complete_job_and_chain` · `dead_letter_job`을 `QUEUE_RPC_FUNCTIONS`에 넣는다.

**PostgREST 0행 함정** (`:219-228`) — 새 RPC 헬퍼도 `_rpc`를 통과시켜 이 방어를 상속할 것:
```python
        # ⚠️ `returns public.jobs` 함수(complete_job · fail_job)가 0행을 돌려주면
        #    PostgREST는 null이 아니라 **모든 필드가 null인 레코드**를 만들어 준다.
        if all(value is None for value in result.values()):
            return None
```

**INSERT 패턴** (`:195-203`) — 청크·위키 페이지 대량 삽입이 그대로 쓴다:
```python
        response = await self._client.post(
            f"/{table}", json=row, headers={"Prefer": "return=representation"}
        )
```
→ upsert가 필요한 자리(`(workspace_id, slug)` · `(raw_source_id, chunk_index)` · `(wiki_id, chunk_index)`)는
  `Prefer: resolution=merge-duplicates` + `on_conflict=` 쿼리 파라미터로 확장한다.

---

### `apps/api/src/api/routers/sources.py` · `jobs.py` (router, request-response)

**Analog:** `apps/api/src/api/routers/workspaces.py` — **전문이 템플릿이다**

**라우터 헤더 + 상태 코드 금지 규약** (`workspaces.py:25-34`):
```python
router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# ⚠️ 이 모듈에는 상태 코드 리터럴도 인라인 상태 코드 응답도 두지 않는다. ...
#    책임 분배: 격리 실패 렌더링은 `api.errors`의 단일 핸들러가, 자격증명 없는 요청은
#    아래 HTTPBearer가 맡는다. 라우터는 어느 쪽도 스스로 판정하지 않는다.
_bearer = HTTPBearer()
```
⚠️ ING-01의 **202**는 예외 상황이다 — 이 규약이 금지한 것은 "오류 상태 코드를 라우터가 판정하는 것"이므로,
성공 응답 코드는 `@router.post(..., status_code=status.HTTP_202_ACCEPTED)` 데코레이터 인자로 선언한다
(본문에 `JSONResponse(status_code=...)`를 쓰지 않는다). OPS-01의 인큐 거부도 `api.errors`에 **새 예외 타입 +
같은 단일 핸들러 등록**으로 붙인다 — 라우터에서 `raise HTTPException(...)` 금지.

**요청 모델** (`workspaces.py:39-50`):
```python
class WorkspaceUpdateRequest(BaseModel):
    """⚠️ `extra="forbid"`가 이 모델의 핵심이다. 모르는 필드를 조용히 버리면 ..."""

    model_config = ConfigDict(extra="forbid")

    # 상한 100은 `0001_core_schema.sql`의 workspaces.name CHECK와 같은 값이다.
    name: str = Field(min_length=1, max_length=100)
```
→ 인제스트 요청 모델도 `extra="forbid"`. OPS-01의 **입력 크기 상한**은 `Field(max_length=...)`로 여기 산다.

**JWT 어댑터 팩토리** (`workspaces.py:53-66`) — 인큐 라우터가 그대로 복사:
```python
def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    """⚠️ 여기에 실리는 것은 요청자 JWT이며 service key가 아니다. service key를 실으면
    BYPASSRLS라 `0004`의 격리 정책이 통째로 우회된다.
    """
    settings: ApiSettings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )
```
⚠️ **인큐도 사용자 JWT 경로다.** `jobs`에는 `authenticated`에 SELECT만 있으므로(`0007:361`), 인큐는
INSERT 권한이 없다. planner는 (a) 인큐 전용 `security definer` RPC를 `0009`에 두거나 (b) `0009`가
`jobs`에 조건부 INSERT 정책+grant를 주거나 중 하나를 **명시적으로** 선택하고 근거를 남겨야 한다 —
`service_client`를 api에 들이는 세 번째 선택지는 02 D-06이 이미 닫았다.

**핸들러 본문** (`workspaces.py:69-82`): 인자 순서 `path → body → request → credentials`, `Annotated[..., Depends(_bearer)]`,
반환은 `dict[str, Any]`, 격리 판정은 `UserDb`에 위임.

---

### `apps/api/src/api/db/user.py` (수정 — `insert_one` 추가)

**Analog:** 자기 자신의 `update_one` / `delete_one` (`:80-104`):
```python
    async def update_one(self, table: str, *, match: Mapping[str, str], values: Mapping[str, Any]) -> dict[str, Any]:
        """정확히 한 행을 갱신하고 그 행을 돌려준다. 아니면 `WorkspaceForbidden`."""
        response = await self._client.patch(
            f"{self._base_url}/{table}",
            params=_require_filters(match),
            json=dict(values),
            headers={**self._headers, "Prefer": _REPRESENTATION},
        )
        return self._exactly_one(response, table=table)
```
⚠️ `insert_one`은 `_require_filters`를 쓰지 않는다(INSERT에 match가 없다). 대신 `_exactly_one`은 그대로 쓴다 —
0행 = `WorkspaceForbidden` = 403이라는 D-11 규약이 INSERT의 `WITH CHECK` 거부에도 그대로 걸린다.
⚠️ ING-02의 `content_hash` 중복은 **23505**로 오며 이것은 격리 위반이 아니다 —
`api/errors.py:86-95`의 SQLSTATE 분기에 별도 경로를 추가하고 42501과 뭉개지 말 것.

---

### `packages/core/src/nexuswiki_core/chunking.py` (utility, transform)

**Analog:** `packages/core/src/nexuswiki_core/tokenizer.py`

**버전 상수 + 계약 주석 패턴** (`tokenizer.py:1-16`):
```python
"""색인 시점과 질의 시점이 함께 쓰는 한국어 bigram 토크나이저.

관련 태스크: P2-BE-02
설계 근거: 02-CONTEXT.md > D-19
"""

from __future__ import annotations

import unicodedata

TSV_TOKENIZER_VERSION: str = "bigram-nfkc-cf-v1"
# ⚠️ 이 상수는 문자열인데 `0002` 시점의 ... 근거: checklists.json > open_questions.
```
→ `CHUNKER_VERSION: str = "..."` (알고리즘 + 파라미터 인코딩, `0007:284-285` 컬럼 주석이 규약을 정의).
**순수 함수 · 부작용 없음 · 처리 순서를 계약으로 못 박는 docstring**(`tokenizer.py:20-28`)을 그대로 따른다.
⚠️ CONTEXT `<deferred>`가 경고: bge-m3의 8192 컨텍스트를 세는 토크나이저는 `packages/core`의 bigram 토크나이저와
**다른 것**이다. 청크 크기를 무엇으로 세는지 파일 헤더에 명시할 것.

**전제 위반 시 반환값이 아니라 예외** (`tokenizer.py:41-45`):
```python
    """⚠️ 색인 시점과 질의 시점이 서로 다른 토크나이저를 쓰면 **오류 없이 조용히
    실패**한다. ... 그래서 전제가 깨지면 반환값으로 알리지 않고 즉시 예외로 끊는다.
```
→ ING-04의 추출 품질 게이트(`needs_ocr` 판정)가 정확히 이 형태다.

---

### `apps/worker/src/worker/settings.py` · `.env.sample` (config)

**Analog:** 자기 자신 (`settings.py:16-32`):
```python
class WorkerSettings(BaseAppSettings):
    # ⚠️ 아래 네 필드의 이름을 casefold한 문자열이 `nexuswiki_core.logging`의
    # `REDACTED_KEYS` 원소와 정확히 일치해야 한다. ...
    # `packages/core/tests/test_logging_redaction.py`가 이 커플링을 단언한다.
    SUPABASE_SECRET_KEY: str
    DATABASE_URL: str
    OPENROUTER_API_KEY: str
    OPENAI_API_KEY: str     # ← D-04가 제거를 지시. 다른 소비자가 없는지 먼저 확인

    # ⚠️ 코드 기본값을 두지 않는다. ... Phase 3에서 실제 OpenRouter 슬러그를 확인하며 정리한다.
    LLM_MODEL: str
```
D-04 회수 시 함께 손댈 곳 (planner 체크리스트):
1. `WorkerSettings.OPENAI_API_KEY` 제거
2. `nexuswiki_core/logging.py`의 `REDACTED_KEYS` — ⚠️ 제거하면 커플링 테스트가 red가 된다. **먼저 테스트를 읽을 것**
3. `.env.sample` §3의 `OPENAI_API_KEY=sk-proj-…` 줄과 `# OpenAI API Key (text-embedding-3-small 1536차원 …)` 주석 (이 주석은 D-01 이후 거짓이 된다)
4. `supabase/config.toml:86`의 Studio AI `OPENAI_API_KEY` — **이것은 다른 소비자다. 제거하지 말 것**
5. Railway `worker` 서비스 env (01 D-12)

비-secret 운영 토글은 기본값을 갖는다 (`settings.py:34-42`의 `RTT_PROBE_ENABLED` / `QUEUE_BASELINE_ENABLED`)
→ OPS-01의 비용 상한 값은 이 형태로 `ApiSettings`에 들어간다.

---

### 테스트

**Analog (단위):** `apps/worker/tests/test_handlers.py` — 계약을 `inspect`로 단언하는 형태:
```python
    parameters = inspect.signature(registered).parameters
    assert set(parameters) == {"job_id", "workspace_id", "payload"}
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters.values()
    )
```
→ 새 핸들러 4종을 이 테스트의 파라미터화 대상에 넣는다 (파일을 새로 만들지 말고 확장).

**Analog (통합):** `apps/api/tests/conftest.py:28-45` — ⚠️ 로컬 스택 접속 정보를 **환경변수에서 읽지 않는다**:
```python
# ⚠️ 로컬 스택 접속 정보를 환경변수에서 읽지 않는다. 저장소 루트의 `.env.local`은
#    **클라우드** 프로젝트의 URL과 secret key를 담고 있어서, 환경을 읽는 픽스처는 그 값이
#    export 된 셸에서 실제 운영 프로젝트에 사용자와 워크스페이스를 만들고 지운다.
LOCAL_STACK: dict[str, str] = {"url": "http://127.0.0.1:54421", ...}
```
새 라우터 테스트는 이 `conftest.py`의 픽스처를 재사용한다 — 두 번째 `LOCAL_STACK` 정의를 만들지 말 것.

---

## Shared Patterns

### 1. 파일 헤더 (모든 신규 파일)
**Source:** `worker/handlers/__init__.py:1-13` · `api/errors.py:1-7` · `0007:1-32`
```python
"""<한 줄 요약 — 무엇을 보장하는가>

관련 태스크: P2-JOB-01
설계 근거: 02-CONTEXT.md > D-18
설계 근거: checklists.json > decisions.db_access, decisions.job_queue

<왜 이 형태인가 — 근거는 재서술하지 않고 키만 가리킨다>

소비자: `worker.queue.run_queue_loop`
"""
```
**Apply to:** 신규 파일 전부. 프로젝트 수명 결정은 `checklists.json > decisions.<key>`,
페이즈 한정 결정은 `03-CONTEXT.md > D-XX`. `소비자:` 줄은 태스크 ID 또는 모듈 경로로 다운스트림을 지목한다.

### 2. `⚠️` 마커
**Source:** `db/service.py:73-76` · `errors.py:30-32` · `0007:26-31`
**Apply to:** "무시하면 데이터/보안이 **오류 없이** 깨지는" 지점에만. Phase 3의 예정 위치 —
D-05(섞인 벡터) · D-08(트랜스포트 계약 누락) · COMP-08(provider 예외 노출) · 축소 재처리 잔여 행 ·
`0009`의 새 테이블 revoke/grant 누락.

### 3. 구조화 로깅 + 잡 컨텍스트 바인딩
**Source:** `worker/queue.py:25`, `:191`, `:230-231`
```python
from nexuswiki_core.logging import bind_job_context, clear_job_context, get_logger

_logger = get_logger(__name__)
...
    bind_job_context(job_id=job_id, workspace_id=workspace_id)
    try:
        _logger.info("worker.job_claimed", job_type=job_type, attempts=job.get("attempts"))
    finally:
        clear_job_context()
```
**Apply to:** 워커 핸들러 전부 — 이벤트명은 `worker.<snake_case>` / `db.<snake_case>` 도트 네임스페이스.
⚠️ 핸들러 안에서 `bind_job_context`를 다시 부르지 않는다 — 큐 루프가 이미 감싸고 있다.
⚠️ LLM/임베딩 응답 본문을 로그 필드로 싣지 않는다 (`REDACTED_KEYS`는 필드명만 마스킹한다).

### 4. 오류 → HTTP 매핑 단일 지점
**Source:** `apps/api/src/api/errors.py:98-108`
```python
def register_error_handlers(app: FastAPI) -> None:
    """⚠️ 호출 지점은 `api.main.create_app` 한 곳뿐이다. 라우터가 스스로 상태 코드를 정하기
    시작하면 D-12의 "존재 여부를 구분하지 않는다"가 라우터마다 다시 결정된다.
    """
    handler: Any = _render_isolation_failure
    app.add_exception_handler(WorkspaceForbidden, handler)
    app.add_exception_handler(DatabaseError, handler)
```
**Apply to:** OPS-01의 인큐 거부 · ING-02의 중복 응답 · ING-04의 추출 게이트 실패.
새 예외 타입을 만들고 이 함수에 등록한다. 라우터에 상태 코드를 흘리지 않는다.

### 5. 커밋
**Source:** CLAUDE.md + `git log`. `type(scope): <migration number or subject> — <구체적으로 무엇이 바뀌었나>`.
마이그레이션은 번호로 시작 (`feat(db): 0008 — …`, D-09). 한 태스크 = 한 커밋. 한국어.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `worker/llm.py`의 Pydantic 3회 재시도 루프 | service | request-response | 저장소에 LLM 호출이 아직 0건. 계약은 `checklists.json > decisions.llm`에만 있다. `worker/rtt.py`가 httpx 재시도 없는 루프의 유일한 참고이며 재시도 정책은 신규 설계 |
| `worker/extract.py` (PDF `pypdf` · URL 페치) | utility | file-I/O | 저장소에 파일 I/O 코드가 전혀 없다. Storage 경로 규약만 `0005`가 강제 |
| Storage 업로드 경로 (`{workspace_id}/{raw_source_id}/{filename}`) | service | file-I/O | `UserDb`/`ServiceDb` 둘 다 PostgREST 전용이며 Storage API 클라이언트가 없다. `scripts/verify_storage_policies.sh`가 경로 규약의 유일한 실물 |

이 3건은 RESEARCH.md가 없으므로 planner가 `.planning/research/EMBEDDING.md`와 공급자 문서를 근거로
직접 설계하고, **설계 근거를 파일 헤더에 남길 것**.

---

## Metadata

**Analog search scope:** `apps/api/src/api/`, `apps/worker/src/worker/`, `packages/core/src/nexuswiki_core/`,
`supabase/migrations/`, `supabase/tests/`, `scripts/`, `apps/*/tests/`
**Files scanned:** 46 Python/TOML + `0007` 마이그레이션 + SQL 계약 러너 + verify 스크립트
**Pattern extraction date:** 2026-08-07
