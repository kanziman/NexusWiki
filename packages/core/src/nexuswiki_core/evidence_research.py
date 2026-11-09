"""재검색의 고정 도구 계약. 설계: ask-evidence-research/design.md D2~D3."""

from __future__ import annotations

import json
from itertools import zip_longest
from typing import Any

from nexuswiki_core.rrf import EvidenceHit

SEARCH_EVIDENCE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_evidence",
        "description": (
            "첫 근거에 없는 비교 대상·시점·개념의 근거를 검색한다. 최대 두 번만 사용한다."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 500}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


def validate_calls(calls: list[dict[str, Any]]) -> list[str]:
    """배치 전체를 검증한 뒤 중복을 제거한다. 모델은 접근 범위를 지정할 수 없다."""
    if len(calls) > 2:
        raise ValueError("too_many_calls")
    queries = []
    for call in calls:
        function = call.get("function", {})
        if call.get("type") != "function" or function.get("name") != "search_evidence":
            raise ValueError("invalid_tool")
        try:
            arguments = json.loads(function["arguments"])
        except (KeyError, TypeError, json.JSONDecodeError):
            raise ValueError("invalid_arguments") from None
        if not isinstance(arguments, dict) or set(arguments) != {"query"}:
            raise ValueError("invalid_arguments")
        query = arguments["query"]
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 500:
            raise ValueError("invalid_query")
        if query.strip() not in queries:
            queries.append(query.strip())
    return queries


def merge_evidence(groups: list[list[EvidenceHit]]) -> list[EvidenceHit]:
    """서로 다른 쿼리의 RRF 점수를 비교하지 않고 순환 배치한다."""
    merged, seen = [], set()
    for row in zip_longest(*groups):
        for hit in row:
            if hit is not None and (hit.kind, hit.document_id) not in seen:
                seen.add((hit.kind, hit.document_id))
                merged.append(hit)
    return merged


class ToolCallCollector:
    """SSE 도구 인자 조각을 index별로 모으고 불완전·과대 응답을 거부한다."""

    def __init__(self) -> None:
        self.calls: dict[int, dict[str, Any]] = {}
        self.finished = False
        self.bytes = 0

    def feed(self, payload: dict[str, Any]) -> None:
        if payload.get("error"):
            raise ValueError("provider_error")
        for choice in payload.get("choices", []):
            if choice.get("index", 0) != 0:
                continue
            reason = choice.get("finish_reason")
            if reason is not None:
                if reason not in {"stop", "tool_calls"}:
                    raise ValueError("incomplete_decision")
                self.finished = True
            for delta in (choice.get("delta") or {}).get("tool_calls", []):
                index = delta.get("index")
                if type(index) is not int or index not in {0, 1}:
                    raise ValueError("too_many_calls")
                call = self.calls.setdefault(
                    index, {"type": "function", "function": {"name": "", "arguments": ""}}
                )
                if delta.get("type") not in {None, "function"}:
                    raise ValueError("invalid_tool")
                for key in ("name", "arguments"):
                    value = (delta.get("function") or {}).get(key, "")
                    if not isinstance(value, str):
                        raise ValueError("invalid_arguments")
                    self.bytes += len(value.encode())
                    if self.bytes > 8192:
                        raise ValueError("decision_too_large")
                    call["function"][key] += value

    def queries(self) -> list[str]:
        if not self.finished:
            raise ValueError("incomplete_decision")
        return validate_calls([self.calls[index] for index in sorted(self.calls)])
