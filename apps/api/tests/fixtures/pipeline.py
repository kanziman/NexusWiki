"""Real local-Supabase pipeline helpers used only by Phase 7 evidence tests."""

from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any

import httpx

from api.services.retrieval import RetrievalService
from tests.conftest import LOCAL_STACK, TenantActor
from worker.db.service import ServiceDb  # noqa: TID251 -- worker run seams need their real DB type
from worker.handlers.compile import run_compile
from worker.handlers.embed import run_embed
from worker.handlers.link_sync import run_link_sync
from worker.handlers.parse import run_parse
from worker.settings import WorkerSettings


def _vector() -> list[float]:
    return [0.0] * 1024


class _QueryEmbedding:
    async def embed(self, _text: str) -> list[float]:
        return _vector()


def _provider_response(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/chat/completions":
        body = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"pages":[{"title":"운영 증거","category":"guides",'
                            '"confidence":"medium","content":"파이프라인 운영 증거"}]}'
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "cost": 0},
            "provider": "test",
            "model": "test-model",
        }
        return httpx.Response(200, json=body)
    if request.url.path == "/embeddings":
        texts = json.loads(request.content).get("input", [])
        return httpx.Response(
            200,
            json={
                "data": [{"embedding": _vector()} for _ in texts],
                "usage": {"prompt_tokens": len(texts), "total_tokens": len(texts), "cost": 0},
                "provider": "test",
                "model": "test-embed",
            },
        )
    raise AssertionError(f"unexpected paid-provider request: {request.url}")


class PipelineHarness:
    """Drive API creation, real queue RPCs, and worker run seams against local Supabase."""

    def __init__(self, local_stack: httpx.Client, authed_client: Any, owner: TenantActor) -> None:
        self._local_stack = local_stack
        self._authed_client = authed_client
        self.owner = owner
        self.created: list[dict[str, str]] = []
        self._stack = AsyncExitStack()
        self._db: ServiceDb | None = None
        self._settings = WorkerSettings(
            SUPABASE_URL=LOCAL_STACK["url"],
            SUPABASE_SECRET_KEY=LOCAL_STACK["admin_key"],
            DATABASE_URL="postgresql://unused",
            OPENROUTER_API_KEY="test-only",
            LLM_MODEL="test-model",
            EMBEDDING_MODEL="test-embed",
            EMBEDDING_PROVIDER="test",
            ALLOW_PRIVATE_FETCH_TARGETS=True,
        )

    async def __aenter__(self) -> PipelineHarness:
        service_client = await self._stack.enter_async_context(
            httpx.AsyncClient(
                base_url=f"{LOCAL_STACK['url']}/rest/v1",
                headers={
                    "apikey": LOCAL_STACK["admin_key"],
                    "Authorization": f"Bearer {LOCAL_STACK['admin_key']}",
                },
                timeout=10.0,
            )
        )
        self._db = ServiceDb(service_client)
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._stack.aclose()

    async def create_three_sources(self) -> list[dict[str, str]]:
        workspace = self.owner.workspace_id
        async with self._authed_client(self.owner) as client:
            responses = [
                await client.post(
                    f"/workspaces/{workspace}/sources/text",
                    json={"title": "텍스트 증거", "text": "파이프라인 운영 증거"},
                ),
                await client.post(
                    f"/workspaces/{workspace}/sources/file?filename=evidence.txt&title=파일 증거",
                    content=b"file pipeline evidence " * 20,
                    headers={"Content-Type": "text/plain"},
                ),
                await client.post(
                    f"/workspaces/{workspace}/sources/url",
                    json={"title": "URL 증거", "url": "https://example.test/evidence"},
                ),
            ]
        assert all(response.status_code == 202 for response in responses), [
            r.text for r in responses
        ]
        self.created = [response.json() for response in responses]
        assert len({item["raw_source_id"] for item in self.created}) == 3
        rows = self._local_stack.get(
            "/rest/v1/raw_sources",
            params={"id": f"eq.{self.created[1]['raw_source_id']}", "select": "storage_path"},
            headers={
                "apikey": LOCAL_STACK["admin_key"],
                "Authorization": f"Bearer {LOCAL_STACK['admin_key']}",
            },
        ).json()
        assert rows[0]["storage_path"].startswith(f"{workspace}/")
        return self.created

    async def drain(self) -> None:
        assert self._db is not None
        async with httpx.AsyncClient(
            base_url="https://provider.test",
            transport=httpx.MockTransport(_provider_response),
        ) as provider:
            async with httpx.AsyncClient(
                base_url=f"{LOCAL_STACK['url']}/storage/v1",
                headers={
                    "apikey": LOCAL_STACK["admin_key"],
                    "Authorization": f"Bearer {LOCAL_STACK['admin_key']}",
                },
            ) as storage:
                while True:
                    job = await self._db.claim_job(worker_id="phase-07-pytest")
                    if job is None:
                        break
                    try:
                        payload = dict(job["payload"])
                        common = {
                            "job_id": str(job["id"]),
                            "workspace_id": str(job["workspace_id"]),
                            "payload": payload,
                        }
                        if job["type"] == "parse":
                            fetch_client = await self._stack.enter_async_context(
                                httpx.AsyncClient(
                                    transport=httpx.MockTransport(
                                        lambda request: httpx.Response(
                                            200,
                                            content=b"url pipeline evidence " * 20,
                                            headers={"content-type": "text/plain"},
                                        )
                                    )
                                )
                            )
                            await run_parse(
                                self._db,
                                settings=self._settings,
                                fetch_client=fetch_client,
                                object_client=storage,
                                **common,
                            )
                        elif job["type"] == "compile":
                            await run_compile(self._db, provider, settings=self._settings, **common)
                        elif job["type"] == "link_sync":
                            await run_link_sync(self._db, **common)
                        elif job["type"] == "embed":
                            await run_embed(self._db, provider, settings=self._settings, **common)
                        else:
                            await self._db.complete_job(str(job["id"]))
                    except Exception as error:
                        await self._db.fail_job(str(job["id"]), error=str(error))
                        raise

    async def assert_retrieval(self, created: list[dict[str, str]]) -> None:
        assert self._db is not None
        jobs = await self._db.list_jobs(workspace_id=self.owner.workspace_id, limit=100)
        assert jobs and all(job["status"] == "succeeded" for job in jobs)
        sources = [
            await self._db.get_raw_source(
                item["raw_source_id"], workspace_id=self.owner.workspace_id
            )
            for item in created
        ]
        assert all(sources)
        pages = await self._db.list_wiki_pages_for_source(
            workspace_id=self.owner.workspace_id, raw_source_id=created[0]["raw_source_id"]
        )
        assert pages
        chunks = await self._db.list_source_chunks(
            workspace_id=self.owner.workspace_id, raw_source_id=created[0]["raw_source_id"]
        )
        assert chunks and chunks[0]["embedding"] is not None
        # The route's real retrieval service needs only the deterministic query boundary replaced.
        service = RetrievalService(_QueryEmbedding())
        async with self._authed_client(self.owner) as client:
            client._transport.app.state.retrieval_service = service  # type: ignore[attr-defined]
            response = await client.post(
                f"/workspaces/{self.owner.workspace_id}/retrieval",
                json={"query": "파이프라인", "requested_k": 1},
            )
        assert response.status_code == 200, response.text
        evidence = response.json()["evidence"]
        assert evidence and evidence[0]["document_id"] in {
            str(pages[0]["id"]),
            str(chunks[0]["id"]),
        }
