"""wiki_proposal_apply 잡 — 승인된 위키 변경을 페이지와 색인에 반영한다.

관련 이슈: #198
설계 근거: openspec/changes/ai-control-risk-policy/design.md > D4

⚠️ API에서 직접 쓰지 않는 이유: 색인 bigram과 체인 전이가 워커에 있다. API에서 재구현하면
토크나이저가 갈라져 검색이 조용히 깨진다.

⚠️ 멱등성: 상태가 `approved`일 때만 적용하고 `applied`로 전이한다. 재실행은 개정 키와 상태
술어로 no-op이 되어 한 번만 반영된다.

소비자: `worker.handlers.HANDLERS`
"""

from __future__ import annotations

from typing import Any, Final

from nexuswiki_core.logging import get_logger
from nexuswiki_core.tokenizer import TSV_TOKENIZER_VERSION, bigram, normalize
from worker.db.service import ServiceDb, service_client
from worker.settings import WorkerSettings

__all__ = [
    "WIKI_PROPOSAL_APPLY_JOB_TYPE",
    "handle_wiki_proposal_apply",
    "run_wiki_proposal_apply",
]

WIKI_PROPOSAL_APPLY_JOB_TYPE: Final[str] = "wiki_proposal_apply"

_logger = get_logger(__name__)


async def handle_wiki_proposal_apply(
    *, job_id: str, workspace_id: str, payload: dict[str, Any]
) -> None:
    settings = WorkerSettings()
    async with service_client(settings) as db_client:
        await run_wiki_proposal_apply(
            ServiceDb(db_client), job_id=job_id, workspace_id=workspace_id, payload=payload
        )


async def run_wiki_proposal_apply(
    db: ServiceDb, *, job_id: str, workspace_id: str, payload: dict[str, Any]
) -> None:
    proposal_id = str(payload.get("proposal_id") or payload.get("target_id") or "")
    if not proposal_id:
        raise ValueError("wiki_proposal_apply 잡 payload에 proposal_id가 없다")

    proposal = await db.get_wiki_write_proposal(proposal_id, workspace_id=workspace_id)
    if proposal is None or proposal.get("status") not in {"approved", "applied"}:
        await db.complete_job_and_chain(job_id)
        return
    raw_source_id = str(proposal["raw_source_id"])
    if proposal.get("status") == "applied":
        # ⚠️ 적용 표시 뒤 체인 등록 전에 죽은 재실행이다. 여기서 체인 없이 끝내면 링크와 임베딩이
        #    영구히 이전 본문에 남는다. 본문은 다시 쓰지 않고 체인만 잇는다.
        await db.complete_job_and_chain(
            job_id,
            next_type="link_sync",
            next_payload={"target_id": raw_source_id, "raw_source_id": raw_source_id},
        )
        return

    wiki_id = str(proposal["wiki_id"])
    page = await db.get_wiki_page(wiki_id, workspace_id=workspace_id)
    if page is None:
        # 승인 뒤 페이지가 지워졌다. 제안은 FK cascade로 함께 사라지므로 여기엔 드물게만 온다.
        await db.complete_job_and_chain(job_id)
        return

    content = str(proposal["proposed_content"])
    await db.insert_wiki_page_revision(
        workspace_id=workspace_id,
        row={
            "wiki_id": wiki_id,
            "raw_source_id": raw_source_id,
            "job_id": job_id,
            "risk_level": "high",
            "reason": "approved_proposal",
            "previous_title": str(page.get("title") or ""),
            "previous_content": str(page.get("content") or ""),
        },
    )

    previous_sources = page.get("sources")
    sources = sorted(
        {str(item) for item in (previous_sources if isinstance(previous_sources, list) else [])}
        | {raw_source_id}
    )
    # ⚠️ 검증 필드를 넣지 않는다. 사람이 이 내용을 승인했으므로 배지를 그대로 둔다.
    await db.upsert_wiki_page(
        workspace_id=workspace_id,
        row={
            "slug": str(page["slug"]),
            "title": str(proposal["proposed_title"]),
            "category": str(proposal["proposed_category"]),
            "content": content,
            "aliases": proposal.get("proposed_aliases") or [],
            "confidence": str(proposal["proposed_confidence"]),
            "sources": sources,
        },
    )
    await db.index_wiki_page_lexical(
        workspace_id=workspace_id,
        wiki_id=wiki_id,
        bigrams=bigram(normalize(content)),
        tokenizer_version=TSV_TOKENIZER_VERSION,
    )
    await db.replace_wiki_page_evidence(
        workspace_id=workspace_id,
        wiki_id=wiki_id,
        raw_source_id=raw_source_id,
        chunk_ids=[str(item) for item in (proposal.get("evidence_chunk_ids") or [])],
    )
    await db.mark_wiki_write_proposal_applied(proposal_id, workspace_id=workspace_id)
    _logger.info("worker.wiki_proposal_applied", raw_source_id=raw_source_id)
    # 링크와 임베딩을 새 본문으로 다시 맞춘다. 컴파일 체인과 같은 경로다.
    await db.complete_job_and_chain(
        job_id,
        next_type="link_sync",
        next_payload={"target_id": raw_source_id, "raw_source_id": raw_source_id},
    )
