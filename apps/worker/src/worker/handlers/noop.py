"""부작용이 없는 성공 핸들러 — LLM 비용 0으로 큐 계약을 증명한다.

관련 태스크: P2-JOB-01
설계 근거: 02-CONTEXT.md > D-17

Phase 2가 증명하려는 것은 "일이 된다"가 아니라 claim→complete · SIGTERM 반납 ·
데드레터 세 경로가 계약대로 돈다는 사실이다. 계약이 틀린 채로 LLM을 얹으면
디버깅 한 사이클마다 토큰 비용이 든다. 그래서 이 핸들러가 하는 유일한 일은
구조화 로그 한 줄을 남기는 것이다.

실제 파이프라인 핸들러(parse → compile → link_sync → embed, COMP-04)는 Phase 3이
`worker.handlers.HANDLERS`에 행을 더해 얹는다 — 이 파일을 고치는 것이 아니다.
"""

from __future__ import annotations

from typing import Any, Final

from nexuswiki_core.logging import get_logger

__all__ = ["NOOP_JOB_TYPE", "handle_noop"]

NOOP_JOB_TYPE: Final[str] = "noop"

_logger = get_logger(__name__)


async def handle_noop(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
    """구조화 로그 한 줄만 남기고 성공한다.

    ⚠️ `workspace_id`는 쓰이지 않는 것처럼 보여도 시그니처에서 뺄 수 없다. 이
    시그니처가 `JobHandler` 계약의 유일한 실물이며, Phase 3의 핸들러가 이 자리에서
    워크스페이스 스코프를 물려받는다. 근거: checklists.json > decisions.db_access.
    """
    _logger.info(
        "worker.noop_handled",
        job_id=job_id,
        workspace_id=workspace_id,
        payload_keys=sorted(payload),
    )
