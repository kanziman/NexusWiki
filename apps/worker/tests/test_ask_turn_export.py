"""API가 넘긴 턴 보고서를 내보내는 내부 라우트 (design D8)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from nexuswiki_core.trace import TRACE_HEADER, TraceMiddleware
from worker import ask_turn_export

_TOKEN = "internal"  # noqa: S105 - 테스트 픽스처


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        TraceMiddleware, log_event="worker.internal_request_completed", trust_inbound=True
    )
    ask_turn_export.add_ask_turn_export_route(app, internal_token=_TOKEN)
    return app


def _body(**overrides: Any) -> dict[str, Any]:
    return {
        "workspace_id": str(uuid4()),
        "control_report": {"outcome": "resolved"},
        "persisted": True,
        **overrides,
    }


async def _post(body: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()), base_url="http://worker"
    ) as client:
        return await client.post("/internal/ask-turn-export", json=body, headers=headers)


@pytest.mark.asyncio
async def test_authenticated_report_is_exported_under_the_callers_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[dict[str, Any], str | None]] = []

    def export(**kwargs: Any) -> None:
        from nexuswiki_core.trace import current_trace_id

        calls.append((kwargs, current_trace_id()))

    monkeypatch.setattr(ask_turn_export, "export_ask_turn", export)
    trace_id = str(uuid4())
    body = _body()

    response = await _post(body, {"Authorization": f"Bearer {_TOKEN}", TRACE_HEADER: trace_id})

    assert response.status_code == 204
    assert calls == [
        (
            {
                "workspace_id": body["workspace_id"],
                "control_report": body["control_report"],
                "persisted": True,
            },
            trace_id,
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer wrong"}], ids=["missing", "wrong"]
)
async def test_unauthenticated_call_exports_nothing(
    monkeypatch: pytest.MonkeyPatch, headers: dict[str, str]
) -> None:
    def export(**_: Any) -> None:
        raise AssertionError("인증 전에 내보내면 안 된다")

    monkeypatch.setattr(ask_turn_export, "export_ask_turn", export)

    response = await _post(_body(), headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_extra_field_is_rejected_so_a_body_cannot_ride_along(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ask_turn_export, "export_ask_turn", lambda **_: None)

    response = await _post(_body(question="본문"), {"Authorization": f"Bearer {_TOKEN}"})

    assert response.status_code == 422


def test_route_refuses_an_empty_token() -> None:
    with pytest.raises(ValueError):
        ask_turn_export.add_ask_turn_export_route(FastAPI(), internal_token="")
