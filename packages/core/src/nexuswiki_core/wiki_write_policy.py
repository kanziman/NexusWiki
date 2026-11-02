"""컴파일의 위키 쓰기 위험 등급 분류.

관련 이슈: #198
설계 근거: openspec/changes/ai-control-risk-policy/design.md > D3
계약: openspec/changes/ai-control-risk-policy/specs/wiki-compilation/spec.md

소비자: `worker.handlers.compile`
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

__all__ = ["WikiWriteDecision", "WikiWriteRisk", "classify_wiki_write"]

# 이 비율 이하로 줄면 내용이 크게 사라진 것으로 본다.
_SHRINK_RATIO: Final[float] = 0.5


class WikiWriteRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class WikiWriteDecision:
    risk: WikiWriteRisk
    reason: str
    # 본문이 바뀌는 쓰기인가. 같은 본문이면 개정도 제안도 만들지 않는다.
    changed: bool


def classify_wiki_write(
    existing: Mapping[str, Any] | None,
    *,
    new_content: str,
    raw_source_id: str,
    published: bool,
) -> WikiWriteDecision:
    """기존 페이지와 새 본문을 비교해 등급을 정한다. 입력만 보는 순수 함수다."""
    if existing is None:
        return WikiWriteDecision(WikiWriteRisk.LOW, "new_page", changed=False)
    previous = str(existing.get("content") or "")
    if previous == new_content:
        return WikiWriteDecision(WikiWriteRisk.LOW, "unchanged", changed=False)
    if existing.get("verification_status") == "verified":
        return WikiWriteDecision(WikiWriteRisk.HIGH, "verified_page", changed=True)
    if published:
        return WikiWriteDecision(WikiWriteRisk.HIGH, "published_page", changed=True)
    sources = existing.get("sources")
    other_sources = [
        str(item)
        for item in (sources if isinstance(sources, list) else [])
        if str(item) != raw_source_id
    ]
    if other_sources:
        return WikiWriteDecision(WikiWriteRisk.MEDIUM, "other_source_page", changed=True)
    if previous and len(new_content) <= len(previous) * _SHRINK_RATIO:
        return WikiWriteDecision(WikiWriteRisk.MEDIUM, "large_shrink", changed=True)
    return WikiWriteDecision(WikiWriteRisk.LOW, "same_source_update", changed=True)
