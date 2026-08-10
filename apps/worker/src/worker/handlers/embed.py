"""원문과 위키 청크에 임베딩을 쓴다."""

from __future__ import annotations

from typing import Any, Final

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
        if payload.get("scope") != "source":
            raise ValueError("unknown_embedding_scope")
        version = embedding_version(settings)
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
            await db.insert_usage_event(
                workspace_id=workspace_id,
                row={
                    "job_id": job_id,
                    "kind": "embedding",
                    "provider": result.provider,
                    "model": result.model,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "total_tokens": result.total_tokens,
                    "cost_micros": result.cost_micros,
                    "metadata": {},
                },
            )
        await db.complete_job_and_chain(job_id)
