"""CITE-05 답변 품질 지표용 한국어/영어 혼합 문장 분리기."""

from __future__ import annotations

import re

__all__ = ["split_sentences"]

# Sentence-final punctuation: ASCII .!? plus full-width Korean/CJK 。！？, followed
# by optional closing quote/bracket, followed by whitespace or end of string.
# A negative lookbehind for a preceding digit avoids splitting "3.14" or "1."-style
# list markers; this is a bounded heuristic (CITE-05 is a quality metric, not a
# correctness-critical parse), not a linguistically complete sentence tokenizer.
_SENTENCE_BOUNDARY: re.Pattern[str] = re.compile(r"(?<![0-9])[.!?。！？]+[\"'\)\]]*(?:\s+|$)")


def split_sentences(text: str) -> list[str]:
    """Best-effort Korean/English/mixed sentence split. See CITE-05 rationale in
    05-RESEARCH.md Standard Stack > Alternatives Considered for why this is
    hand-rolled instead of pulling in `kss` (Korean morphological analyzer)."""
    pieces = _SENTENCE_BOUNDARY.split(text)
    return [piece.strip() for piece in pieces if piece.strip()]
