"""공개 쇼케이스의 합성 증거를 만들고, 커밋된 값이 실제 코드와 일치하는지 검사한다 (#168).

설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D10

⚠️ 이 파일은 기준 커밋의 코드 위에서도 그대로 돌아야 한다. `before` 값을 같은 시나리오로 재기
위해서다. 그래서 시나리오는 두 커밋에 모두 있는 경계(공급자 HTTP, `run_*` 함수, Ask 라우트)만 쓰고,
이번 변경에서 생긴 모듈을 import하지 않는다.

증거 갱신 절차:
    # after: 현재 코드로 측정한다. 코드가 커밋되어 있지 않으면 커밋은 `uncommitted`로 남는다.
    uv run python apps/worker/tests/test_controlled_ai_evidence.py measure out.json
    uv run python apps/worker/tests/test_controlled_ai_evidence.py write after out.json

    # before: 기준 커밋의 worktree를 PYTHONPATH 앞에 두고 측정한다.
    git worktree add <dir> 79b68fe
    # 구분자는 macOS와 Linux에서 `:`, Windows에서 `;`다.
    PYTHONPATH="<dir>/apps/api/src:<dir>/apps/worker/src:<dir>/packages/core/src" \
        uv run python apps/worker/tests/test_controlled_ai_evidence.py measure before.json
    uv run python apps/worker/tests/test_controlled_ai_evidence.py write before before.json
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import subprocess
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = _REPO_ROOT / "apps" / "dashboard" / "content" / "controlled-ai" / "step1.json"
BASELINE_COMMIT = "79b68fe"
_UNCOMMITTED = "uncommitted"
_COST_PER_ATTEMPT_USD = 0.001

_WIKI_ID = str(uuid4())
_SOURCE_CHUNK_ID = str(uuid4())
_RAW_SOURCE_ID = str(uuid4())
_WORKSPACE_ID = str(uuid4())


# -- 공급자 대역 ----------------------------------------------------------------


def _provider(contents: list[str]) -> tuple[httpx.AsyncClient, list[float]]:
    """응답마다 같은 비용을 보고하는 공급자. 돌려준 비용을 시도별로 함께 남긴다."""
    reported: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        content = contents[min(len(reported), len(contents) - 1)]
        reported.append(_COST_PER_ATTEMPT_USD)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                    "cost": _COST_PER_ATTEMPT_USD,
                },
                "provider": "scenario-provider",
                "model": "scenario-model",
            },
        )

    client = httpx.AsyncClient(
        base_url="https://provider.test", transport=httpx.MockTransport(handler)
    )
    return client, reported


def _worker_settings() -> Any:
    from worker.settings import WorkerSettings

    return WorkerSettings(
        SUPABASE_URL="https://example.invalid",
        SUPABASE_PUBLISHABLE_KEY="scenario-publishable",
        SUPABASE_SECRET_KEY="scenario-secret",  # noqa: S106 - 합성 시나리오
        DATABASE_URL="postgresql://scenario",
        OPENROUTER_API_KEY="scenario-provider-key",
        LLM_MODEL="scenario-model",
    )


def _usage_values(rows: list[dict[str, Any]], reported: list[float]) -> dict[str, int]:
    return {
        "provider_reported_cost_micros": round(sum(reported) * 1_000_000),
        "recorded_cost_micros": sum(int(row["cost_micros"]) for row in rows),
        "recorded_usage_rows": len(rows),
    }


# -- 비용 회계 시나리오 ------------------------------------------------------------


async def conflict_judge_cost() -> dict[str, Any]:
    """충돌 판정이 후보 두 쌍을 판정한다."""
    from worker.handlers import conflict

    class Db:
        def __init__(self) -> None:
            self.usage: list[dict[str, Any]] = []

        async def list_wiki_pages_for_source(self, **_: Any) -> list[dict[str, str]]:
            return [{"id": "page-a", "content": "합성 문서 A"}]

        async def find_similar_wiki_pages(self, **_: Any) -> list[dict[str, Any]]:
            return [
                {"candidate_wiki_id": "page-b", "similarity": 0.93},
                {"candidate_wiki_id": "page-c", "similarity": 0.91},
            ]

        async def _select(self, _table: str, *, params: dict[str, str]) -> list[dict[str, str]]:
            return [{"id": params["id"].removeprefix("eq."), "content": "합성 문서 B"}]

        async def complete_job_and_chain(self, _job_id: str, **_: Any) -> None:
            return None

        async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
            self.usage.append(row)

    db = Db()
    client, reported = _provider(['{"is_contradiction": false, "rationale": "합성 판정"}'])
    async with client:
        await conflict.run_conflict_check(
            db,  # type: ignore[arg-type]
            client,
            settings=_worker_settings(),
            job_id="scenario-job",
            workspace_id=_WORKSPACE_ID,
            payload={"raw_source_id": _RAW_SOURCE_ID},
        )
    return _usage_values(db.usage, reported)


async def compile_retry_cost() -> dict[str, Any]:
    """컴파일 첫 시도가 스키마 검증에 실패하고 두 번째 시도가 성공한다."""
    from worker.handlers import compile as compile_handler

    class Db:
        def __init__(self) -> None:
            self.usage: list[dict[str, Any]] = []

        async def get_raw_source(self, *_: Any, **__: Any) -> dict[str, str]:
            return {"title": "합성 문서", "source_type": "text"}

        async def get_default_prompt_template(self, **_: Any) -> dict[str, str]:
            return {"system_prompt": "합성 지시", "template": "{{source_content}}"}

        async def list_wiki_slugs(self, **_: Any) -> list[str]:
            return []

        async def list_source_chunks(self, **_: Any) -> list[dict[str, str]]:
            return [{"content": "합성 원문"}]

        async def latest_compile_fingerprint(self, **_: Any) -> None:
            return None

        async def get_wiki_page_by_slug(self, **_: Any) -> None:
            return None

        async def upsert_wiki_page(self, **_: Any) -> dict[str, str]:
            return {"id": "page-a"}

        async def index_wiki_page_lexical(self, **_: Any) -> None:
            return None

        async def replace_wiki_page_evidence(self, **_: Any) -> None:
            return None

        async def complete_job_and_chain(self, _job_id: str, **_: Any) -> None:
            return None

        async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
            self.usage.append(row)

    db = Db()
    client, reported = _provider(
        [
            "스키마를 만족하지 않는 응답",
            json.dumps(
                {
                    "pages": [
                        {
                            "title": "합성 문서",
                            "category": "guides",
                            "confidence": "medium",
                            "content": "합성 본문",
                        }
                    ]
                }
            ),
        ]
    )
    async with client:
        await compile_handler.run_compile(
            db,  # type: ignore[arg-type]
            client,
            settings=_worker_settings(),
            job_id="scenario-job",
            workspace_id=_WORKSPACE_ID,
            payload={"raw_source_id": _RAW_SOURCE_ID},
        )
    return _usage_values(db.usage, reported)


class _OutputContractDb:
    """Step 3 시나리오의 컴파일 대역. 저장된 페이지만 센다."""

    def __init__(self) -> None:
        self.usage: list[dict[str, Any]] = []
        self.saved = 0

    async def get_raw_source(self, *_: Any, **__: Any) -> dict[str, str]:
        return {"title": "합성 문서", "source_type": "text"}

    async def get_default_prompt_template(self, **_: Any) -> dict[str, str]:
        return {"system_prompt": "합성 지시", "template": "{{source_content}}"}

    async def list_wiki_slugs(self, **_: Any) -> list[str]:
        return []

    async def list_source_chunks(self, **_: Any) -> list[dict[str, str]]:
        return [{"content": "합성 원문"}]

    async def latest_compile_fingerprint(self, **_: Any) -> None:
        return None

    async def get_wiki_page_by_slug(self, **_: Any) -> None:
        return None

    async def upsert_wiki_page(self, **_: Any) -> dict[str, str]:
        self.saved += 1
        return {"id": "page-a"}

    async def index_wiki_page_lexical(self, **_: Any) -> None:
        return None

    async def replace_wiki_page_evidence(self, **_: Any) -> None:
        return None

    async def complete_job_and_chain(self, _job_id: str, **_: Any) -> None:
        return None

    async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
        self.usage.append(row)


def _page_json(content: str) -> str:
    return json.dumps(
        {
            "pages": [
                {
                    "title": "합성 문서",
                    "category": "guides",
                    "confidence": "medium",
                    "content": content,
                }
            ]
        },
        ensure_ascii=False,
    )


async def _run_output_contract_compile(contents: list[str]) -> tuple[_OutputContractDb, int]:
    from worker.handlers import compile as compile_handler

    db = _OutputContractDb()
    client, reported = _provider(contents)
    async with client:
        try:
            await compile_handler.run_compile(
                db,  # type: ignore[arg-type]
                client,
                settings=_worker_settings(),
                job_id="scenario-job",
                workspace_id=_WORKSPACE_ID,
                payload={"raw_source_id": _RAW_SOURCE_ID},
            )
        except Exception:  # noqa: BLE001, S110 - 잡 실패도 관측 대상이다. 호출 수와 저장 수만 잰다.
            pass
    return db, len(reported)


async def compile_fence_retry() -> dict[str, Any]:
    """공급자가 유효한 JSON을 코드 펜스로 감싸 돌려준다."""
    db, calls = await _run_output_contract_compile(
        [f"```json\n{_page_json('합성 본문')}\n```", _page_json("합성 본문")]
    )
    return {"provider_calls": calls, "pages_saved": db.saved}


async def compile_placeholder_page() -> dict[str, Any]:
    """공급자가 본문이 placeholder인 페이지를 계속 돌려준다."""
    db, calls = await _run_output_contract_compile([_page_json("TODO")])
    return {"provider_calls": calls, "pages_saved": db.saved}


async def compile_unchanged_skip() -> dict[str, Any]:
    """원문 해시와 프롬프트·모델 지문이 이전 컴파일과 같고 위키 페이지가 이미 존재한다."""
    import hashlib

    from worker.handlers import compile as compile_handler

    body = hashlib.sha256("합성 원문".encode()).hexdigest()
    fingerprint = hashlib.sha256(
        f"{body}\x1fscenario-template\x1fscenario-model".encode()
    ).hexdigest()

    class Db:
        def __init__(self) -> None:
            self.usage: list[dict[str, Any]] = []

        async def get_raw_source(self, *_: Any, **__: Any) -> dict[str, str]:
            return {
                "title": "합성 문서",
                "source_type": "text",
                "content_hash": "scenario-hash",
            }

        async def get_default_prompt_template(self, **_: Any) -> dict[str, str]:
            return {
                "id": "scenario-template",
                "system_prompt": "합성 지시",
                "template": "{{source_content}}",
            }

        async def list_wiki_slugs(self, **_: Any) -> list[str]:
            return []

        async def list_source_chunks(self, **_: Any) -> list[dict[str, str]]:
            return [{"content": "합성 원문"}]

        async def latest_compile_fingerprint(self, **_: Any) -> str:
            return fingerprint

        async def list_wiki_pages_for_source(self, **_: Any) -> list[dict[str, str]]:
            return [{"id": "page-a", "content": "합성 본문"}]

        async def get_wiki_page_by_slug(self, **_: Any) -> None:
            return None

        async def upsert_wiki_page(self, **_: Any) -> dict[str, str]:
            return {"id": "page-a"}

        async def index_wiki_page_lexical(self, **_: Any) -> None:
            return None

        async def complete_job_and_chain(self, _job_id: str, **_: Any) -> None:
            return None

        async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
            self.usage.append(row)

    db = Db()
    client, reported = _provider(
        [
            json.dumps(
                {
                    "pages": [
                        {
                            "title": "합성 문서",
                            "category": "guides",
                            "confidence": "medium",
                            "content": "합성 본문",
                        }
                    ]
                }
            )
        ]
    )
    async with client:
        await compile_handler.run_compile(
            db,  # type: ignore[arg-type]
            client,
            settings=_worker_settings(),
            job_id="scenario-job",
            workspace_id=_WORKSPACE_ID,
            payload={"raw_source_id": _RAW_SOURCE_ID},
        )
    return _usage_values(db.usage, reported)


async def structured_output_max_tokens() -> dict[str, Any]:
    """긴 위키 페이지 쌍의 충돌 판정 요청에서 입력 토큰과 max_tokens 상한을 관측한다."""
    import tiktoken

    from worker.handlers import conflict

    long_text = "합성 충돌 검증 문장입니다. " * 600
    captured_bodies: list[dict[str, Any]] = []

    class Db:
        def __init__(self) -> None:
            self.usage: list[dict[str, Any]] = []

        async def list_wiki_pages_for_source(self, **_: Any) -> list[dict[str, str]]:
            return [{"id": "page-a", "content": long_text}]

        async def find_similar_wiki_pages(self, **_: Any) -> list[dict[str, Any]]:
            return [{"candidate_wiki_id": "page-b", "similarity": 0.93}]

        async def _select(self, _table: str, *, params: dict[str, str]) -> list[dict[str, str]]:
            return [{"id": params["id"].removeprefix("eq."), "content": long_text}]

        async def complete_job_and_chain(self, _job_id: str, **_: Any) -> None:
            return None

        async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
            self.usage.append(row)

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"is_contradiction": false, "rationale": "합성 판정"}'
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                    "cost": _COST_PER_ATTEMPT_USD,
                },
                "provider": "scenario-provider",
                "model": "scenario-model",
            },
        )

    db = Db()
    client = httpx.AsyncClient(
        base_url="https://provider.test", transport=httpx.MockTransport(handler)
    )
    async with client:
        await conflict.run_conflict_check(
            db,  # type: ignore[arg-type]
            client,
            settings=_worker_settings(),
            job_id="scenario-job",
            workspace_id=_WORKSPACE_ID,
            payload={"raw_source_id": _RAW_SOURCE_ID},
        )
    body = captured_bodies[0]
    encoding = tiktoken.get_encoding("cl100k_base")
    user_prompt = body["messages"][-1]["content"]
    return {
        "input_tokens": len(encoding.encode(user_prompt)),
        "requested_max_tokens": body.get("max_tokens"),
    }


# -- Ask 시나리오 -----------------------------------------------------------------


class _Upstream:
    status_code = 200

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


class _LlmStream:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.calls = 0

    def stream(self, **_: Any) -> _LlmStream:
        self.calls += 1
        return self

    async def __aenter__(self) -> _Upstream:
        return _Upstream(self._lines)

    async def __aexit__(self, *_: object) -> None:
        return None


class _Retrieval:
    async def retrieve(self, *_: Any) -> Any:
        from api.services.retrieval import RetrievalResult
        from nexuswiki_core.rrf import EvidenceHit

        return RetrievalResult(
            evidence=[
                EvidenceHit.wiki(wiki_id=_WIKI_ID, rank=1, metadata={"title": "합성 위키"}),
                EvidenceHit.source(
                    chunk_id=_SOURCE_CHUNK_ID,
                    rank=1,
                    metadata={"raw_source_id": _RAW_SOURCE_ID, "chunk_index": 0},
                ),
            ],
            meta={"policy_version": "scenario"},
        )


def _ask_transport(finalized: dict[str, Any]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/rest/v1/wiki_pages":
            return httpx.Response(200, json=[{"id": _WIKI_ID, "content": "합성 위키 본문"}])
        if path == "/rest/v1/source_chunks":
            return httpx.Response(200, json=[{"id": _SOURCE_CHUNK_ID, "content": "합성 원문"}])
        if path == "/rest/v1/prompt_templates":
            if "workspace_id" in request.url.params:
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[
                    {
                        "id": str(uuid4()),
                        "name": "합성 템플릿",
                        "workspace_id": None,
                        "system_prompt": "합성 지시",
                        "template": "{{question}} {{wiki_context}} {{source_context}}",
                    }
                ],
            )
        if path in {"/rest/v1/rpc/start_ask_turn", "/rest/v1/rpc/finalize_ask_turn"}:
            if path.endswith("finalize_ask_turn"):
                finalized.update(json.loads(request.content))
            return httpx.Response(
                200, json=[{"thread_id": str(uuid4()), "message_id": str(uuid4())}]
            )
        raise AssertionError(f"시나리오에 없는 요청: {path}")

    return httpx.MockTransport(handler)


async def _ask(
    lines: list[str], *, quality_mode: str = "shadow", stream: Any = None
) -> tuple[list[tuple[str, dict[str, Any]]], dict[str, Any]]:
    from api.main import create_app
    from api.services.ask import AskService
    from api.settings import ApiSettings

    finalized: dict[str, Any] = {}
    app = create_app(
        ApiSettings(
            SUPABASE_URL="https://example.invalid",
            SUPABASE_PUBLISHABLE_KEY="scenario-publishable",
        ),
        git_sha="scenario",
    )
    async with app.router.lifespan_context(app):
        await app.state.http_client.aclose()
        app.state.http_client = httpx.AsyncClient(transport=_ask_transport(finalized))
        # 기준 커밋에는 품질 모드가 없다. Step 1 시나리오는 지표만 보도록 기록 모드로 둔다.
        extra = (
            {"quality_mode": quality_mode}
            if "quality_mode" in inspect.signature(AskService.__init__).parameters
            else {}
        )
        app.state.ask_service = AskService(_Retrieval(), stream or _LlmStream(lines), **extra)
        async with httpx.AsyncClient(
            # 기준 커밋은 깨진 프레임에서 예외로 스트림이 끊긴다. 그 동작도 관측값이다.
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/workspaces/{_WORKSPACE_ID}/ask",
                json={"query": "합성 질문", "client_turn_id": str(uuid4())},
                headers={"Authorization": "Bearer scenario"},
            )
    assert response.status_code == 200, response.text
    events: list[tuple[str, dict[str, Any]]] = []
    for block in response.text.split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields.get("data") or "{}")))
    return events, finalized


async def ask_broken_stream_frame() -> dict[str, Any]:
    """답변 스트림 중간에 깨진 프레임이 온다."""
    events, finalized = await _ask(
        [
            'data: {"choices":[{"delta":{"content":"부분 답변 [[wiki:w1]] [[src:s1]]."}}]}',
            'data: {"choices":[{"delta":',
            "data: [DONE]",
        ]
    )
    return {
        "turn_final_status": finalized.get("p_status") or "not_finalized",
        "terminal_event": events[-1][0],
    }


async def ask_fabricated_citation() -> dict[str, Any]:
    """모델이 근거에 없는 앵커만 단 문장을 답한다."""
    events, _ = await _ask(
        [
            'data: {"choices":[{"delta":{"content":"근거 없는 주장 [[wiki:w9]] [[src:s9]]."}}]}',
            "data: [DONE]",
        ]
    )
    citations = next(payload for name, payload in events if name == "citations")
    return {
        "fabricated_anchor_count": citations.get("fabricated_anchor_count", 0),
        "dual_citation_rate": citations.get("dual_citation_rate"),
    }


async def ask_no_citation_terminal() -> dict[str, Any]:
    """모델이 수리 뒤에도 인용을 하나도 달지 않는다."""
    stream = _LlmStream(
        ['data: {"choices":[{"delta":{"content":"근거를 달지 않은 답변입니다."}}]}', "data: [DONE]"]
    )
    events, finalized = await _ask([], quality_mode="enforce", stream=stream)
    citations = next(payload for name, payload in events if name == "citations")
    return {
        "turn_final_status": finalized.get("p_status"),
        "provider_calls": stream.calls,
        "cited_anchor_count": citations.get("cited_anchor_count", 0),
    }


async def ask_context_budget_quota() -> dict[str, Any]:
    """긴 위키 근거 세 건이 앞순위를 차지할 때 컨텍스트 토큰 상한과 원문 최소 몫을 관측한다."""
    import tiktoken

    from api.main import create_app
    from api.services.ask import AskService
    from api.services.retrieval import RetrievalResult
    from api.settings import ApiSettings
    from nexuswiki_core.rrf import EvidenceHit

    wiki_ids = ["scenario-wiki-1", "scenario-wiki-2", "scenario-wiki-3"]
    chunk_id = "scenario-chunk-1"
    raw_source_id = "scenario-source-1"
    long_wiki = "합성 위키 본문 문장입니다. " * 500
    source_text = "합성 원문 근거 문장입니다. " * 20
    captured_messages: list[list[dict[str, str]]] = []

    class BudgetRetrieval:
        async def retrieve(self, *_: Any) -> Any:
            return RetrievalResult(
                evidence=[
                    EvidenceHit.wiki(
                        wiki_id=wiki_ids[0], rank=1, metadata={"title": "합성 위키 가"}
                    ),
                    EvidenceHit.wiki(
                        wiki_id=wiki_ids[1], rank=2, metadata={"title": "합성 위키 나"}
                    ),
                    EvidenceHit.wiki(
                        wiki_id=wiki_ids[2], rank=3, metadata={"title": "합성 위키 다"}
                    ),
                    EvidenceHit.source(
                        chunk_id=chunk_id,
                        rank=4,
                        metadata={"raw_source_id": raw_source_id, "chunk_index": 0},
                    ),
                ],
                meta={"policy_version": "scenario"},
            )

    class CapturingStream(_LlmStream):
        def stream(self, **kwargs: Any) -> _LlmStream:
            if "messages" in kwargs:
                captured_messages.append(kwargs["messages"])
            return self

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/rest/v1/wiki_pages":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": wid,
                        "slug": f"wiki-{idx}",
                        "title": f"합성 위키 {idx}",
                        "content": long_wiki,
                    }
                    for idx, wid in enumerate(wiki_ids, start=1)
                ],
            )
        if path == "/rest/v1/source_chunks":
            return httpx.Response(200, json=[{"id": chunk_id, "content": source_text}])
        if path == "/rest/v1/prompt_templates":
            if "workspace_id" in request.url.params:
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[
                    {
                        "id": str(uuid4()),
                        "name": "합성 템플릿",
                        "workspace_id": None,
                        "system_prompt": "합성 지시",
                        "template": "{{question}} {{wiki_context}} {{source_context}}",
                    }
                ],
            )
        if path in {"/rest/v1/rpc/start_ask_turn", "/rest/v1/rpc/finalize_ask_turn"}:
            return httpx.Response(
                200, json=[{"thread_id": str(uuid4()), "message_id": str(uuid4())}]
            )
        raise AssertionError(f"시나리오에 없는 요청: {path}")

    lines = [
        'data: {"choices":[{"delta":{"content":"합성 답변 [[wiki:w1]] [[src:s1]]."}}]}',
        "data: [DONE]",
    ]
    app = create_app(
        ApiSettings(
            SUPABASE_URL="https://example.invalid",
            SUPABASE_PUBLISHABLE_KEY="scenario-publishable",
        ),
        git_sha="scenario",
    )
    async with app.router.lifespan_context(app):
        await app.state.http_client.aclose()
        app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app.state.ask_service = AskService(BudgetRetrieval(), CapturingStream(lines))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/workspaces/{_WORKSPACE_ID}/ask",
                json={"query": "합성 질문", "client_turn_id": str(uuid4())},
                headers={"Authorization": "Bearer scenario"},
            )
    assert response.status_code == 200, response.text
    user_prompt = captured_messages[0][-1]["content"]
    encoding = tiktoken.get_encoding("cl100k_base")
    return {
        "prompt_context_tokens": len(encoding.encode(user_prompt)),
        "prompt_wiki_anchors": user_prompt.count("[[wiki:"),
        "prompt_source_anchors": user_prompt.count("[[src:"),
    }


# -- 증거 항목 정의 -----------------------------------------------------------------

_COST_METRICS = [
    {"key": "provider_reported_cost_micros", "label": "공급자가 보고한 비용", "unit": "usd_micros"},
    {"key": "recorded_cost_micros", "label": "회계에 기록된 비용", "unit": "usd_micros"},
    {"key": "recorded_usage_rows", "label": "기록된 사용량 행", "unit": "count"},
]

_CONTRACT_METRICS = [
    {"key": "provider_calls", "label": "공급자 호출", "unit": "count"},
    {"key": "pages_saved", "label": "저장된 페이지", "unit": "count"},
]

ITEMS: list[dict[str, Any]] = [
    {
        "id": "conflict-judge-cost",
        "title": "충돌 판정 비용 누락",
        "problem": "충돌 판정의 LLM 비용이 회계에 전혀 남지 않아 월 상한 계산에서 빠졌습니다.",
        "fix": "모든 공급자 호출을 하나의 경계로 모아 호출마다 사용량을 기록합니다.",
        "scenario": "conflict_judge_cost",
        "metrics": _COST_METRICS,
    },
    {
        "id": "compile-retry-cost",
        "title": "컴파일 재시도 비용 누락",
        "problem": "검증에 실패한 시도의 비용이 버려져, 마지막 시도의 비용만 기록되었습니다.",
        "fix": "공급자가 사용량을 보고하는 즉시, 응답을 검증하기 전에 시도별로 기록합니다.",
        "scenario": "compile_retry_cost",
        "metrics": _COST_METRICS,
    },
    {
        "id": "ask-broken-stream-frame",
        "title": "깨진 스트림의 미종결 턴",
        "problem": "깨진 프레임에서 예외가 나 연결이 끊기고, 턴이 종결되지 않고 남았습니다.",
        "fix": "깨진 프레임을 받으면 턴을 오류로 종결하고 부분 답변은 저장하지 않습니다.",
        "scenario": "ask_broken_stream_frame",
        "metrics": [
            {"key": "turn_final_status", "label": "턴의 최종 상태", "unit": "text"},
            {"key": "terminal_event", "label": "클라이언트가 받은 마지막 이벤트", "unit": "text"},
        ],
    },
    {
        "id": "ask-fabricated-citation",
        "title": "위조 앵커의 인용 지표 왜곡",
        "problem": "근거에 없는 앵커만 단 문장이 이중 인용으로 계산되었습니다.",
        "fix": "위조 앵커를 제거한 텍스트로 인용 지표를 계산합니다.",
        "scenario": "ask_fabricated_citation",
        "metrics": [
            {"key": "fabricated_anchor_count", "label": "적발한 위조 앵커", "unit": "count"},
            {"key": "dual_citation_rate", "label": "이중 인용률", "unit": "rate"},
        ],
    },
    {
        "id": "compile-unchanged-skip",
        "title": "변경 없는 원문의 중복 재컴파일",
        "problem": "원문 해시와 프롬프트·모델 지문이 그대로여도 매번 공급자를 다시 호출했습니다.",
        "fix": (
            "지문이 일치하고 기존 위키 페이지가 있으면 "
            "공급자 호출을 생략하고 후속 작업으로 넘깁니다."
        ),
        "scenario": "compile_unchanged_skip",
        "metrics": _COST_METRICS,
    },
    {
        "id": "ask-context-budget-quota",
        "title": "질문 컨텍스트 무제한 주입과 원문 근거 기아",
        "problem": (
            "긴 위키 페이지들이 프롬프트에 그대로 들어가 "
            "컨텍스트가 비대해지고 원문 근거를 밀어냈습니다."
        ),
        "fix": (
            "컨텍스트 토큰 상한과 원문 최소 몫을 강제해 "
            "상한 안에서 위키와 원문 근거를 함께 유지합니다."
        ),
        "scenario": "ask_context_budget_quota",
        "metrics": [
            {"key": "prompt_context_tokens", "label": "프롬프트 컨텍스트 크기", "unit": "tokens"},
            {"key": "prompt_wiki_anchors", "label": "포함된 위키 근거", "unit": "count"},
            {"key": "prompt_source_anchors", "label": "포함된 원문 근거", "unit": "count"},
        ],
    },
    {
        "id": "structured-output-max-tokens",
        "title": "구조화 호출의 입출력 토큰 무제한 요청",
        "problem": (
            "충돌 판정과 컴파일이 긴 본문을 그대로 보내고 출력 토큰 상한도 지정하지 않았습니다."
        ),
        "fix": (
            "작업별 입력 토큰 상한으로 본문을 절단하고 공급자 요청에 출력 토큰 상한을 명시합니다."
        ),
        "scenario": "structured_output_max_tokens",
        "metrics": [
            {"key": "input_tokens", "label": "전송한 입력 크기", "unit": "tokens"},
            {"key": "requested_max_tokens", "label": "요청한 출력 상한", "unit": "tokens"},
        ],
    },
    {
        "id": "compile-fence-retry",
        "title": "코드 펜스 하나가 부른 유료 재시도",
        "problem": "온전한 JSON도 코드 펜스로 감싸이면 실패로 처리되어 호출을 다시 지불했습니다.",
        "fix": "응답 전체를 감싼 펜스 한 겹은 코드로 벗겨 재시도 없이 통과시킵니다.",
        "scenario": "compile_fence_retry",
        "metrics": _CONTRACT_METRICS,
    },
    {
        "id": "compile-placeholder-page",
        "title": "placeholder 페이지 저장",
        "problem": "본문이 TODO인 페이지도 스키마를 통과해 위키에 저장되었습니다.",
        "fix": "공백과 placeholder를 의미 검증으로 거부하고 호출을 2회로 제한합니다.",
        "scenario": "compile_placeholder_page",
        "metrics": _CONTRACT_METRICS,
    },
    {
        "id": "ask-no-citation-terminal",
        "title": "인용 없는 답변의 정상 저장",
        "problem": "인용이 하나도 없는 답변이 정상 답변으로 저장되었습니다.",
        "fix": "위반을 1회 수리하고, 실패하면 발급 앵커만 쓴 근거 목록으로 끝냅니다.",
        "scenario": "ask_no_citation_terminal",
        "metrics": [
            {"key": "turn_final_status", "label": "턴의 최종 상태", "unit": "text"},
            {"key": "provider_calls", "label": "공급자 호출", "unit": "count"},
            {"key": "cited_anchor_count", "label": "해소된 인용", "unit": "count"},
        ],
    },
]

UPCOMING_STEPS = [
    {"step": 4, "title": "리스크", "description": "공통 정책을 주입하고 위키 쓰기를 분류합니다."},
]

SCENARIOS: dict[str, Callable[[], Awaitable[dict[str, Any]]]] = {
    "conflict_judge_cost": conflict_judge_cost,
    "compile_retry_cost": compile_retry_cost,
    "ask_broken_stream_frame": ask_broken_stream_frame,
    "ask_fabricated_citation": ask_fabricated_citation,
    "compile_unchanged_skip": compile_unchanged_skip,
    "ask_context_budget_quota": ask_context_budget_quota,
    "structured_output_max_tokens": structured_output_max_tokens,
    "compile_fence_retry": compile_fence_retry,
    "compile_placeholder_page": compile_placeholder_page,
    "ask_no_citation_terminal": ask_no_citation_terminal,
}


# -- 증거 파일 생성 -----------------------------------------------------------------


def _measure() -> dict[str, dict[str, Any]]:
    async def run_all() -> dict[str, dict[str, Any]]:
        return {name: await scenario() for name, scenario in SCENARIOS.items()}

    return asyncio.run(run_all())


def _current_commit() -> str:
    """측정에 쓰인 코드가 커밋되어 있을 때만 그 커밋을 돌려준다.

    ⚠️ 작업 트리가 더러운데 HEAD를 적으면, 그 커밋에 없는 코드의 측정값을 그 커밋의 것처럼 공개한다.
    증거 파일 자신은 측정 대상이 아니므로 제외한다.
    """
    status = subprocess.run(  # noqa: S603 - 고정된 인자로 git을 실행한다
        [  # noqa: S607
            "git",
            "status",
            "--porcelain",
            "--",
            "apps/api/src",
            "apps/worker/src",
            "packages/core/src",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if status.stdout.strip():
        return _UNCOMMITTED
    head = subprocess.run(  # noqa: S603 - 고정된 인자로 git을 실행한다
        ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return head.stdout.strip()


def _write(side: str, measured: dict[str, dict[str, Any]]) -> None:
    existing = (
        json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")) if EVIDENCE_PATH.exists() else {}
    )
    previous = {item["id"]: item for item in existing.get("items", [])}
    commit = BASELINE_COMMIT if side == "before" else _current_commit()
    items = []
    for definition in ITEMS:
        item = {
            **definition,
            **{key: previous.get(definition["id"], {}).get(key) for key in ("before", "after")},
        }
        item[side] = {"commit": commit, "values": measured[definition["scenario"]]}
        items.append(item)
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(
            {
                "version": 1,
                "synthetic": True,
                "generator": "apps/worker/tests/test_controlled_ai_evidence.py",
                "items": items,
                "upcoming": UPCOMING_STEPS,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# -- 테스트 ---------------------------------------------------------------------


def _evidence() -> dict[str, Any]:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("item", ITEMS, ids=lambda item: item["id"])
async def test_committed_after_values_match_the_current_code(item: dict[str, Any]) -> None:
    # 코드가 바뀌었는데 공개 화면의 수치가 그대로 남는 일을 막는다.
    committed = next(entry for entry in _evidence()["items"] if entry["id"] == item["id"])

    assert await SCENARIOS[item["scenario"]]() == committed["after"]["values"]


def test_evidence_definitions_match_the_generator() -> None:
    evidence = _evidence()

    assert evidence["synthetic"] is True
    assert evidence["upcoming"] == UPCOMING_STEPS
    for definition, committed in zip(ITEMS, evidence["items"], strict=True):
        assert {key: committed[key] for key in definition} == definition


@pytest.mark.parametrize("item", ITEMS, ids=lambda item: item["id"])
def test_each_item_records_a_real_before_and_after(item: dict[str, Any]) -> None:
    committed = next(entry for entry in _evidence()["items"] if entry["id"] == item["id"])
    keys = {metric["key"] for metric in item["metrics"]}

    assert committed["before"]["commit"] == BASELINE_COMMIT
    assert re.fullmatch(rf"[0-9a-f]{{7,40}}|{_UNCOMMITTED}", committed["after"]["commit"])
    assert set(committed["before"]["values"]) == keys
    assert set(committed["after"]["values"]) == keys
    # 전후가 같으면 그 항목은 통제의 효과를 보여주지 못한다.
    assert committed["before"]["values"] != committed["after"]["values"]


def test_committed_code_cannot_ship_with_uncommitted_evidence() -> None:
    # ⚠️ 측정 대상 코드가 커밋된 뒤에도 `uncommitted`가 남으면 task 7.3을 잊은 것이다. 이 검사가
    #    없으면 "커밋 전" 표시가 공개 쇼케이스에 그대로 배포된다. 작업 중에는 측정 대상이 더러워서
    #    `_current_commit`이 같은 값을 돌려주므로 통과한다.
    if _current_commit() == _UNCOMMITTED:
        pytest.skip("측정 대상 코드에 커밋되지 않은 변경이 있다")

    stale = [
        entry["id"] for entry in _evidence()["items"] if entry["after"]["commit"] == _UNCOMMITTED
    ]

    assert stale == [], "코드를 커밋했으면 증거를 다시 생성해 실제 해시를 기록해야 한다"


def test_upcoming_steps_carry_no_example_numbers() -> None:
    # 구현되지 않은 Step의 예시 수치가 실제 결과처럼 보이면 안 된다.
    for step in _evidence()["upcoming"]:
        assert set(step) == {"step", "title", "description"}
        assert not re.search(r"\d", step["title"] + step["description"])


_FORBIDDEN_PATTERNS = {
    "uuid": r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
    "email": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "openrouter_or_openai_key": r"\bsk-[A-Za-z0-9_-]{6,}",
    "supabase_key": r"\bsb_(?:secret|publishable)_[A-Za-z0-9_-]+",
    "langfuse_key": r"\b[ps]k-lf-[A-Za-z0-9_-]+",
    "jwt": r"\beyJ[A-Za-z0-9_-]{10,}",
    "bearer": r"(?i)\bbearer\s+\S+",
}


def test_evidence_contains_no_identifier_or_credential_shapes() -> None:
    text = EVIDENCE_PATH.read_text(encoding="utf-8")

    found = {name for name, pattern in _FORBIDDEN_PATTERNS.items() if re.search(pattern, text)}

    assert found == set()


@pytest.mark.parametrize(
    ("name", "sample"),
    [
        ("uuid", "7f3a19c2-1111-4222-8333-444455556666"),
        ("email", "someone@example.com"),
        ("openrouter_or_openai_key", "sk-or-v1-abcdef"),
        ("supabase_key", "sb_secret_abcdef"),
        ("langfuse_key", "sk-lf-abcdef"),
        ("jwt", "eyJhbGciOiJIUzI1NiJ9"),
        ("bearer", "Bearer abc"),
    ],
)
def test_forbidden_patterns_actually_match_their_shape(name: str, sample: str) -> None:
    # 정규식이 깨지면 위 검사는 아무것도 찾지 못하고 조용히 통과한다.
    assert re.search(_FORBIDDEN_PATTERNS[name], sample)


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "measure":
        Path(sys.argv[2]).write_text(json.dumps(_measure(), ensure_ascii=False), encoding="utf-8")
    elif command == "write":
        _write(sys.argv[2], json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")))
    else:
        raise SystemExit(f"알 수 없는 명령: {command}")
