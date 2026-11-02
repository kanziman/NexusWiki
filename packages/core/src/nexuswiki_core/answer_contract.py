"""Ask 답변의 인용 계약 판정과 결정론적 Fallback.

관련 이슈: #190
설계 근거: openspec/changes/ai-control-output-contract/design.md > D5, D7
계약: openspec/changes/ai-control-output-contract/specs/grounded-answering/spec.md

⚠️ 판정은 턴 단위 두 코드만 쓴다. 문장 단위로 강제하면 연결 문장까지 위반으로 잡혀
멀쩡한 답변에 수리 호출 비용이 붙는다.

소비자: `api.services.ask`
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Final

from nexuswiki_core.citations import strip_forged_anchors
from nexuswiki_core.rrf import EvidenceHit
from nexuswiki_core.sentences import split_sentences

__all__ = [
    "FALLBACK_NOTICE",
    "VIOLATION_FABRICATED_ANCHOR",
    "VIOLATION_NO_CITATION",
    "build_fallback_answer",
    "check_answer_contract",
    "repair_instruction",
]

VIOLATION_NO_CITATION: Final[str] = "no_citation"
VIOLATION_FABRICATED_ANCHOR: Final[str] = "fabricated_anchor"

FALLBACK_NOTICE: Final[str] = (
    "인용 검증을 통과한 답변을 만들지 못해 관련 근거를 그대로 보여드립니다."
)

_FALLBACK_MAX_ITEMS: Final[int] = 6
_FALLBACK_SNIPPET_CHARS: Final[int] = 160

# 시드 템플릿이 지시한 문구(`0006:151,184`)와 그 변형. 문장 전체가 자료를 주어로 답을 못 한다고
# 밝힐 때만 근거 부족이다. 부분 일치를 쓰면 "문서를 찾을 수 없으면", "거부할 근거가 없습니다",
# "A는 되지만 B는 자료에서 찾을 수 없습니다"가 빠져나간다.
_ABSTENTION = re.compile(
    r"(?:이\s*(?:내용|질문)[은는]\s*)?(?:제공된\s*|주어진\s*)?"
    r"(?:(?:자료|컨텍스트)(?:만으로는?|로는?|에서는?)\s*"
    r"(?:이\s*질문에\s*|(?:(?:관련|해당)\s*)?(?:내용|정보)[을를]\s*)?"
    r"(?:알|찾을|확인할|답할|답변할)\s*수\s*없습니다"
    r"|(?:자료|컨텍스트)에[는서]?\s*(?:(?:해당|관련)\s*)?(?:(?:내용|정보|근거)[이가은는]?\s*)?없습니다"
    r"|(?:관련\s*)?근거가\s*없습니다)"
    r"[.!]?"
)
# 근거 부족 뒤에 올 수 있는 안내. 무엇이 있어야 답할 수 있는지만 말하는 문장이다 (`0006:151`).
_GUIDANCE = re.compile(
    r"(?:확인하려면|답하려면|답변하려면|알려면|있어야\s*(?:답|확인|알))"
    r"|(?:자료|데이터|문서|정보)(?:가|를)\s*(?:더\s*)?(?:필요|있어야|제공해\s*주)"
)
# ⚠️ `^\s*`는 줄바꿈을 먹어 빈 줄이 많은 입력에서 제곱 시간이 된다. 같은 줄의 공백만 본다.
_WORD = re.compile(r"\w")
_HEADING = re.compile(r"^[ \t]*#[^\n]*$", re.MULTILINE)


def _is_abstention(rendered_text: str) -> bool:
    """답변 전체가 근거 부족을 밝힐 때만 참이다.

    ⚠️ 표현이 어디에든 있으면 면제하면 단정 뒤에 "다만 배송비는 자료에서 찾을 수 없습니다"만
    붙인 답변이 인용 없이 정상 저장된다. 판정이 틀려도 수리 호출 1회가 더 들 뿐이다.
    제목 줄은 지우고 줄바꿈도 문장 경계로 본다. 목록은 마침표 없이 단정을 이어 붙일 수 있다.
    """
    body = _HEADING.sub("", rendered_text)
    sentences = [
        sentence.strip().strip("*_").strip()
        for line in body.splitlines()
        for sentence in split_sentences(line)
        if _WORD.search(sentence)
    ]
    if not sentences or not _ABSTENTION.fullmatch(sentences[0]):
        return False
    return all(_GUIDANCE.search(sentence) for sentence in sentences[1:])


def check_answer_contract(
    rendered_text: str,
    *,
    cited_anchor_count: int,
    fabricated_anchor_count: int,
) -> tuple[str, ...]:
    """위반 코드를 돌려준다. 비어 있으면 통과다."""
    violations: list[str] = []
    if fabricated_anchor_count > 0:
        violations.append(VIOLATION_FABRICATED_ANCHOR)
    if cited_anchor_count == 0 and not _is_abstention(rendered_text):
        violations.append(VIOLATION_NO_CITATION)
    return tuple(violations)


def repair_instruction(violations: tuple[str, ...], issued_aliases: list[str]) -> str:
    """수리 호출의 되먹임. 값 없이 위반 사유와 쓸 수 있는 앵커만 담는다."""
    reasons = {
        VIOLATION_NO_CITATION: "인용 앵커가 하나도 없습니다.",
        VIOLATION_FABRICATED_ANCHOR: "발급되지 않은 앵커를 썼습니다.",
    }
    lines = "\n".join(f"- {reasons.get(code, code)}" for code in violations)
    anchors = " ".join(
        f"[[wiki:{alias}]]" if alias.startswith("w") else f"[[src:{alias}]]"
        for alias in issued_aliases
    )
    return (
        "직전 답변이 인용 규칙을 어겼습니다.\n"
        f"{lines}\n\n"
        f"쓸 수 있는 앵커: {anchors}\n\n"
        "컨텍스트에 있는 내용만으로 답변을 다시 쓰고, 주장마다 위 앵커를 그대로 다세요. "
        '컨텍스트로 답할 수 없으면 "제공된 자료로는 알 수 없습니다"라고 쓰세요.'
    )


def _snippet(content: str) -> str:
    # ⚠️ 근거 본문의 앵커 문법을 지운다. 남기면 이 턴에 발급하지 않은 앵커가 답변에 실린다.
    cleaned = " ".join(strip_forged_anchors(content).split())
    if len(cleaned) <= _FALLBACK_SNIPPET_CHARS:
        return cleaned
    return cleaned[:_FALLBACK_SNIPPET_CHARS].rstrip() + "…"


def build_fallback_answer(
    evidence: list[EvidenceHit],
    issuance: Mapping[str, tuple[str, str]],
    content_by_id: Mapping[str, str],
) -> str:
    """상위 근거를 위키와 원문이 번갈아 나오게 나열한다.

    모델을 다시 부르지 않고 코드만으로 만든다. 앵커는 `issuance`에 있는 것만 쓰므로 위조가
    나올 수 없다. 번갈아 고르는 이유는 한 종류로 채우면 이중 Citation이 끊기기 때문이다.
    """
    alias_by_key = {(kind, real_id): alias for alias, (kind, real_id) in issuance.items()}
    wiki_lines: list[str] = []
    source_lines: list[str] = []
    for hit in evidence:
        if hit.kind == "wiki":
            alias = alias_by_key.get(("wiki", hit.document_id))
            if alias is None:
                continue
            # 제목도 모델이 쓴 값이다. 앵커가 남으면 이 턴의 별칭으로 해소되어 인용처럼 보인다.
            title = (
                strip_forged_anchors(str(hit.metadata.get("title") or "")).strip() or "위키 문서"
            )
            body = _snippet(content_by_id.get(hit.document_id, ""))
            wiki_lines.append(f"- {title}: {body} [[wiki:{alias}]]")
        else:
            alias = alias_by_key.get(("source", hit.evidence_id))
            if alias is None:
                continue
            body = _snippet(content_by_id.get(hit.evidence_id, "")) or "원문 근거"
            source_lines.append(f"- {body} [[src:{alias}]]")

    lines: list[str] = []
    for index in range(max(len(wiki_lines), len(source_lines))):
        lines.extend(wiki_lines[index : index + 1])
        lines.extend(source_lines[index : index + 1])
    return "\n\n".join([FALLBACK_NOTICE, "\n".join(lines[:_FALLBACK_MAX_ITEMS])]).strip()
