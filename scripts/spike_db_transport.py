"""DB 트랜스포트 스파이크 러너 — RPC/asyncpg 두 경로를 같은 기준으로 실측한다.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-01 (EXPLAIN 계획 + 실제 반환 행 수로 판정)
           02-CONTEXT.md > D-02 (고정 시드 합성 코퍼스, 적대적 분포)
           02-CONTEXT.md > D-03 (GUC 3종 · HNSW Index Scan · k행, 셋 다여야 RPC)

이 스크립트는 스파이크용 일회성 도구가 아니다. EXPLAIN 계획을 파싱해 인덱스 사용을
단언하는 부분이 Phase 4 RTV-08 회귀 테스트의 원형이다.

실행
    export SPIKE_USER_PASSWORD='...'
    uv run --with httpx python scripts/spike_db_transport.py --transport rpc --k 20 --repeat 3
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import random
import subprocess
import sys
import time
from dataclasses import asdict, dataclass

import httpx

# 코퍼스 계약. supabase/spike/0001_transport_corpus.sql 의 기본값과 같은 값이어야 하며,
# 어긋나면 러너가 판정하는 코퍼스와 적재된 코퍼스가 달라진다.
SPIKE_CORPUS_TOTAL_ROWS: int = 50000
SPIKE_CORPUS_TARGET_ROWS: int = 750
SPIKE_CORPUS_SEED: float = 0.4242
SPIKE_K: int = 20

SPIKE_EMBEDDING_DIM: int = 1536
SPIKE_QUERY_SEED: int = 20260806
SPIKE_USER_EMAIL: str = "spike-owner@nexuswiki.local"
SPIKE_TARGET_WORKSPACE_ID: str = "b0000000-0000-4000-8000-000000000001"
SPIKE_HNSW_INDEX_NAME: str = "source_chunks_embedding_idx"

# D-03 판정 조건 1. 함수 정의(RPC)나 set local(asyncpg)로 세 값이 전부 살아 있어야 한다.
EXPECTED_GUCS: dict[str, str] = {
    "iterative_scan": "strict_order",
    "ef_search": "200",
    "max_scan_tuples": "40000",
}

DEFAULT_SUPABASE_URL: str = "http://127.0.0.1:54421"
REQUEST_TIMEOUT_SECONDS: float = 120.0


@dataclass(frozen=True)
class SpikeRunResult:
    """한 번의 실행에서 관측한 D-03 판정 3조건의 원자료."""

    transport: str
    iteration: int
    iterative_scan: str | None
    ef_search: str | None
    max_scan_tuples: str | None
    has_hnsw_index_scan: bool
    returned_rows: int
    elapsed_ms: float


# -----------------------------------------------------------------------------
# 설정 해석 — 자격증명은 CLI 인자 · 환경변수 · 로컬 스택 조회로만 얻는다 (T-02-01)
# -----------------------------------------------------------------------------
_local_stack_cache: dict[str, str] | None = None


def _local_stack() -> dict[str, str]:
    """`supabase status -o json` 으로 로컬 스택 접속 정보를 읽는다."""
    global _local_stack_cache
    if _local_stack_cache is None:
        try:
            completed = subprocess.run(  # noqa: S603
                ["supabase", "status", "-o", "json"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            _local_stack_cache = json.loads(completed.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            _local_stack_cache = {}
    return _local_stack_cache


def _resolve(cli_value: str | None, env_key: str, status_key: str, fallback: str = "") -> str:
    if cli_value:
        return cli_value
    if os.environ.get(env_key):
        return os.environ[env_key]
    return _local_stack().get(status_key, fallback)


def _require(value: str, what: str) -> str:
    if not value:
        raise SystemExit(f"설정 누락: {what} 를 결정할 수 없다. CLI 인자나 환경변수로 넘길 것.")
    return value


# -----------------------------------------------------------------------------
# 질의 벡터와 요청자 JWT
# -----------------------------------------------------------------------------
def query_vector() -> list[float]:
    """고정 시드로 만든 질의 벡터. 반복 실행이 같은 질의를 보게 한다."""
    rng = random.Random(SPIKE_QUERY_SEED)  # noqa: S311
    return [rng.random() for _ in range(SPIKE_EMBEDDING_DIM)]


def fetch_jwt(
    client: httpx.Client,
    *,
    supabase_url: str,
    anon_key: str,
    email: str,
    password: str,
) -> str:
    """GoTrue password grant 로 요청자 JWT를 받는다."""
    response = client.post(
        f"{supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
    )
    if not response.is_success:
        raise SystemExit(
            f"JWT 발급 실패({response.status_code}): {response.text[:200]}\n"
            "코퍼스 SQL(0001)을 같은 SPIKE_USER_PASSWORD 로 먼저 적재했는지 확인할 것."
        )
    return response.json()["access_token"]


def jwt_claims(token: str) -> dict[str, object]:
    """서명 검증 없이 payload 만 디코딩한다 (asyncpg 경로의 request.jwt.claims 원본)."""
    payload = token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


# -----------------------------------------------------------------------------
# EXPLAIN 계획 파싱 — Phase 4 RTV-08 회귀 테스트의 원형
# -----------------------------------------------------------------------------
def walk_plan(node: object) -> list[dict[str, object]]:
    """계획 트리를 재귀 순회해 모든 노드를 평탄화한다."""
    nodes: list[dict[str, object]] = []
    if isinstance(node, list):
        for item in node:
            nodes.extend(walk_plan(item))
    elif isinstance(node, dict):
        if "Node Type" in node:
            nodes.append(node)
        for value in node.values():
            if isinstance(value, list | dict):
                nodes.extend(walk_plan(value))
    return nodes


def has_hnsw_index_scan(plan: object) -> bool:
    """HNSW 인덱스를 실제로 스캔했는지.

    ⚠️ 노드 타입이 'Index Scan' 인 것만 보면 workspace_id btree 스캔도 통과한다.
    그 오탐이 바로 D-01이 막으려는 것 — 계획이 인덱스를 썼다는 사실과 *그* 인덱스를
    썼다는 사실은 다르다. 인덱스 이름까지 일치시킨다.
    """
    for node in walk_plan(plan):
        node_type = str(node.get("Node Type", ""))
        index_name = str(node.get("Index Name", ""))
        if "Index Scan" in node_type and index_name == SPIKE_HNSW_INDEX_NAME:
            return True
    return False


# -----------------------------------------------------------------------------
# 경로 1: RPC (SECURITY INVOKER 함수 + 요청자 JWT)
# -----------------------------------------------------------------------------
def run_rpc(
    client: httpx.Client,
    *,
    supabase_url: str,
    anon_key: str,
    jwt: str,
    workspace_id: str,
    vector: list[float],
    k: int,
    iteration: int,
    forced_hnsw: bool = False,
) -> SpikeRunResult:
    function = "spike_explain_search_chunks"
    if forced_hnsw:
        function = "spike_explain_search_chunks_forced"
    started = time.perf_counter()
    response = client.post(
        f"{supabase_url.rstrip('/')}/rest/v1/rpc/{function}",
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
        },
        json={"p_workspace_id": workspace_id, "p_query": vector, "p_k": k},
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if not response.is_success:
        raise SystemExit(f"RPC 실패({response.status_code}): {response.text[:300]}")

    observed = response.json()
    return SpikeRunResult(
        transport="rpc",
        iteration=iteration,
        iterative_scan=observed.get("iterative_scan"),
        ef_search=observed.get("ef_search"),
        max_scan_tuples=observed.get("max_scan_tuples"),
        has_hnsw_index_scan=has_hnsw_index_scan(observed.get("plan")),
        returned_rows=int(observed.get("returned_rows", 0)),
        elapsed_ms=elapsed_ms,
    )


# -----------------------------------------------------------------------------
# 경로 2: asyncpg 세션 직결
#
# SPEC R6은 "asyncpg + Supavisor session mode"를 요구하지만 로컬 스택은 pooler가
# 비활성이다(config.toml 54429). 직접 연결은 세션 단위 연결이므로 set local GUC
# 의미론에 관한 한 session mode와 동등하다. 이탈 근거는 결과 문서의 방법 절에 남긴다.
# -----------------------------------------------------------------------------
def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.17g}" for value in vector) + "]"


async def run_asyncpg(
    *,
    database_url: str,
    claims: dict[str, object],
    workspace_id: str,
    vector: list[float],
    k: int,
    iteration: int,
    forced_hnsw: bool = False,
) -> SpikeRunResult:
    import asyncpg

    literal = vector_literal(vector)
    # EXPLAIN 은 유틸리티 문이라 바인드 파라미터를 받지 못한다. 스파이크가 스스로 만든
    # 합성 값만 조립하며 외부 입력은 이 경로에 들어오지 않는다.
    search_sql = (
        "select c.id, c.chunk_index"  # noqa: S608
        " from public.source_chunks c"
        f" where c.workspace_id = '{workspace_id}'::uuid"
        "   and c.embedding is not null"
        f" order by c.embedding operator(extensions.<=>) '{literal}'::extensions.vector(1536)"
        f" limit {k}"
    )

    # ⚠️ 작은따옴표가 섞이면 문 자체가 깨진다. GoTrue claims 에는 없지만, 이 경로는
    #    문자열 조립이 유일한 수단이므로 방어를 생략하지 않는다.
    claims_json = json.dumps(claims, separators=(",", ":")).replace("'", "''")

    connection = await asyncpg.connect(database_url)
    try:
        started = time.perf_counter()
        transaction = connection.transaction()
        await transaction.start()
        try:
            # hnsw.* GUC는 vector.so 가 이 백엔드에 적재된 뒤에야 정식 등록된다.
            await connection.fetchval("select '[1,2,3]'::extensions.vector")

            await connection.execute("set local hnsw.iterative_scan = 'strict_order'")
            await connection.execute("set local hnsw.ef_search = '200'")
            await connection.execute("set local hnsw.max_scan_tuples = '40000'")
            if forced_hnsw:
                # 진단 전용. 정렬 경로를 막아 플래너가 HNSW를 고르게 만든 뒤,
                # GUC가 실제 HNSW 스캔까지 도달하는지를 따로 관측한다.
                await connection.execute("set local enable_sort = off")

            # ⚠️ 아래 두 문장 중 하나라도 빠지면 auth.uid() 가 값을 보지 못해 RLS 정책이
            #    아무도 막지 않는 상태가 된다. 예외는 나지 않고 격리만 조용히 풀린다 —
            #    실패가 눈에 보이지 않는다는 것이 이 경로의 진짜 비용이다.
            #    근거: 02-CONTEXT.md > D-04.
            await connection.execute(f"set local request.jwt.claims = '{claims_json}'")
            await connection.execute("set local role authenticated")

            observed = await connection.fetchrow(
                "select current_setting('hnsw.iterative_scan', true)  as iterative_scan,"
                "       current_setting('hnsw.ef_search', true)       as ef_search,"
                "       current_setting('hnsw.max_scan_tuples', true) as max_scan_tuples"
            )
            plan_json = await connection.fetchval(
                f"explain (analyze, buffers, format json) {search_sql}"
            )
            rows = await connection.fetch(search_sql)
        finally:
            # 판정만 하고 아무것도 남기지 않는다.
            await transaction.rollback()
        elapsed_ms = (time.perf_counter() - started) * 1000
    finally:
        await connection.close()

    return SpikeRunResult(
        transport="asyncpg",
        iteration=iteration,
        iterative_scan=observed["iterative_scan"],
        ef_search=observed["ef_search"],
        max_scan_tuples=observed["max_scan_tuples"],
        has_hnsw_index_scan=has_hnsw_index_scan(json.loads(plan_json)),
        returned_rows=len(rows),
        elapsed_ms=elapsed_ms,
    )


# -----------------------------------------------------------------------------
# 판정
# -----------------------------------------------------------------------------
def conditions(result: SpikeRunResult, *, k: int) -> dict[str, bool]:
    """D-03 3조건을 개별 참/거짓으로 돌려준다. 부분 충족을 통과로 접지 않는다."""
    return {
        "gucs_applied": (
            result.iterative_scan == EXPECTED_GUCS["iterative_scan"]
            and result.ef_search == EXPECTED_GUCS["ef_search"]
            and result.max_scan_tuples == EXPECTED_GUCS["max_scan_tuples"]
        ),
        "hnsw_index_scan": result.has_hnsw_index_scan,
        "k_rows_returned": result.returned_rows == k,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DB 트랜스포트 스파이크 러너")
    parser.add_argument("--transport", choices=["rpc", "asyncpg"], required=True)
    parser.add_argument("--k", type=int, default=SPIKE_K)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--supabase-url", default=None)
    parser.add_argument("--anon-key", default=None)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--email", default=SPIKE_USER_EMAIL)
    parser.add_argument("--password", default=None)
    parser.add_argument("--workspace-id", default=SPIKE_TARGET_WORKSPACE_ID)
    parser.add_argument(
        "--forced-hnsw",
        action="store_true",
        help="정렬 경로를 막아 HNSW를 강제한다(진단 전용, 판정 조건 2의 원인 분리)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    supabase_url = _require(
        _resolve(args.supabase_url, "SUPABASE_URL", "API_URL", DEFAULT_SUPABASE_URL),
        "SUPABASE_URL",
    )
    anon_key = _require(
        _resolve(args.anon_key, "SUPABASE_PUBLISHABLE_KEY", "PUBLISHABLE_KEY"),
        "SUPABASE_PUBLISHABLE_KEY",
    )
    password = _require(
        args.password or os.environ.get("SPIKE_USER_PASSWORD", ""),
        "SPIKE_USER_PASSWORD",
    )

    vector = query_vector()
    results: list[SpikeRunResult] = []

    with httpx.Client(timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS)) as client:
        jwt = fetch_jwt(
            client,
            supabase_url=supabase_url,
            anon_key=anon_key,
            email=args.email,
            password=password,
        )

        for iteration in range(1, args.repeat + 1):
            if args.transport == "rpc":
                result = run_rpc(
                    client,
                    supabase_url=supabase_url,
                    anon_key=anon_key,
                    jwt=jwt,
                    workspace_id=args.workspace_id,
                    vector=vector,
                    k=args.k,
                    iteration=iteration,
                    forced_hnsw=args.forced_hnsw,
                )
            else:
                database_url = _require(
                    _resolve(args.database_url, "DATABASE_URL", "DB_URL"),
                    "DATABASE_URL",
                )
                result = asyncio.run(
                    run_asyncpg(
                        database_url=database_url,
                        claims=jwt_claims(jwt),
                        workspace_id=args.workspace_id,
                        vector=vector,
                        k=args.k,
                        iteration=iteration,
                        forced_hnsw=args.forced_hnsw,
                    )
                )
            results.append(result)
            observed = {**asdict(result), **conditions(result, k=args.k)}
            print(json.dumps(observed, ensure_ascii=False))

    verdicts = {tuple(sorted(conditions(r, k=args.k).items())) for r in results}
    if len(verdicts) > 1:
        print(
            json.dumps(
                {
                    "consistent": False,
                    "reason": "반복 회차 간 판정 불일치 — 흔들리는 판정을 통과로 적을 수 없다.",
                    "verdicts": [dict(v) for v in verdicts],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    final = conditions(results[-1], k=args.k)
    print(
        json.dumps(
            {
                "transport": args.transport,
                "repeat": args.repeat,
                "k": args.k,
                "consistent": True,
                "conditions": final,
                "all_conditions_met": all(final.values()),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
