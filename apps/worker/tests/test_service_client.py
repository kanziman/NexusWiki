"""service key 팩토리의 인자 강제와 ServiceDb의 workspace 스코프 강제 회귀 테스트."""

import importlib
import inspect
import json
from typing import Any

import httpx
import pytest

from worker.db import service
from worker.settings import WorkerSettings

# 02-02가 고정한 worker env 전량. 값이 아니라 "필드가 존재한다"가 이 테스트의 관심사다.
COMPLETE_WORKER_ENV = {
    "SUPABASE_URL": "https://example.invalid",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
    "SUPABASE_SECRET_KEY": "sb_secret_test",
    "DATABASE_URL": "postgresql://postgres:pw@127.0.0.1:54422/postgres",
    "OPENROUTER_API_KEY": "sk-or-v1-test",
    "LLM_MODEL": "anthropic/claude-sonnet-4.6",
}

WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
JOB_ID = "22222222-2222-4222-8222-222222222222"


def build_worker_settings() -> WorkerSettings:
    return WorkerSettings(**COMPLETE_WORKER_ENV)


def build_api_settings() -> Any:
    from api.settings import ApiSettings

    return ApiSettings(
        SUPABASE_URL=COMPLETE_WORKER_ENV["SUPABASE_URL"],
        SUPABASE_PUBLISHABLE_KEY=COMPLETE_WORKER_ENV["SUPABASE_PUBLISHABLE_KEY"],
    )


def client_returning(
    payload: Any,
    *,
    status: int = 200,
    seen: list[httpx.Request] | None = None,
) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://example.invalid/rest/v1",
    )


# -----------------------------------------------------------------------------
# 1. 팩토리 — 인자 없이는 만들어지지 않는다 (02-CONTEXT.md > D-08)
# -----------------------------------------------------------------------------


def test_service_client_refuses_to_build_without_settings() -> None:
    with pytest.raises(TypeError):
        service.service_client()  # type: ignore[call-arg]


def test_service_client_takes_settings_as_its_first_parameter() -> None:
    parameters = list(inspect.signature(service.service_client).parameters)

    assert parameters[0] == "settings"


def test_service_client_rejects_api_settings_and_names_the_missing_key() -> None:
    # ⚠️ api 프로세스에는 이 필드가 존재하지 않는다. 그것이 SEC-01의 집행 지점이며
    # 이 거부는 그 사실의 표면이지 방어선 자체가 아니다 (02-CONTEXT.md > D-06).
    with pytest.raises(TypeError) as excinfo:
        service.service_client(build_api_settings())

    assert "SUPABASE_SECRET_KEY" in str(excinfo.value)


@pytest.mark.asyncio
async def test_service_client_builds_a_client_carrying_the_secret_key() -> None:
    async with service.service_client(build_worker_settings()) as client:
        assert client.headers["apikey"] == COMPLETE_WORKER_ENV["SUPABASE_SECRET_KEY"]
        assert COMPLETE_WORKER_ENV["SUPABASE_SECRET_KEY"] in client.headers["authorization"]
        assert str(client.base_url).startswith(COMPLETE_WORKER_ENV["SUPABASE_URL"])


def test_importing_the_module_reads_no_credentials_and_holds_no_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in COMPLETE_WORKER_ENV:
        monkeypatch.delenv(key, raising=False)

    reloaded = importlib.reload(service)

    module_level_clients = [
        name
        for name, value in vars(reloaded).items()
        if not name.startswith("_") and isinstance(value, httpx.AsyncClient | httpx.Client)
    ]
    assert module_level_clients == []


# -----------------------------------------------------------------------------
# 2. ServiceDb — service_role은 BYPASSRLS이므로 workspace_id가 유일한 격리 수단
# -----------------------------------------------------------------------------


def test_every_public_helper_is_classified_as_table_or_approved_rpc() -> None:
    # 새 헬퍼가 분류를 빠져나가면 workspace 스코프 강제가 조용히 뚫린다.
    public_helpers = {
        name
        for name, value in vars(service.ServiceDb).items()
        if not name.startswith("_") and inspect.isfunction(value)
    }

    assert public_helpers == service.TABLE_HELPERS | service.RPC_HELPERS
    assert service.RPC_HELPERS == (
        service.QUEUE_RPC_FUNCTIONS
        | service.CATALOG_RPC_FUNCTIONS
        | service.LEXICAL_RPC_FUNCTIONS
        | service.CONFLICT_RPC_FUNCTIONS
        | service.BUDGET_RPC_FUNCTIONS
    )
    assert not (service.TABLE_HELPERS & service.QUEUE_RPC_FUNCTIONS)
    assert not (service.TABLE_HELPERS & service.CATALOG_RPC_FUNCTIONS)
    assert not (service.QUEUE_RPC_FUNCTIONS & service.CATALOG_RPC_FUNCTIONS)
    assert not (service.TABLE_HELPERS & service.CONFLICT_RPC_FUNCTIONS)
    assert not (service.TABLE_HELPERS & service.BUDGET_RPC_FUNCTIONS)
    assert not (service.BUDGET_RPC_FUNCTIONS & service.QUEUE_RPC_FUNCTIONS)


def test_table_helpers_declare_workspace_id_without_a_default() -> None:
    for name in service.TABLE_HELPERS:
        parameter = inspect.signature(getattr(service.ServiceDb, name)).parameters.get(
            "workspace_id"
        )

        assert parameter is not None, name
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert parameter.default is inspect.Parameter.empty, name


def test_plan_03_09_domain_helpers_remain_explicitly_classified() -> None:
    """링크·임베딩 경로가 분류 규약을 우회하지 않게 한다 (03-09 Task 3)."""
    assert {
        "list_wiki_links",
        "upsert_wiki_links",
        "delete_wiki_links_not_in",
        "resolve_red_links",
        "list_source_chunks_missing_embedding",
        "update_source_chunk_embedding",
        "upsert_wiki_embeddings",
        "delete_wiki_embeddings_from",
    } <= service.TABLE_HELPERS


@pytest.mark.asyncio
async def test_scoped_helpers_reject_missing_workspace_id() -> None:
    async with client_returning([]) as client:
        db = service.ServiceDb(client)

        with pytest.raises(TypeError):
            await db.get_job(JOB_ID)  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            await db.list_jobs()  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_scoped_helpers_accept_workspace_id() -> None:
    seen: list[httpx.Request] = []
    row = {"id": JOB_ID, "workspace_id": WORKSPACE_ID}
    async with client_returning([row], seen=seen) as client:
        db = service.ServiceDb(client)

        job = await db.get_job(JOB_ID, workspace_id=WORKSPACE_ID)
        jobs = await db.list_jobs(workspace_id=WORKSPACE_ID)

    assert job is not None and job["id"] == JOB_ID
    assert jobs == [{"id": JOB_ID, "workspace_id": WORKSPACE_ID}]
    assert len(seen) == 2
    for request in seen:
        assert request.url.params["workspace_id"] == f"eq.{WORKSPACE_ID}"


@pytest.mark.asyncio
async def test_queue_rpc_helpers_post_to_their_own_function_path() -> None:
    seen: list[httpx.Request] = []
    async with client_returning([{"id": JOB_ID}], seen=seen) as client:
        db = service.ServiceDb(client)

        await db.claim_job(worker_id="worker-1", types=["noop"])
        await db.complete_job(JOB_ID)
        await db.fail_job(JOB_ID, error="boom")
        await db.release_job(JOB_ID, worker_id="worker-1")
        await db.complete_job_and_chain(JOB_ID, next_type="compile")
        await db.dead_letter_job(JOB_ID, worker_id="worker-1", error="dead")
        await db.cancel_job(JOB_ID, worker_id="worker-1")
        await db.reap_stale_jobs(timeout="900 seconds")

    called = [request.url.path.rsplit("/", 1)[-1] for request in seen]
    assert called == [
        "claim_job",
        "complete_job",
        "fail_job",
        "release_job",
        "complete_job_and_chain",
        "dead_letter_job",
        "cancel_job",
        "reap_stale_jobs",
    ]
    # ⚠️ 이 단언은 큐 RPC 헬퍼를 하나 더할 때마다 **의도적으로 red가 된다.** 허용 목록에만
    #    이름을 넣고 실제 호출 경로를 확인하지 않으면 그 헬퍼는 검증되지 않은 채 통과한다.
    assert set(called) == service.QUEUE_RPC_FUNCTIONS
    assert all(request.method == "POST" for request in seen)


@pytest.mark.asyncio
async def test_conflict_candidate_rpc_posts_its_bounded_similarity_arguments() -> None:
    seen: list[httpx.Request] = []
    candidates = [{"candidate_wiki_id": "candidate-1", "similarity": 0.93}]
    async with client_returning(candidates, seen=seen) as client:
        db = service.ServiceDb(client)
        rows = await db.find_similar_wiki_pages(
            workspace_id=WORKSPACE_ID, wiki_id="wiki-1", similarity_threshold=0.91, limit=3
        )

    assert rows == candidates
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path.endswith("/rpc/find_similar_wiki_pages")
    assert json.loads(request.content) == {
        "p_workspace_id": WORKSPACE_ID,
        "p_wiki_id": "wiki-1",
        "p_similarity_threshold": 0.91,
        "p_limit": 3,
    }


@pytest.mark.asyncio
async def test_set_wiki_page_disputed_writes_only_dispute_state() -> None:
    seen: list[httpx.Request] = []
    row = {"id": "wiki-1", "disputed": True, "verification_status": "disputed"}
    async with client_returning([row], seen=seen) as client:
        db = service.ServiceDb(client)
        result = await db.set_wiki_page_disputed("wiki-1", workspace_id=WORKSPACE_ID)

    assert result == row
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "PATCH"
    assert request.url.path.endswith("/wiki_pages")
    assert request.url.params["id"] == "eq.wiki-1"
    assert request.url.params["workspace_id"] == f"eq.{WORKSPACE_ID}"
    assert json.loads(request.content) == {"disputed": True, "verification_status": "disputed"}


@pytest.mark.asyncio
async def test_domain_table_helpers_carry_an_explicit_workspace_filter() -> None:
    # ⚠️ 복합 FK가 잡아 주는 것은 **삽입**이지 조회가 아니다. service_role은 BYPASSRLS라
    #    조회 파라미터에서 workspace_id가 빠지면 오류 없이 다른 테넌트의 행이 돌아온다.
    seen: list[httpx.Request] = []
    row = {"id": "abc", "workspace_id": WORKSPACE_ID, "slug": "s", "sources": []}
    async with client_returning([row], seen=seen) as client:
        db = service.ServiceDb(client)

        await db.get_raw_source("rs", workspace_id=WORKSPACE_ID)
        await db.list_source_chunks(workspace_id=WORKSPACE_ID, raw_source_id="rs")
        await db.delete_source_chunks_from(
            workspace_id=WORKSPACE_ID, raw_source_id="rs", from_index=3
        )
        await db.list_wiki_slugs(workspace_id=WORKSPACE_ID)
        await db.get_wiki_page_by_slug(workspace_id=WORKSPACE_ID, slug="s")
        await db.list_wiki_pages_for_source(workspace_id=WORKSPACE_ID, raw_source_id="rs")

    assert len(seen) == 6
    for request in seen:
        assert request.url.params["workspace_id"] == f"eq.{WORKSPACE_ID}", request.url


@pytest.mark.asyncio
async def test_upserts_declare_their_conflict_target_and_merge_resolution() -> None:
    # `resolution=merge-duplicates`가 없으면 재처리가 409로 돌아오고, at-least-once
    # 큐에서 재처리는 정상 경로이므로 그 409는 곧 잡 실패다.
    seen: list[httpx.Request] = []
    async with client_returning([{"id": "abc"}], seen=seen) as client:
        db = service.ServiceDb(client)

        await db.upsert_source_chunks(
            workspace_id=WORKSPACE_ID,
            raw_source_id="rs",
            rows=[{"chunk_index": 0, "content": "본문", "char_start": 0, "char_end": 2}],
        )
        await db.upsert_wiki_page(workspace_id=WORKSPACE_ID, row={"slug": "s", "title": "제목"})

    assert seen[0].url.params["on_conflict"] == "raw_source_id,chunk_index"
    assert seen[1].url.params["on_conflict"] == "workspace_id,slug"
    for request in seen:
        assert "merge-duplicates" in request.headers["Prefer"]


@pytest.mark.asyncio
async def test_chunk_rows_always_receive_the_scope_the_caller_declared() -> None:
    # 호출부가 행마다 workspace_id를 적어 넣는 형태였다면 한 행만 빠뜨려도 조용히
    # 통과한다. 스코프는 헬퍼가 **전 행에** 덮어쓴다.
    seen: list[httpx.Request] = []
    async with client_returning([], seen=seen) as client:
        db = service.ServiceDb(client)

        await db.upsert_source_chunks(
            workspace_id=WORKSPACE_ID,
            raw_source_id="rs",
            rows=[{"chunk_index": index} for index in range(3)],
        )

    body = json.loads(seen[0].content)
    assert len(body) == 3
    assert all(row["workspace_id"] == WORKSPACE_ID and row["raw_source_id"] == "rs" for row in body)


@pytest.mark.asyncio
async def test_prompt_template_lookup_falls_back_from_workspace_to_global() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        # 첫 조회(워크스페이스)는 비고, 두 번째(전역)가 응답한다.
        payload = [] if len(seen) == 1 else [{"id": "tpl", "template": "t"}]
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.invalid/rest/v1"
    ) as client:
        db = service.ServiceDb(client)

        template = await db.get_default_prompt_template(
            workspace_id=WORKSPACE_ID, target_type="compile"
        )

    assert template is not None and template["id"] == "tpl"
    assert seen[0].url.params["workspace_id"] == f"eq.{WORKSPACE_ID}"
    assert seen[1].url.params["workspace_id"] == "is.null"


@pytest.mark.asyncio
async def test_workspace_budget_helpers_read_the_cap_and_sum_usage_since() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/workspaces"):
            return httpx.Response(200, json=[{"monthly_budget_micros": 250}])
        return httpx.Response(200, json={"sum_usage_events_since": 1001})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.invalid/rest/v1"
    ) as client:
        db = service.ServiceDb(client)
        cap = await db.get_workspace_budget_cap(workspace_id=WORKSPACE_ID)
        spent = await db.sum_usage_events_since(
            workspace_id=WORKSPACE_ID, since="2026-08-01T00:00:00+00:00"
        )

    assert cap == 250
    assert spent == 1001
    assert dict(seen[0].url.params) == {
        "id": f"eq.{WORKSPACE_ID}",
        "select": "monthly_budget_micros",
        "limit": "1",
    }
    assert seen[1].method == "POST"
    assert seen[1].url.path.endswith("/rpc/sum_usage_events_since")
    assert json.loads(seen[1].content) == {
        "p_workspace_id": WORKSPACE_ID,
        "p_since": "2026-08-01T00:00:00+00:00",
    }
    assert all(not request.url.path.endswith("/usage_events") for request in seen)


@pytest.mark.asyncio
async def test_workspace_budget_helpers_distinguish_no_cap_from_zero_spend() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.invalid/rest/v1"
    ) as client:
        db = service.ServiceDb(client)
        cap = await db.get_workspace_budget_cap(workspace_id=WORKSPACE_ID)
        spent = await db.sum_usage_events_since(
            workspace_id=WORKSPACE_ID, since="2026-08-01T00:00:00+00:00"
        )

    assert cap is None
    assert spent == 0


@pytest.mark.asyncio
async def test_usage_aggregate_accepts_scalar_and_rejects_unexpected_shape() -> None:
    async with client_returning(1001) as client:
        db = service.ServiceDb(client)
        assert (
            await db.sum_usage_events_since(
                workspace_id=WORKSPACE_ID, since="2026-08-01T00:00:00+00:00"
            )
            == 1001
        )

    async with client_returning({"unexpected": 1, "also_unexpected": 2}) as client:
        db = service.ServiceDb(client)
        with pytest.raises(ValueError, match="unexpected sum_usage_events_since result"):
            await db.sum_usage_events_since(
                workspace_id=WORKSPACE_ID, since="2026-08-01T00:00:00+00:00"
            )


@pytest.mark.asyncio
async def test_complete_job_and_chain_posts_the_next_step_in_one_call() -> None:
    # ⚠️ 완료와 다음 잡 인큐가 두 왕복으로 갈라지면 그 틈에서 죽었을 때 파이프라인이
    #    조용히 멈춘다 (0007 섹션 3).
    seen: list[httpx.Request] = []
    async with client_returning([{"id": JOB_ID}], seen=seen) as client:
        db = service.ServiceDb(client)

        await db.complete_job_and_chain(
            JOB_ID, next_type="compile", next_payload={"target_id": "rs"}
        )
        await db.complete_job_and_chain(JOB_ID)

    assert seen[0].url.path.endswith("/rpc/complete_job_and_chain")
    chained = json.loads(seen[0].content)
    assert chained["p_next_type"] == "compile"
    assert chained["p_next_payload"] == {"target_id": "rs"}
    # 다음 잡이 없으면 인자를 아예 싣지 않는다 — 기본값 null이 DB 쪽 계약이다.
    assert "p_next_type" not in json.loads(seen[1].content)


@pytest.mark.asyncio
async def test_all_null_record_from_a_zero_row_composite_function_becomes_none() -> None:
    # ⚠️ `returns public.jobs` 함수가 0행이면 PostgREST는 null이 아니라 모든 필드가
    #    null인 레코드를 만들어 준다. 그대로 돌려주면 `if row:` 가 no-op을 성공으로
    #    읽고, at-least-once 큐에서 그것은 "두 번 처리해서 두 번 다 성공"으로 기록된다.
    empty_record = {"id": None, "workspace_id": None, "status": None, "attempts": None}
    async with client_returning(empty_record) as client:
        db = service.ServiceDb(client)

        assert await db.complete_job(JOB_ID) is None
        assert await db.fail_job(JOB_ID, error="boom") is None


@pytest.mark.asyncio
async def test_a_real_row_survives_the_zero_row_normalisation() -> None:
    async with client_returning({"id": JOB_ID, "status": "succeeded", "locked_by": None}) as client:
        db = service.ServiceDb(client)

        row = await db.complete_job(JOB_ID)

    assert row is not None and row["id"] == JOB_ID


@pytest.mark.asyncio
async def test_failed_response_raises_instead_of_returning_an_empty_result() -> None:
    async with client_returning({"message": "nope"}, status=500) as client:
        db = service.ServiceDb(client)

        with pytest.raises(httpx.HTTPStatusError):
            await db.list_jobs(workspace_id=WORKSPACE_ID)


# -----------------------------------------------------------------------------
# 3. `returns void` RPC — PostgREST가 204 No Content(빈 바디)로 답하는 경우
#
# 회귀 테스트: .planning/debug/resolved/worker-parse-jsondecodeerror.md.
# index_source_chunk_lexical / index_wiki_page_lexical은 SQL에서 `returns void`이고
# (0011_retrieval.sql:18-58), 로컬 PostgREST(curl로 직접 확인)는 그런 함수 호출에
# 본문 없는 204로 응답한다. 이전 _rpc()는 상태 코드/본문 유무를 확인하지 않고
# response.json()을 무조건 호출해 빈 바디에서 JSONDecodeError를 던졌다.
# -----------------------------------------------------------------------------


def _client_returning_no_content(*, status: int = 204) -> httpx.AsyncClient:
    # PostgREST의 실제 204 응답을 그대로 흉내낸다 — client_returning()처럼 json=payload를
    # 강제로 붙이면 이 케이스(빈 바디)를 검증할 수 없다.
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=b"")

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://example.invalid/rest/v1",
    )


@pytest.mark.asyncio
async def test_lexical_rpc_helpers_treat_204_no_content_as_none() -> None:
    async with _client_returning_no_content(status=204) as client:
        db = service.ServiceDb(client)

        chunk_result = await db.index_source_chunk_lexical(
            workspace_id=WORKSPACE_ID,
            source_chunk_id="chunk-1",
            bigrams="테스트",
            tokenizer_version="v1",
        )
        wiki_result = await db.index_wiki_page_lexical(
            workspace_id=WORKSPACE_ID,
            wiki_id="wiki-1",
            bigrams="테스트",
            tokenizer_version="v1",
        )

    assert chunk_result is None
    assert wiki_result is None


@pytest.mark.asyncio
async def test_rpc_treats_any_empty_body_as_none_even_with_200_status() -> None:
    # 경계 이웃: 상태 코드가 204가 아니라 200이어도 본문이 비어 있으면 같은 결함이
    # 재현된다 — 가드는 status_code 하나가 아니라 본문 유무도 봐야 한다.
    async with _client_returning_no_content(status=200) as client:
        db = service.ServiceDb(client)

        result = await db._rpc("index_source_chunk_lexical", {"p_workspace_id": WORKSPACE_ID})

    assert result is None
