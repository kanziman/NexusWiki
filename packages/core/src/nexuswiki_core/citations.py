"""서버 발급 인용 앵커의 두 정규식 문법 — 위조 제거용(broad)과 해소용(issued).

관련 태스크: 05-01-PLAN.md Task 2
설계 근거: 05-CONTEXT.md > D-02, D-03, D-04
설계 근거: 05-RESEARCH.md Architecture Patterns > Pattern 2

`worker.llm`의 `_PLACEHOLDER` 정규식/`render_template()`와 같은 house style —
stdlib 정규식 단일 스캔, 클래스 없는 순수 함수. `tokenizer.py`의 `bigram()`/`normalize()`와
같은 결이다.

⚠️ 이 둘은 **서로 다른 정규식이어야 한다.** 좁은 `ISSUED_ANCHOR_PATTERN`으로 CITE-06의
수집 시점 제거를 하면, `[[wiki:homepage]]`처럼 이 요청이 절대 발급하지 않을 형태의
위조 앵커가 그대로 통과한다 — 그리고 미래의 어느 요청에서 우연히 그 별칭이 실제로
발급되면(`w1`처럼 낮은 번호는 흔하다) 그 위조 앵커가 `parsed ∩ issued` 교집합을
통과해 조작된 인용처럼 보이게 된다. 그래서 수집 시점 제거는 **의도적으로 더 넓다.**
"""

from __future__ import annotations

import re

__all__ = [
    "BROAD_ANCHOR_PATTERN",
    "ISSUED_ANCHOR_PATTERN",
    "neutralize_anchor_brackets",
    "strip_forged_anchors",
]

# D-04 / CITE-06: 수집 시점 — 어떤 값이든 `[[wiki:...]]`/`[[src:...]]` 모양이면 매치한다.
# 의도적으로 관대하다.
BROAD_ANCHOR_PATTERN: re.Pattern[str] = re.compile(r"\[\[(?:wiki|src):[^\[\]]*\]\]")

# D-02 / D-03 / CITE-01~03: Ask 시점 — 이 서버가 이번 요청에서 실제로 발급하는 형태만
# 매치한다. 의도적으로 좁다.
ISSUED_ANCHOR_PATTERN: re.Pattern[str] = re.compile(r"\[\[(wiki:w\d+|src:s\d+)\]\]")


_MAX_STRIP_ROUNDS: int = 8
_BRACKET_RUN: re.Pattern[str] = re.compile(r"\[+")


def neutralize_anchor_brackets(text: str) -> str:
    """여는 괄호 연속을 하나로 줄여 어떤 앵커도 남거나 재조립되지 못하게 한다.

    ⚠️ `"[["`를 치환하는 방식은 괄호가 홀수 개일 때 앵커를 남긴다. 연속 자체를 없앤다.
    """
    return _BRACKET_RUN.sub("[", text)


def strip_forged_anchors(text: str) -> str:
    """CITE-06: 방금 수집한 원문에서 앵커 모양의 토큰을 전부 제거한다.

    ⚠️ `chunk_text()` 이전, 전체 추출 텍스트 위에서 **한 번만** 돌아야 한다 — 위조
    앵커가 청크 경계에 걸치면 청크별 정규식은 그것을 놓친다(D-04).
    """
    # ⚠️ 한 번 지우면 끝이 아니다. `[[wi[[wiki:w8]]ki:w1]]`은 안쪽을 지우면 `[[wiki:w1]]`로
    #    재조립되어 그 턴의 별칭으로 해소된다.
    # ⚠️ 끝날 때까지 반복하면 깊게 중첩한 입력의 비용이 제곱으로 늘어 이벤트 루프가 멈춘다.
    #    횟수를 제한하고, 그보다 깊으면 여는 괄호를 끊어 앵커가 될 수 없게 만든다.
    for _ in range(_MAX_STRIP_ROUNDS):
        stripped = BROAD_ANCHOR_PATTERN.sub("", text)
        if stripped == text:
            return text
        text = stripped
    return neutralize_anchor_brackets(text) if BROAD_ANCHOR_PATTERN.search(text) else text
