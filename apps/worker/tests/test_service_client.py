"""service key 팩토리의 인자 강제와 ServiceDb의 workspace 스코프 강제 회귀 테스트."""

import importlib
import inspect
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
    "OPENAI_API_KEY": "sk-proj-test",
    "LLM_MODEL": "anthropic/claude-3.5-sonnet",
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


def test_every_public_helper_is_classified_as_table_or_queue_rpc() -> None:
    # 새 헬퍼가 분류를 빠져나가면 workspace 스코프 강제가 조용히 뚫린다.
    public_helpers = {
        name
        for name, value in vars(service.ServiceDb).items()
        if not name.startswith("_") and inspect.isfunction(value)
    }

    assert public_helpers == service.TABLE_HELPERS | service.RPC_HELPERS
    assert service.TABLE_HELPERS & service.RPC_HELPERS == set()
    assert service.RPC_HELPERS <= service.QUEUE_RPC_FUNCTIONS


def test_table_helpers_declare_workspace_id_without_a_default() -> None:
    for name in service.TABLE_HELPERS:
        parameter = inspect.signature(getattr(service.ServiceDb, name)).parameters.get(
            "workspace_id"
        )

        assert parameter is not None, name
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert parameter.default is inspect.Parameter.empty, name


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

    called = [request.url.path.rsplit("/", 1)[-1] for request in seen]
    assert called == ["claim_job", "complete_job", "fail_job", "release_job"]
    assert set(called) == service.QUEUE_RPC_FUNCTIONS
    assert all(request.method == "POST" for request in seen)


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
