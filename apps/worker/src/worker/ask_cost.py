"""#172 Ask 예약·정산 경계. 설계: reconcile-interrupted-ask-cost/design.md D1~D5.

공급자 본문은 저장하지 않는다. 공급자 호출은 재전송하지 않으며 불명확한 전송은 예약을 유지한다.
"""

from __future__ import annotations

import asyncio
import json
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from nexuswiki_core.logging import get_logger
from nexuswiki_core.trace import current_trace_id
from worker.db.service import ServiceDb, service_client
from worker.llm import openrouter_client
from worker.llm_gateway import LlmCallContext, record_stream_usage
from worker.settings import WorkerSettings

_logger = get_logger(__name__)


class ReservationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reserve_micros: int = Field(gt=0, le=10**12)
    max_input_bytes: int = Field(gt=0, le=1_000_000)
    max_tokens: int = Field(gt=0, le=100_000)
    version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")


def confirmed_cost(value: object) -> int | None:
    """누락·bool·비정상 금액을 0과 구분하고 micro-dollar로 올린다."""
    if value is None or isinstance(value, bool) or not isinstance(value, str | int | float):
        return None
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal(10**9):
            return None
        return int((amount * 1_000_000).to_integral_value(rounding=ROUND_CEILING))
    except (InvalidOperation, ValueError):
        return None


class AskCostAccounting:
    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings

    async def rpc(self, function: str, **params: Any) -> Any:
        async with service_client(self.settings) as client:
            db = ServiceDb(client)
            if function == "claim_ask_costs":
                return await db.claim_ask_costs(limit=params["p_limit"])
            workspace_id = params.pop("p_workspace_id")
            if function == "reserve_ask_cost":
                return await db.reserve_ask_cost(workspace_id=workspace_id, params=params)
            if function == "update_ask_cost":
                return await db.update_ask_cost(workspace_id=workspace_id, params=params)
            raise ValueError("unknown accounting function")

    async def reserve(self, workspace_id: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        try:
            policy = ReservationPolicy.model_validate(
                self.settings.ASK_COST_POLICIES.get(self.settings.LLM_MODEL)
            )
        except ValueError:
            _logger.warning("worker.ask_cost_policy_unavailable")
            raise HTTPException(503, "ask_cost_policy_unavailable") from None
        # JSON 구조와 모든 role/content 값을 함께 제한한다. 본문 자체는 DB로 보내지 않는다.
        if len(json.dumps(messages, ensure_ascii=False).encode()) > policy.max_input_bytes:
            raise HTTPException(422, "ask_input_too_large")
        try:
            row = await self.rpc(
                "reserve_ask_cost",
                p_workspace_id=workspace_id,
                p_call_id=str(uuid4()),
                p_trace_id=current_trace_id() or str(uuid4()),
                p_model=self.settings.LLM_MODEL,
                p_policy_version=policy.version,
                p_reserve_micros=policy.reserve_micros,
            )
        except httpx.HTTPStatusError as exc:
            try:
                body = exc.response.json()
                code = body.get("code") if isinstance(body, dict) else None
            except ValueError:
                code = None
            raise HTTPException(
                402 if code == "NW402" else 503,
                "budget_exceeded" if code == "NW402" else "accounting_unavailable",
            ) from None
        except httpx.HTTPError:
            raise HTTPException(503, "accounting_unavailable") from None
        if not isinstance(row, dict) or not row.get("id"):
            raise HTTPException(503, "accounting_unavailable")
        return {**row, "max_tokens": policy.max_tokens}

    async def update(self, call: dict[str, Any], action: str, **params: Any) -> bool:
        return (
            await self.rpc(
                "update_ask_cost",
                p_workspace_id=call["workspace_id"],
                p_call_id=call["id"],
                p_action=action,
                **params,
            )
            is True
        )

    async def finish(
        self,
        call: dict[str, Any],
        usage: dict[str, Any],
        *,
        complete: bool,
        duration_ms: int,
        sent: bool,
    ) -> None:
        if not sent:
            await self.update(call, "release")
            return
        cost = confirmed_cost(usage.get("cost", usage.get("total_cost")))
        # 관측 행은 한 호출당 한 건이다. 최종 비용을 못 얻었어도 예약이 예산을 지킨다.
        async with service_client(self.settings) as client:
            await record_stream_usage(
                ServiceDb(client),
                LlmCallContext(workspace_id=call["workspace_id"], call="ask"),
                usage={
                    **usage,
                    # 공급자 라우팅 문자열을 본문 저장 경로로 만들지 않는다.
                    "model": call["model"],
                    "provider": "openrouter",
                    "cost": (cost or 0) / 1_000_000,
                },
                duration_ms=duration_ms,
                incomplete=not complete or cost is None,
                ask_call_id=call["id"],
                trace_id=call.get("trace_id"),
            )
        if complete and cost is not None and usage.get("model", call["model"]) == call["model"]:
            if await self.update(call, "settle", p_cost_micros=cost, p_source="final_usage"):
                return
        await self.update(call, "unresolved")

    async def reconcile(self, client: httpx.AsyncClient, call: dict[str, Any]) -> None:
        """임대된 호출의 메타데이터만 조회한다. 본문 조회 엔드포인트는 사용하지 않는다."""
        lease = call["lease_id"]
        try:
            generation = call.get("generation_id")
            if not generation:
                return
            response = await client.get("/generation", params={"id": generation}, timeout=5)
            response.raise_for_status()
            body = response.json()
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, dict):
                return
            cost = confirmed_cost(data.get("total_cost"))
            if (
                data.get("id") != generation
                or data.get("model") != call["model"]
                or cost is None
                or not (
                    data.get("finish_reason")
                    in (
                        "stop",
                        "length",
                        "content_filter",
                        "tool_calls",
                        "function_call",
                        "error",
                        "cancelled",
                    )
                    or data.get("cancelled") is True
                )
            ):
                return
            if await self.update(
                call, "settle", p_cost_micros=cost, p_source="generation", p_lease_id=lease
            ):
                return
        except (httpx.HTTPError, ValueError, TypeError):
            # 예외 원문·공급자 응답에 비밀과 본문이 섞일 수 있다.
            _logger.warning("worker.ask_cost_lookup_failed")
        finally:
            # 정산된 호출은 DB가 no-op 처리한다. 실패나 ID 부재는 예약을 해제하지 않는다.
            await self.update(call, "retry", p_lease_id=lease)

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                calls = await self.rpc("claim_ask_costs", p_limit=5)
                async with openrouter_client(self.settings) as client:
                    # 조회와 DB 타임아웃을 합쳐도 5건을 180초 임대 안에서 처리한다.
                    for call in calls:
                        if stop.is_set():
                            break
                        await self.reconcile(client, call)
            except Exception:  # noqa: BLE001 - 다음 주기에 재시도하고 예약을 보존한다.
                _logger.warning("worker.ask_cost_reconcile_failed")
            try:
                await asyncio.wait_for(stop.wait(), timeout=10)
            except TimeoutError:
                pass
