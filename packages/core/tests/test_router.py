"""Router 판정 계약 (#163, #164)."""

from __future__ import annotations

import pytest

from nexuswiki_core.router import (
    AskRoute,
    CompileRoute,
    compile_fingerprint,
    decide_ask_route,
    decide_compile_route,
)
from nexuswiki_core.rrf import EvidenceHit


def _wiki(**metadata: str) -> EvidenceHit:
    return EvidenceHit.wiki(wiki_id="w", rank=1, metadata=metadata)


_SOURCE = EvidenceHit.source(chunk_id="s", rank=1)


def test_no_evidence_is_its_own_route() -> None:
    assert decide_ask_route("질문", []).decision == AskRoute.NO_EVIDENCE


@pytest.mark.parametrize(
    ("evidence", "reason"),
    [([_SOURCE], "source_only"), ([_wiki(title="제목")], "wiki_only")],
)
def test_one_kind_of_evidence_cannot_be_dual_cited(
    evidence: list[EvidenceHit], reason: str
) -> None:
    decision = decide_ask_route("제목", evidence)

    assert decision.decision == AskRoute.SINGLE_KIND
    assert decision.reason == reason


def test_exact_title_with_both_kinds_is_a_lookup() -> None:
    decision = decide_ask_route("  벡터   인덱스 ", [_wiki(title="벡터 인덱스"), _SOURCE])

    assert decision.decision == AskRoute.LOOKUP
    assert decision.reason == "exact_title_match"


def test_exact_slug_with_both_kinds_is_a_lookup() -> None:
    decision = decide_ask_route("OpenRouter", [_wiki(slug="openrouter"), _SOURCE])

    assert decision.decision == AskRoute.LOOKUP
    assert decision.reason == "exact_slug_match"


def test_a_source_title_does_not_make_a_lookup() -> None:
    source = EvidenceHit.source(chunk_id="s", rank=1, metadata={"title": "제목"})

    assert (
        decide_ask_route("제목", [_wiki(title="다른 문서"), source]).decision == AskRoute.STANDARD
    )


def test_ordinary_question_is_standard() -> None:
    decision = decide_ask_route("이 제품은 어떻게 동작하나요", [_wiki(title="제품"), _SOURCE])

    assert decision.as_report() == {"decision": "STANDARD", "reason": "default"}


def test_fingerprint_changes_with_each_input() -> None:
    base = {"content_hash": "h", "template_id": "t", "model": "m"}
    variants = [
        compile_fingerprint(**base),
        compile_fingerprint(**{**base, "content_hash": "h2"}),
        compile_fingerprint(**{**base, "template_id": "t2"}),
        compile_fingerprint(**{**base, "model": "m2"}),
    ]

    assert len(set(variants)) == 4
    assert compile_fingerprint(**base) == variants[0]


@pytest.mark.parametrize(
    ("previous", "truncated", "has_existing_pages", "expected"),
    [
        ("same", False, True, CompileRoute.SKIP_UNCHANGED),
        ("same", True, True, CompileRoute.SKIP_UNCHANGED),
        ("same", False, False, CompileRoute.STANDARD),
        ("same", True, False, CompileRoute.TRUNCATED),
        ("other", True, True, CompileRoute.TRUNCATED),
        (None, True, True, CompileRoute.TRUNCATED),
        (None, False, True, CompileRoute.STANDARD),
        ("other", False, True, CompileRoute.STANDARD),
    ],
)
def test_compile_route(
    previous: str | None,
    truncated: bool,
    has_existing_pages: bool,
    expected: CompileRoute,
) -> None:
    decision = decide_compile_route(
        fingerprint="same",
        previous_fingerprint=previous,
        truncated=truncated,
        has_existing_pages=has_existing_pages,
    )

    assert decision.decision == expected
