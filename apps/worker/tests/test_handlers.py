"""핸들러 레지스트리 계약 회귀 테스트 — 미등록 type이 조용히 통과하지 않는다."""

import inspect
from typing import Any

import pytest

from worker import handlers
from worker.handlers import compile as compile_handler
from worker.handlers import noop, parse
from worker.handlers.noop import handle_noop

JOB_ID = "22222222-2222-4222-8222-222222222222"
WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"


# -----------------------------------------------------------------------------
# 1. 레지스트리 — 0003이 jobs.type에 CHECK를 걸지 않은 자리를 이 딕셔너리가 대신한다
# -----------------------------------------------------------------------------


def test_registry_holds_exactly_the_job_types_this_phase_registered() -> None:
    # ⚠️ 이 단언은 03-09가 `link_sync`·`embed`를 등록할 때 **의도적으로 red가 된다.**
    #    그것이 목적이다 — 핸들러를 딕셔너리에 넣고 이 열거를 갱신하지 않으면
    #    `HANDLERS`가 사실상의 잡 종류 열거라는 계약(0003_jobs.sql:31-36)이 흐려진다.
    #    깨지면 값을 확인하고 여기 이름을 더할 것. 단언을 지워서 통과시키지 말 것.
    assert set(handlers.HANDLERS) == {"noop", "parse", "compile"}


def test_each_handler_module_exports_a_job_type_constant_matching_its_key() -> None:
    # 등록 키와 모듈 상수가 갈라지면 핸들러는 등록됐는데 인큐 측이 다른 문자열을 쓰는
    # 상태가 되고, 그 잡은 미등록 type으로 데드레터에 간다.
    constants = {
        "noop": noop.NOOP_JOB_TYPE,
        "parse": parse.PARSE_JOB_TYPE,
        "compile": compile_handler.COMPILE_JOB_TYPE,
    }

    assert set(constants) == set(handlers.HANDLERS)
    for key, constant in constants.items():
        assert constant == key


def test_noop_is_registered_and_satisfies_the_handler_contract() -> None:
    assert "noop" in handlers.HANDLERS, sorted(handlers.HANDLERS)

    registered = handlers.HANDLERS["noop"]

    assert registered is handle_noop
    assert inspect.iscoroutinefunction(registered)
    parameters = inspect.signature(registered).parameters
    assert set(parameters) == {"job_id", "workspace_id", "payload"}
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters.values()
    )


@pytest.mark.asyncio
async def test_handle_noop_succeeds_without_side_effects() -> None:
    payload = {"target_id": "abc"}

    result = await handle_noop(job_id=JOB_ID, workspace_id=WORKSPACE_ID, payload=payload)

    assert result is None
    # 부작용 없음: 넘긴 payload를 건드리지 않는다.
    assert payload == {"target_id": "abc"}


def test_unknown_type_raises_and_names_the_type() -> None:
    # 예외 메시지가 그대로 last_error에 실린다 — 오타는 그 경로로 잡힌다
    # (supabase/migrations/0003_jobs.sql:31-36).
    with pytest.raises(handlers.UnknownJobTypeError) as excinfo:
        handlers.resolve_handler("complie")

    assert "complie" in str(excinfo.value)
    assert excinfo.value.job_type == "complie"


# -----------------------------------------------------------------------------
# 2. workspace 스코프 — service_role은 BYPASSRLS다
# -----------------------------------------------------------------------------


def test_every_registered_handler_requires_workspace_id() -> None:
    # ⚠️ 기본값이 있으면 잊고 호출해도 통과하고, 그 핸들러는 자기 워크스페이스를
    #    모른 채 교차 테넌트를 읽는 쿼리를 쓰게 된다.
    for job_type, handler in handlers.HANDLERS.items():
        parameter = inspect.signature(handler).parameters.get("workspace_id")

        assert parameter is not None, job_type
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, job_type
        assert parameter.default is inspect.Parameter.empty, job_type


# -----------------------------------------------------------------------------
# 3. 예외 전파 — 재시도/데드레터 판정은 큐 루프의 몫이다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_exceptions_are_not_swallowed_by_the_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exploding(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del job_id, workspace_id, payload
        raise RuntimeError("handler boom")

    monkeypatch.setitem(handlers.HANDLERS, "exploding", exploding)

    handler = handlers.resolve_handler("exploding")

    with pytest.raises(RuntimeError, match="handler boom"):
        await handler(job_id=JOB_ID, workspace_id=WORKSPACE_ID, payload={})
