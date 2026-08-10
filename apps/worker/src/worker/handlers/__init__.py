"""잡 type을 핸들러로 잇는 레지스트리 — `jobs.type`에 CHECK가 없는 자리를 지킨다.

관련 태스크: P2-JOB-01
설계 근거: 02-CONTEXT.md > D-18
설계 근거: checklists.json > decisions.db_access, decisions.job_queue

`supabase/migrations/0003_jobs.sql:31-36`은 잡 종류가 Phase 2~3에서 계속 바뀐다는
이유로 `jobs.type`에 CHECK 열거를 걸지 않았고, 대신 워커 레지스트리가 그 역할을
맡기로 했다. 즉 아래 `HANDLERS`가 사실상의 잡 종류 열거이며, 여기에 없는 type을
만나면 워커가 즉시 데드레터로 보내는 것이 그 계약의 나머지 절반이다.

소비자: `worker.queue.run_queue_loop`
"""

from __future__ import annotations

from typing import Any, Final, Protocol, runtime_checkable

from worker.handlers.compile import COMPILE_JOB_TYPE, handle_compile
from worker.handlers.embed import EMBED_JOB_TYPE, handle_embed
from worker.handlers.link_sync import LINK_SYNC_JOB_TYPE, handle_link_sync
from worker.handlers.noop import NOOP_JOB_TYPE, handle_noop
from worker.handlers.parse import PARSE_JOB_TYPE, handle_parse

__all__ = [
    "HANDLERS",
    "JobHandler",
    "UnknownJobTypeError",
    "resolve_handler",
]


class UnknownJobTypeError(LookupError):
    """레지스트리에 등록되지 않은 잡 type.

    메시지에 그 type 문자열을 그대로 싣는다 — 이 문자열이 `jobs.last_error`에
    실려 오타가 그 경로로 잡힌다 (0003_jobs.sql:31-36).
    """

    def __init__(self, job_type: str) -> None:
        self.job_type = job_type
        super().__init__(
            f"등록된 핸들러가 없는 잡 type: {job_type!r} "
            "— 재시도해도 결과가 같으므로 데드레터로 보낸다"
        )


# ⚠️ `workspace_id`를 필수 인자로 두는 것이 이 Protocol의 핵심이다. 워커는
#    `service_role`로 도는데 그것은 BYPASSRLS라, 핸들러가 자기 워크스페이스
#    스코프를 모르면 0004의 격리 정책 전부가 무효인 채로 **오류 없이** 다른
#    테넌트의 행을 읽는 쿼리를 쓰게 된다. 기본값을 주는 순간 잊고 호출해도
#    통과하므로 기본값도 두지 않는다. 근거: checklists.json > decisions.db_access.
@runtime_checkable
class JobHandler(Protocol):
    """모든 잡 핸들러가 만족해야 하는 시그니처 계약."""

    async def __call__(
        self, *, job_id: str, workspace_id: str, payload: dict[str, Any]
    ) -> None: ...


# 새 잡 종류는 이 딕셔너리에 행 하나를 추가하는 것으로 끝나야 한다.
# Phase 2는 `noop` 하나뿐이었다 — 큐 계약을 증명하는 것이 목적이지 일을 하는 것이
# 목적이 아니었기 때문이다 (02-CONTEXT.md > D-17). `noop`은 그대로 둔다:
# `worker.queue_baseline`과 `apps/worker/tests/test_handlers.py`가 의존한다.
#
# ⚠️ 03-09가 `link_sync`와 `embed` 두 행을 더한다. 그때 `test_handlers.py`의 키 집합
#    단언이 **의도적으로 red가 된다** — 핸들러를 등록하고 그 단언을 잊는 경로를 막는 것이
#    그 단언의 목적이다.
HANDLERS: Final[dict[str, JobHandler]] = {
    NOOP_JOB_TYPE: handle_noop,
    PARSE_JOB_TYPE: handle_parse,
    COMPILE_JOB_TYPE: handle_compile,
    LINK_SYNC_JOB_TYPE: handle_link_sync,
    EMBED_JOB_TYPE: handle_embed,
}


def resolve_handler(job_type: str) -> JobHandler:
    """등록된 핸들러를 돌려주고, 없으면 `UnknownJobTypeError`를 던진다.

    여기서 예외를 삼키지 않는다 — 재시도/데드레터 판정은 큐 루프의 몫이다.
    """
    try:
        return HANDLERS[job_type]
    except KeyError as error:
        raise UnknownJobTypeError(job_type) from error
