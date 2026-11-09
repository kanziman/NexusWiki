"""재검색의 실행 상한·권한·타임아웃과 폴백을 검증한다."""

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from api.services.ask import AskService, ResearchDenied
from api.services.retrieval import strict_research_access
from nexuswiki_core.context_budget import allocate_ask_context_budget
from nexuswiki_core.rrf import EvidenceHit


class Db:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.calls = []

    async def rpc(self, function, *, params):
        self.calls.append((function, params))
        return [self.allowed]


class Model:
    def __init__(self, calls=None, status=200):
        self.calls, self.status, self.requests = calls or [], status, []
        self.drained = False

    @asynccontextmanager
    async def stream(self, **kwargs):
        self.requests.append(kwargs)

        async def lines():
            for index, arguments in enumerate(self.calls):
                yield "data: " + json.dumps(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": index,
                                            "type": "function",
                                            "function": {
                                                "name": "search_evidence",
                                                "arguments": json.dumps(arguments),
                                            },
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                )
            yield 'data: {"choices":[{"finish_reason":"tool_calls"}]}'
            yield "data: [DONE]"
            self.drained = True

        yield SimpleNamespace(status_code=self.status, aiter_lines=lines)


class TruncatedModel(Model):
    """q28 재현: 판단이 도구 없이 출력 상한에 닿아 `length`로 끝나고, 뒤이어 사용량이 온다."""

    @asynccontextmanager
    async def stream(self, **kwargs):
        self.requests.append(kwargs)

        async def lines():
            yield 'data: {"choices":[{"delta":{"content":"근거를 살펴보면"}}]}'
            yield 'data: {"choices":[{"finish_reason":"length"}]}'
            yield 'data: {"choices":[],"usage":{"prompt_tokens":6391,"completion_tokens":256}}'
            yield "data: [DONE]"
            self.drained = True

        yield SimpleNamespace(status_code=self.status, aiter_lines=lines)


async def research(model, db=None, error=None):
    workspace, seen = uuid4(), []
    initial = [EvidenceHit.wiki(wiki_id="new", rank=1)]

    async def retrieve(ws, query, k, user_db):
        seen.append((ws, query, user_db))
        if error:
            raise error
        return SimpleNamespace(
            candidates=[],
            evidence=[
                EvidenceHit.source(chunk_id="old", rank=1),
            ],
            meta={},
        )

    service = AskService(SimpleNamespace(retrieve=retrieve), model)
    report = {}
    result = await service._research(
        workspace_id=workspace,
        query="비교",
        user_db=db or Db(),
        requested_k=8,
        budget=allocate_ask_context_budget(initial, {"new": "새 방식 근거"}),
        initial=initial,
        report=report,
    )
    return result, report, seen, workspace


async def test_executes_only_model_query_with_original_workspace_and_db():
    model, db = Model([{"query": "기존 방식"}, {"query": "기존 방식"}]), Db()
    result, report, seen, workspace = await research(model, db)
    assert seen == [(workspace, "기존 방식", db)]
    assert {hit.document_id for hit in result} == {"old", "new"}
    assert report["executed_calls"] == 1
    assert model.requests[0]["evidence_research"] is True
    assert "새 방식 근거" in model.requests[0]["messages"][1]["content"]
    assert not strict_research_access.get()


async def test_rejects_entire_invalid_batch_before_search():
    _, report, seen, _ = await research(
        Model([{"query": "old"}, {"query": "x", "workspace_id": "bad"}])
    )
    assert not seen
    assert report["status"] == "decision_or_search_failed"
    assert report["failure_reason"] == "invalid_arguments"


async def test_truncated_decision_drains_stream_and_falls_back():
    model = TruncatedModel()
    result, report, seen, _ = await research(model)
    # 끝까지 읽어야 워커가 실사용량을 완전한 것으로 정산한다.
    assert model.drained
    assert not seen
    assert [hit.document_id for hit in result] == ["new"]
    assert report["status"] == "decision_or_search_failed"
    assert report["failure_reason"] == "incomplete_decision"


async def test_mid_stream_rejection_still_drains():
    # 세 번째 도구 호출(index 2)은 `feed` 도중 거부된다. 그 뒤 프레임도 읽어야 한다.
    model = Model([{"query": "a"}, {"query": "b"}, {"query": "c"}])
    _, report, seen, _ = await research(model)
    assert model.drained
    assert not seen
    assert report["failure_reason"] == "too_many_calls"


async def test_revoked_membership_stops_paid_search():
    with pytest.raises(ResearchDenied, match="forbidden"):
        await research(Model([{"query": "old"}]), Db(False))


async def test_sufficient_decision_does_not_search():
    result, report, seen, _ = await research(Model())
    assert not seen
    assert report["status"] == "sufficient"
    assert [hit.document_id for hit in result] == ["new"]


@pytest.mark.parametrize("status", [401, 402, 403])
async def test_worker_access_denial_is_not_swallowed(status):
    with pytest.raises(ResearchDenied):
        await research(Model(status=status))


async def test_timeout_falls_back_and_cancellation_propagates():
    result, report, _, _ = await research(Model([{"query": "old"}]), error=TimeoutError())
    assert [hit.document_id for hit in result] == ["new"]
    assert report["status"] == "timeout"
    with pytest.raises(asyncio.CancelledError):
        await research(Model([{"query": "old"}]), error=asyncio.CancelledError())
    assert not strict_research_access.get()
