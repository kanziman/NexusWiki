"""요청을 어느 처리 경로로 보낼지 정하는 결정론적 판정.

관련 이슈: #163, #164
설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D7
계약: openspec/changes/ai-control-flow-accounting/specs/ai-request-tracing/spec.md

⚠️ 이 change에서는 판정을 **기록만** 한다. `NO_EVIDENCE` 외의 결정으로 LLM 호출을 건너뛰지
않는다. 실행 여부는 기록된 빈도를 보고 후속 Step에서 정한다.

소비자: `api.services.ask`, `worker.handlers.compile`
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from nexuswiki_core.rrf import EvidenceHit
from nexuswiki_core.tokenizer import normalize

__all__ = [
    "AskRoute",
    "CompileRoute",
    "RouteDecision",
    "compile_fingerprint",
    "decide_ask_route",
    "decide_compile_route",
]


class AskRoute(StrEnum):
    NO_EVIDENCE = "NO_EVIDENCE"
    LOOKUP = "LOOKUP"
    SINGLE_KIND = "SINGLE_KIND"
    STANDARD = "STANDARD"


class CompileRoute(StrEnum):
    SKIP_UNCHANGED = "SKIP_UNCHANGED"
    TRUNCATED = "TRUNCATED"
    STANDARD = "STANDARD"


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """결정과 사유 코드. 멤버에게 보이는 값이므로 본문을 담지 않는다."""

    decision: str
    reason: str

    def as_report(self) -> dict[str, str]:
        return {"decision": self.decision, "reason": self.reason}


def decide_ask_route(query: str, evidence: Sequence[EvidenceHit]) -> RouteDecision:
    """검색 직후의 Ask 경로를 판정한다.

    `LOOKUP`은 위키와 원문 근거가 모두 있을 때만 준다. 한쪽이 없으면 LLM 없이 내놓는 답이
    이중 Citation을 만족할 수 없기 때문이다. 별칭은 현재 근거 메타데이터에 없어서 제목과 slug만
    비교한다.
    """
    if not evidence:
        return RouteDecision(AskRoute.NO_EVIDENCE, "no_evidence")
    kinds = {hit.kind for hit in evidence}
    if len(kinds) == 1:
        return RouteDecision(AskRoute.SINGLE_KIND, f"{next(iter(kinds))}_only")
    wanted = normalize(query).casefold()
    for hit in evidence:
        if hit.kind != "wiki":
            continue
        for key in ("title", "slug"):
            value = hit.metadata.get(key)
            if isinstance(value, str) and normalize(value).casefold() == wanted:
                return RouteDecision(AskRoute.LOOKUP, f"exact_{key}_match")
    return RouteDecision(AskRoute.STANDARD, "default")


def compile_fingerprint(*, content_hash: str, template_id: str, model: str) -> str:
    """같은 입력의 재컴파일을 알아보는 지문. 셋 중 하나라도 바뀌면 값이 달라진다."""
    material = "\x1f".join((content_hash, template_id, model))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def decide_compile_route(
    *,
    fingerprint: str,
    previous_fingerprint: str | None,
    truncated: bool,
    has_existing_pages: bool = True,
) -> RouteDecision:
    """컴파일 호출 직전의 경로를 판정한다. 기존 위키 페이지가 있고 지문이 같으면 생략을 택한다."""
    if (
        has_existing_pages
        and previous_fingerprint is not None
        and fingerprint == previous_fingerprint
    ):
        return RouteDecision(CompileRoute.SKIP_UNCHANGED, "fingerprint_unchanged")
    if truncated:
        return RouteDecision(CompileRoute.TRUNCATED, "input_over_budget")
    return RouteDecision(CompileRoute.STANDARD, "default")
