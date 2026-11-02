"""원문과 위키 청크에 임베딩을 쓴다."""

from __future__ import annotations

from typing import Any, Final

import httpx

from nexuswiki_core.chunking import chunk_text
from worker.db.service import ServiceDb, service_client
from worker.embedding import embedding_version
from worker.llm import openrouter_client
from worker.llm_gateway import LlmCallContext, LlmGateway
from worker.settings import WorkerSettings

EMBED_JOB_TYPE: Final[str] = "embed"


async def handle_embed(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
    settings = WorkerSettings()
    async with service_client(settings) as db_client, openrouter_client(settings) as or_client:
        await run_embed(
            ServiceDb(db_client),
            or_client,
            settings=settings,
            job_id=job_id,
            workspace_id=workspace_id,
            payload=payload,
        )


async def run_embed(
    db: ServiceDb,
    client: httpx.AsyncClient,
    *,
    settings: WorkerSettings,
    job_id: str,
    workspace_id: str,
    payload: dict[str, Any],
) -> None:
    """Inject provider and database clients for deterministic integration execution."""
    source_id = str(payload.get("raw_source_id") or "")
    scope = payload.get("scope")
    if scope not in {"source", "wiki"}:
        raise ValueError("unknown_embedding_scope")
    version = embedding_version(settings)
    gateway = LlmGateway(db, client, settings)
    context = LlmCallContext(
        workspace_id=workspace_id,
        job_id=job_id,
        call=f"embed_{scope}",
        metadata={"raw_source_id": source_id},
    )
    if scope == "source":
        chunks = await db.list_source_chunks_missing_embedding(
            workspace_id=workspace_id, raw_source_id=source_id, embedding_version=version
        )
        for start in range(0, len(chunks), settings.EMBED_BATCH_SIZE):
            batch = chunks[start : start + settings.EMBED_BATCH_SIZE]
            result = await gateway.embed_texts(context, texts=[str(c["content"]) for c in batch])
            for chunk, vector in zip(batch, result.vectors, strict=True):
                await db.update_source_chunk_embedding(
                    str(chunk["id"]),
                    workspace_id=workspace_id,
                    embedding="[" + ",".join(map(str, vector)) + "]",
                    embedding_version=version,
                )
    else:
        for page in await db.list_wiki_pages_for_source(
            workspace_id=workspace_id, raw_source_id=source_id
        ):
            chunks = chunk_text(str(page.get("content") or ""))
            # ⚠️ 번호만 비교하면 재컴파일이나 승인으로 본문이 바뀌어도 건너뛰어, 벡터 채널이 이전
            #    본문으로 계속 검색된다. 잡은 성공으로 끝나므로 어디에도 드러나지 않는다.
            current_contents = {
                int(row["chunk_index"]): row.get("chunk_content")
                for row in await db.list_wiki_embeddings(
                    workspace_id=workspace_id, wiki_id=str(page["id"]), embedding_version=version
                )
            }
            missing_chunks = [
                chunk for chunk in chunks if current_contents.get(chunk.index) != chunk.content
            ]
            if not missing_chunks:
                await db.delete_wiki_embeddings_from(
                    workspace_id=workspace_id, wiki_id=str(page["id"]), from_index=len(chunks)
                )
                continue
            result = await gateway.embed_texts(
                context, texts=[chunk.content for chunk in missing_chunks]
            )
            await db.upsert_wiki_embeddings(
                workspace_id=workspace_id,
                rows=[
                    {
                        "wiki_id": page["id"],
                        "chunk_index": chunk.index,
                        "chunk_content": chunk.content,
                        "embedding": "[" + ",".join(map(str, vector)) + "]",
                        "embedding_version": version,
                    }
                    for chunk, vector in zip(missing_chunks, result.vectors, strict=True)
                ],
            )
            await db.delete_wiki_embeddings_from(
                workspace_id=workspace_id, wiki_id=str(page["id"]), from_index=len(chunks)
            )
    if scope == "wiki":
        await db.complete_job_and_chain(
            job_id,
            next_type="conflict_check",
            next_payload={"target_id": f"{source_id}:conflict_check", "raw_source_id": source_id},
        )
    else:
        await db.complete_job_and_chain(job_id)
