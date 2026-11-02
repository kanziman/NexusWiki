"""API가 넘긴 Ask 턴 보고서를 외부 관측으로 내보내는 내부 경계.

관련 이슈: #167
설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D8

⚠️ Langfuse 비밀 키는 워커에만 둔다. 같은 키로 전 테넌트의 trace를 읽고 지울 수 있어, API에 두면
API 침해가 RLS 바깥의 교차 테넌트 읽기로 이어진다. 그래서 API는 보고서만 이 라우트로 넘긴다.

⚠️ 본문이 실려 오지 않는다는 것은 호출자의 조립에 기대지 않는다. `export_ask_turn`이 알려진 필드를
숫자와 식별자 모양으로만 통과시키고 구간 이름을 닫아 두며, `_mask`가 2차로 막는다. 내보내기 실패는
어떤 경우에도 호출자에게 전달하지 않는다.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict

from nexuswiki_core.observability import export_ask_turn

__all__ = ["AskTurnExportRequest", "add_ask_turn_export_route"]


class AskTurnExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    control_report: dict[str, Any]
    persisted: bool


def add_ask_turn_export_route(app: FastAPI, *, internal_token: str) -> None:
    """`POST /internal/ask-turn-export`를 기존 앱에 등록한다."""
    if not internal_token:
        raise ValueError("internal token is required")

    @app.post("/internal/ask-turn-export", status_code=status.HTTP_204_NO_CONTENT)
    async def ask_turn_export(
        request: AskTurnExportRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        if authorization != f"Bearer {internal_token}":
            raise HTTPException(status_code=401, detail="internal_unauthorized")
        export_ask_turn(
            workspace_id=str(request.workspace_id),
            control_report=request.control_report,
            persisted=request.persisted,
        )
