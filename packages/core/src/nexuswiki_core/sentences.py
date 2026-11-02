"""CITE-05 답변 품질 지표용 한국어/영어 혼합 문장 분리기."""

from __future__ import annotations

import re

from nexuswiki_core.citations import BROAD_ANCHOR_PATTERN

__all__ = ["split_sentences"]

_ANCHOR: str = BROAD_ANCHOR_PATTERN.pattern

# Sentence-final punctuation: ASCII .!? plus full-width Korean/CJK 。！？, followed
# by optional closing quote/bracket, followed by whitespace, end of string, or a
# citation anchor glued to the punctuation.
# A negative lookbehind for a preceding digit avoids splitting "3.14" or "1."-style
# list markers; this is a bounded heuristic (CITE-05 is a quality metric, not a
# correctness-critical parse), not a linguistically complete sentence tokenizer.
_SENTENCE_BOUNDARY: re.Pattern[str] = re.compile(
    rf"(?<![0-9])[.!?。！？]+[\"'\)\]]*(?:\s+|$|(?={_ANCHOR}))"
)

_LEADING_ANCHORS: re.Pattern[str] = re.compile(rf"^(?:{_ANCHOR}\s*)+")


def split_sentences(text: str) -> list[str]:
    """Best-effort Korean/English/mixed sentence split. See CITE-05 rationale in
    05-RESEARCH.md Standard Stack > Alternatives Considered for why this is
    hand-rolled instead of pulling in `kss` (Korean morphological analyzer).

    ⚠️ 문장 부호 뒤의 앵커는 앞 문장의 근거다. 다음 문장에 붙이면 인용이 있는 문장은
    근거 없음으로, 없는 문장은 근거 있음으로 뒤바뀌어 지표가 조용히 틀린다
    (ai-control-flow-accounting design D6).
    """
    sentences: list[str] = []
    for raw_piece in _SENTENCE_BOUNDARY.split(text):
        piece = raw_piece.strip()
        if not piece:
            continue
        leading = _LEADING_ANCHORS.match(piece)
        if leading and sentences:
            sentences[-1] = f"{sentences[-1]} {leading.group(0).strip()}"
            piece = piece[leading.end() :].strip()
            if not piece:
                continue
        sentences.append(piece)
    return sentences
