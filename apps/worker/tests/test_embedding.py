import json

import httpx
import pytest

from worker.embedding import EMBEDDING_DIMENSIONS, embed_texts
from worker.settings import WorkerSettings


def settings() -> WorkerSettings:
    return WorkerSettings(
        SUPABASE_URL="https://x",
        SUPABASE_PUBLISHABLE_KEY="x",
        SUPABASE_SECRET_KEY="x",  # noqa: S106 - 테스트용 비밀값
        DATABASE_URL="x",
        OPENROUTER_API_KEY="x",
        OPENAI_API_KEY="x",
        LLM_MODEL="x",
        EMBEDDING_MODEL="m",
        EMBEDDING_PROVIDER="p",
    )


@pytest.mark.asyncio
async def test_embedding_request_locks_provider_and_checks_dimensions() -> None:
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "provider": "p",
                "data": [{"embedding": [0.0] * EMBEDDING_DIMENSIONS}],
                "usage": {"total_tokens": 1, "cost": 0.000001},
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://x"
    ) as client:
        result = await embed_texts(client, settings=settings(), texts=["x"])
    assert result.vectors and seen[0]["provider"]["allow_fallbacks"] is False
    assert seen[0]["provider"]["order"] == ["p"] and "dimensions" not in seen[0]
