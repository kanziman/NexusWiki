"""도구 인자의 권한 주입과 조각난 호출·중복 근거를 검증한다."""

import json

import pytest

from nexuswiki_core.evidence_research import ToolCallCollector, merge_evidence, validate_calls
from nexuswiki_core.rrf import EvidenceHit


def call(arguments, name="search_evidence"):
    return {"type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


@pytest.mark.parametrize(
    "calls",
    [
        [call({"query": "old", "workspace_id": "foreign"})],
        [call({"query": "old", "jwt": "foreign"})],
        [call({"query": " "})],
        [call({"query": "x" * 501})],
        [call({"query": 3})],
        [call({"query": "ok"}, "read_source")],
        [call({"query": "a"}), call({"query": "b"}), call({"query": "c"})],
    ],
)
def test_reject_invalid_batch(calls):
    with pytest.raises(ValueError):
        validate_calls(calls)


def test_deduplicate_queries():
    assert validate_calls([call({"query": " old "}), call({"query": "old"})]) == ["old"]


def test_collect_interleaved_argument_fragments():
    collector = ToolCallCollector()
    for index, fragment in [(0, '{"query":'), (1, '{"query":"new"}'), (0, '"old"}')]:
        collector.feed(
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": index,
                                    "function": {
                                        "name": "search_evidence"
                                        if fragment.startswith("{")
                                        else "",
                                        "arguments": fragment,
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        )
    with pytest.raises(ValueError, match="incomplete"):
        collector.queries()
    collector.feed({"choices": [{"finish_reason": "tool_calls"}]})
    assert collector.queries() == ["old", "new"]


def test_round_robin_keeps_new_target_without_comparing_scores():
    first = [EvidenceHit.wiki(wiki_id="a", rank=1), EvidenceHit.wiki(wiki_id="b", rank=2)]
    extra = [EvidenceHit.wiki(wiki_id="c", rank=1), EvidenceHit.wiki(wiki_id="a", rank=2)]
    assert [hit.document_id for hit in merge_evidence([first, extra])] == ["a", "c", "b"]
