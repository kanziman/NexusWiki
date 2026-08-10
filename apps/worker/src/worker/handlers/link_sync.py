"""위키 본문의 링크를 동기화한다.

관련 태스크: P2-LLM-02
설계 근거: 03-09-PLAN.md > COMP-05 가정
"""

from __future__ import annotations

import re
from typing import Any, Final

from nexuswiki_core.slug import slugify
from worker.db.service import ServiceDb, service_client
from worker.settings import WorkerSettings

LINK_SYNC_JOB_TYPE: Final[str] = "link_sync"
_LINK = re.compile(r"\[\[([^\]]+)\]\]")


async def handle_link_sync(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
    settings = WorkerSettings()
    async with service_client(settings) as client:
        await run_link_sync(
            ServiceDb(client), job_id=job_id, workspace_id=workspace_id, payload=payload
        )


async def run_link_sync(
    db: ServiceDb, *, job_id: str, workspace_id: str, payload: dict[str, Any]
) -> None:
    raw_source_id = str(payload.get("raw_source_id") or payload.get("target_id") or "")
    if not raw_source_id:
        raise ValueError("link_sync 잡 payload에 raw_source_id가 없다")
    for page in await db.list_wiki_pages_for_source(
        workspace_id=workspace_id, raw_source_id=raw_source_id
    ):
        page_id, page_slug = str(page["id"]), str(page["slug"])
        targets = {
            slugify(title=x.strip(), taken=frozenset())
            for x in _LINK.findall(str(page.get("content") or ""))
            if x.strip()
        }
        targets.discard(page_slug)
        rows = []
        for target in sorted(targets):
            other = await db.get_wiki_page_by_slug(workspace_id=workspace_id, slug=target)
            rows.append(
                {
                    "from_wiki_id": page_id,
                    "target_slug": target,
                    "to_wiki_id": other.get("id") if other else None,
                }
            )
        await db.upsert_wiki_links(workspace_id=workspace_id, rows=rows)
        await db.delete_wiki_links_not_in(
            workspace_id=workspace_id, from_wiki_id=page_id, target_slugs=sorted(targets)
        )
        await db.resolve_red_links(
            workspace_id=workspace_id, target_slug=page_slug, to_wiki_id=page_id
        )
    await db.complete_job_and_chain(
        job_id,
        next_type="embed",
        next_payload={
            "target_id": f"{raw_source_id}:wiki",
            "raw_source_id": raw_source_id,
            "scope": "wiki",
        },
    )
