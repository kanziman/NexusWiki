"""색인 시점과 질의 시점이 함께 쓰는 한국어 bigram 토크나이저.

관련 태스크: P2-BE-02
설계 근거: 02-CONTEXT.md > D-19
"""

from __future__ import annotations

import unicodedata

TSV_TOKENIZER_VERSION: str = "bigram-nfkc-cf-v1"
# ⚠️ 이 상수는 문자열인데 `0002` 시점의 `source_chunks.tsv_tokenizer_version`
# (`0002_search_schema.sql:94`)과 `wiki_pages.tsv_tokenizer_version`(`:220`)은
# `smallint`다. 값을 그대로 쓸 수 없으며, `0007`이 두 컬럼을 `text`로 바꾼다.
# 근거: checklists.json > open_questions.

_BIGRAM_SIZE = 2


def normalize(text: str) -> str:
    """검색·슬러그가 공유하는 표준형으로 접는다.

    처리 순서가 결과를 바꾸므로 순서 자체를 계약으로 못 박는다.
    1. NFKC — 전각·호환 문자를 표준 형태로 모은다
    2. casefold — 라틴 대소문자를 접는다
    3. NFKC 재적용 — casefold가 호환 문자를 되살릴 수 있어, 없으면 멱등성이 깨진다
    4. 공백 정규화 — 모든 유니코드 공백류를 단일 스페이스로 접고 앞뒤를 제거한다
    """
    composed = unicodedata.normalize("NFKC", text)
    folded = unicodedata.normalize("NFKC", composed.casefold())
    return " ".join(folded.split())


def is_normalized(text: str) -> bool:
    """이미 `normalize()`를 통과한 문자열인지 판정한다."""
    return normalize(text) == text


def bigram(normalized: str) -> str:
    """정규화된 문자열을 공백으로 이어진 bigram 열로 바꾼다.

    ⚠️ 색인 시점과 질의 시점이 서로 다른 토크나이저를 쓰면 **오류 없이 조용히
    실패**한다. 그 실패는 검색 결과가 비는 형태로만 드러나 원인을 되짚기 어렵다.
    그래서 전제가 깨지면 반환값으로 알리지 않고 즉시 예외로 끊는다.
    근거: 02-CONTEXT.md > D-19.

    퇴화 입력의 반환값을 계약으로 고정한다 — 빈 문자열은 빈 문자열, 길이 1은 그
    글자 자체이며 둘 다 예외를 던지지 않는다.

    토큰 안에서만 bigram을 만들고 토큰 사이는 공백으로 잇는다. 질의 측이
    `phraseto_tsquery('simple', bigram(q))`로 `<->` 인접성까지 검사하기 때문에
    (`0002_search_schema.sql:78-88`) 이 경계가 어긋나면 부분 문자열 매칭 의미가
    보존되지 않는다.
    """
    if not is_normalized(normalized):
        raise ValueError(
            "bigram()은 정규화된 입력만 받는다 — normalize()를 먼저 통과시킬 것 "
            f"(tokenizer={TSV_TOKENIZER_VERSION})"
        )

    return " ".join(_token_bigrams(token) for token in normalized.split(" ") if token)


def _token_bigrams(token: str) -> str:
    if len(token) < _BIGRAM_SIZE:
        return token
    return " ".join(
        token[index : index + _BIGRAM_SIZE] for index in range(len(token) - _BIGRAM_SIZE + 1)
    )
