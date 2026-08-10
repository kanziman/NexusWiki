"""원문과 위키 청크에 임베딩을 쓴다."""

from __future__ import annotations

from typing import Any, Final

from nexuswiki_core.chunking import chunk_text
from nexuswiki_core.domain import UsageKind
from worker.db.service import ServiceDb, service_client
from worker.embedding import embed_texts, embedding_version
from worker.llm import openrouter_client
from worker.settings import WorkerSettings

EMBED_JOB_TYPE: Final[str] = "embed"


async def handle_embed(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
    settings = WorkerSettings()
    async with service_client(settings) as db_client, openrouter_client(settings) as or_client:
        db = ServiceDb(db_client)
        source_id = str(payload.get("raw_source_id") or "")
        scope = payload.get("scope")
        if scope not in {"source", "wiki"}:
            raise ValueError("unknown_embedding_scope")
        version = embedding_version(settings)
        if scope == "source":
            chunks = await db.list_source_chunks_missing_embedding(
                workspace_id=workspace_id, raw_source_id=source_id, embedding_version=version
            )
            for start in range(0, len(chunks), settings.EMBED_BATCH_SIZE):
                batch = chunks[start : start + settings.EMBED_BATCH_SIZE]
                result = await embed_texts(
                    or_client, settings=settings, texts=[str(c["content"]) for c in batch]
                )
                for chunk, vector in zip(batch, result.vectors, strict=True):
                    await db.update_source_chunk_embedding(
                        str(chunk["id"]),
                        workspace_id=workspace_id,
                        embedding="[" + ",".join(map(str, vector)) + "]",
                        embedding_version=version,
                    )
                await _record_usage(db, workspace_id, job_id, result)
        else:
            for page in await db.list_wiki_pages_for_source(
                workspace_id=workspace_id, raw_source_id=source_id
            ):
                chunks = chunk_text(str(page.get("content") or ""))
                current_indices = {
                    int(row["chunk_index"])
                    for row in await db.list_wiki_embeddings(
                        workspace_id=workspace_id,
                        wiki_id=str(page["id"]),
                        embedding_version=version,
                    )
                }
                missing_chunks = [chunk for chunk in chunks if chunk.index not in current_indices]
                if not missing_chunks:
                    await db.delete_wiki_embeddings_from(
                        workspace_id=workspace_id, wiki_id=str(page["id"]), from_index=len(chunks)
                    )
                    continue
                result = await embed_texts(
                    or_client, settings=settings, texts=[chunk.content for chunk in missing_chunks]
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
                if chunks:
                    await _record_usage(db, workspace_id, job_id, result)
        await db.complete_job_and_chain(job_id)


async def _record_usage(db: ServiceDb, workspace_id: str, job_id: str, result: Any) -> None:
    await db.insert_usage_event(
        workspace_id=workspace_id,
        row={
            "job_id": job_id,
            "kind": UsageKind.EMBEDDING.value,
            "provider": result.provider,
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "cost_micros": result.cost_micros,
            "metadata": {},
        },
    )
