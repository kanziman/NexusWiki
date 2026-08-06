"""요청자 JWT로 PostgREST에 붙는 사용자 요청 경로.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-11, D-12
설계 근거: checklists.json > decisions.db_access, decisions.db_transport

`health_check.py`(01-CONTEXT.md > D-11)가 맡던 "트랜스포트 교체 지점" 역할의 Phase 2 연장이다.
트랜스포트가 rpc로 잠겼으므로 asyncpg 커넥션 계층을 두지 않는다.

소비자: 02-04의 `workspaces` 라우터
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

import httpx

from api.errors import DatabaseError, WorkspaceForbidden

__all__ = ["UserDb"]

_REPRESENTATION: Final[str] = "return=representation"


class UserDb:
    """요청자 JWT를 실은 PostgREST 어댑터.

    클라이언트를 인자로 주입받고 모듈 전역을 두지 않는다 — `health_check.py`의 형태를
    그대로 따른다. RLS가 격리를 강제하므로 이 클래스는 스스로 `workspace_id`를 강제하지
    않는다. 그것을 강제해야 하는 쪽은 BYPASSRLS인 `worker.db.service`다.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        supabase_url: str,
        publishable_key: str,
        access_token: str,
    ) -> None:
        self._client = client
        self._base_url = f"{supabase_url.rstrip('/')}/rest/v1"
        # ⚠️ Authorization에 실리는 것은 요청자 JWT다. 여기에 service key가 들어가면
        #    RLS가 통째로 우회되어 0004의 격리 정책 전부가 장식이 된다.
        #    근거: checklists.json > decisions.db_access.
        self._headers = {
            "apikey": publishable_key,
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    # ⚠️ 읽기 경로에는 "0행 = 403" 규칙을 적용하지 않는다. 범용 쿼리 래퍼로 만들면
    #    "정상적으로 비어 있는 조회"와 "RLS가 막은 0행"을 원리적으로 구분할 수 없고,
    #    그 순간 빈 목록이 403이 된다. 쓰기 전용 메서드를 따로 두는 것이 SEC-04의 유일한
    #    온전한 해법이다. 근거: 02-CONTEXT.md > D-11.
    async def select(
        self,
        table: str,
        *,
        match: Mapping[str, str] | None = None,
        columns: str = "*",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """조건에 맞는 행을 돌려준다. 결과가 없으면 빈 리스트이며 예외가 아니다."""
        params: dict[str, str] = {"select": columns}
        params.update(_as_filters(match or {}))
        if limit is not None:
            params["limit"] = str(limit)

        response = await self._client.get(
            f"{self._base_url}/{table}",
            params=params,
            headers=self._headers,
        )
        payload = self._payload(response)
        return payload if isinstance(payload, list) else [payload]

    async def update_one(
        self,
        table: str,
        *,
        match: Mapping[str, str],
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        """정확히 한 행을 갱신하고 그 행을 돌려준다. 아니면 `WorkspaceForbidden`."""
        response = await self._client.patch(
            f"{self._base_url}/{table}",
            params=_require_filters(match),
            json=dict(values),
            headers={**self._headers, "Prefer": _REPRESENTATION},
        )
        return self._exactly_one(response, table=table)

    async def delete_one(self, table: str, *, match: Mapping[str, str]) -> dict[str, Any]:
        """정확히 한 행을 삭제하고 그 행을 돌려준다. 아니면 `WorkspaceForbidden`."""
        response = await self._client.request(
            "DELETE",
            f"{self._base_url}/{table}",
            params=_require_filters(match),
            headers={**self._headers, "Prefer": _REPRESENTATION},
        )
        return self._exactly_one(response, table=table)

    # -- 내부 ----------------------------------------------------------------

    def _exactly_one(self, response: httpx.Response, *, table: str) -> dict[str, Any]:
        # 반환값 계약이 아니라 예외인 이유는 호출자가 무시할 수 없어야 하기 때문이다.
        # 0행을 성공으로 넘기면 격리 실패가 조용히 지나간다 (02-CONTEXT.md > D-11).
        payload = self._payload(response)
        rows = payload if isinstance(payload, list) else [payload]
        if len(rows) != 1:
            raise WorkspaceForbidden(table=table, affected=len(rows))
        return rows[0]

    def _payload(self, response: httpx.Response) -> Any:
        if response.is_success:
            return response.json()

        # ⚠️ 어떤 오류 코드가 Forbidden인지 여기서 판정하지 않는다. 판정과 렌더링이
        #    `api.errors`의 단일 핸들러에만 있어야 SEC-04의 "한 곳" 조건이 유지된다.
        raise DatabaseError(
            sqlstate=_sqlstate_of(response),
            status_code=response.status_code,
            message=f"{response.request.method} {response.request.url.path}",
        )


def _sqlstate_of(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    code = body.get("code") if isinstance(body, dict) else None
    return code if isinstance(code, str) else None


def _as_filters(match: Mapping[str, str]) -> dict[str, str]:
    return {column: f"eq.{value}" for column, value in match.items()}


def _require_filters(match: Mapping[str, str]) -> dict[str, str]:
    # ⚠️ 조건 없는 UPDATE/DELETE는 요청자에게 보이는 모든 행을 건드린다. RLS가 범위를
    #    좁혀주더라도 그것은 "의도한 한 행"이 아니다. 요청을 보내기 전에 막는다.
    if not match:
        raise ValueError("쓰기 경로는 match 조건을 반드시 요구한다 — 조건 없는 쓰기는 금지다")
    return _as_filters(match)
