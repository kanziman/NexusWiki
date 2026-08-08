"""원문을 토큰 예산 안의 청크로 자르는 순수 함수와 그 버전 상수.

관련 태스크: P2-ING-02 (ING-05)
설계 근거: 03-03-PLAN.md > D-P4, D-P5
설계 근거: checklists.json > decisions.embedding_model

⚠️ **여기서 세는 토큰은 임베딩 모델이 실제로 세는 토큰이 아니다.** 청크 크기는
`tiktoken`의 `cl100k_base` BPE로 세는데, 임베딩 모델 bge-m3의 실제 토크나이저는
XLM-R SentencePiece다. 근사를 택한 이유와 그 방향(과대평가라 8192 예산을 넘길 위험이
구조적으로 없다)은 03-03-PLAN.md > D-P4에 있다 — 여기서 되풀이하지 않는다.
⚠️ 이 토크나이저는 `nexuswiki_core.tokenizer`의 bigram 토크나이저와도 **다른 것**이다.
저쪽은 `search_tsv` 색인·질의가 쓰고, 이쪽은 청크 크기만 센다. 둘을 섞으면 어느 쪽도
자기 목적을 달성하지 못한다.

⚠️ 한국어 청킹 파라미터(목표 512 · 오버랩 64)에는 문헌 근거가 없다. 읽을 만한 인용
단위와 배치 비용 사이의 경험적 출발점이며, Phase 4의 골든 질의 세트(RTV-06)가 반증할
대상이다. 그래서 값을 상수로 노출하고 `CHUNKER_VERSION`에 인코딩한다 — 값이 바뀌면
재청킹 범위를 그 문자열로 좁힐 수 있다 (02-CONTEXT.md > D-19가 세운 규약).

소비자: `worker.handlers.parse` (source_chunks 작성) · `worker.handlers.embed`
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Final

import tiktoken

__all__ = [
    "CHUNK_OVERLAP_TOKENS",
    "CHUNK_TARGET_TOKENS",
    "CHUNKER_VERSION",
    "Chunk",
    "chunk_text",
    "count_tokens",
]

CHUNKER_VERSION: Final[str] = "recursive-cl100k-512-64-v1"
# 알고리즘(recursive) + 토크나이저(cl100k) + 목표 토큰(512) + 오버랩(64)을 한 문자열에
# 담는다. `source_chunks.chunker_version`(`0007` §6)에 그대로 들어가며, 넷 중 하나라도
# 바뀌면 값이 달라져야 재청킹 대상을 이 값으로 조회할 수 있다.

CHUNK_TARGET_TOKENS: Final[int] = 512
CHUNK_OVERLAP_TOKENS: Final[int] = 64

_TOKENIZER_NAME: Final[str] = "cl100k_base"

# 분리자 우선순위. 앞에서부터 시도하고 그래도 목표를 넘으면 다음으로 내려간다.
# ⚠️ 마지막 빈 문자열은 "분리자 없이 강제로 자른다"는 뜻이다. 이것이 없으면 공백도
#    개행도 없는 초장문 입력에서 목표를 넘는 조각이 그대로 남거나 루프가 끝나지 않는다.
_SEPARATORS: Final[tuple[str, ...]] = ("\n\n", "\n", ". ", " ", "")


@dataclass(frozen=True, slots=True)
class Chunk:
    """원문의 한 구간. 좌표는 원문에 대한 **파이썬 코드 포인트** 인덱스다.

    `char_start`/`char_end`의 의미는 `source_chunks`(`0002_search_schema.sql:58-`)의
    같은 이름 컬럼과 정확히 같고, `content`는 그 구간을 다시 잘라낸 것이므로
    `원문[char_start:char_end] == content`가 항상 성립한다.
    """

    index: int
    content: str
    char_start: int
    char_end: int


@lru_cache(maxsize=1)
def _encoding() -> tiktoken.Encoding:
    """인코딩 객체를 첫 호출에 만들어 캐시한다.

    ⚠️ 모듈 전역에서 즉시 만들지 않는다. `tiktoken`은 인코딩을 처음 만들 때 BPE 어휘
    파일이 캐시에 없으면 인터넷으로 나가므로, 전역 생성은 **import가 네트워크를 타는**
    부작용이 된다. `worker.db.service`가 세운 "import에는 부작용을 두지 않는다" 규약과
    어긋나고, 테스트 수집만으로도 밖으로 나가게 된다.
    이미지에는 빌드 시점에 캐시를 굽는다 (`Dockerfile`의 `TIKTOKEN_CACHE_DIR`).
    """
    return tiktoken.get_encoding(_TOKENIZER_NAME)


def count_tokens(text: str) -> int:
    """`cl100k_base` 기준 토큰 수. 빈 문자열은 0이다."""
    if not text:
        return 0
    return len(_encoding().encode(text))


def chunk_text(content: str) -> list[Chunk]:
    """원문을 토큰 예산 안의 청크 열로 자른다.

    보장하는 계약:

    * 모든 청크에 대해 `content[c.char_start:c.char_end] == c.content`
    * 모든 청크가 `char_end > char_start` — ⚠️ 빈 구간 청크를 절대 만들지 않는다.
      `source_chunks_char_range_check`(`0002_search_schema.sql:99`)가 그런 행을 거부한다.
    * 모든 청크가 `count_tokens(c.content) <= CHUNK_TARGET_TOKENS`
    * `index`가 0부터 1씩 빈틈 없이 증가하고 `char_start`가 엄격히 증가한다
    * 첫 청크가 0에서 시작하고 마지막 청크가 `len(content)`에서 끝나며 사이에 빈틈이 없다
      — 덮이지 않은 구간은 검색에서 영원히 보이지 않는다

    퇴화 입력의 반환값도 계약이다:

    * 빈 원문과 공백뿐인 원문은 **빈 리스트**를 돌려준다
    * 한 청크에 들어가는 짧은 원문은 `[0, len(content))`를 덮는 청크 정확히 1개가 된다
    """
    if not content.strip():
        return []

    spans = _atomic_spans(content)
    token_counts = [count_tokens(content[start:end]) for start, end in spans]
    total_spans = len(spans)

    chunks: list[Chunk] = []
    start_index = 0
    previous_end_index = -1

    while start_index < total_spans:
        end_index = _pack(content, spans, token_counts, start_index)

        if end_index <= previous_end_index:
            # 오버랩으로 되돌아간 지점이 다음 조각을 담을 여유를 다 써 버린 경우다
            # (되돌린 구간 + 다음 조각이 목표를 넘는다). 그대로 두면 직전 청크에 완전히
            # 포함된 청크가 나오고 진전이 멈추므로, 이번 청크만 오버랩을 포기한다.
            start_index = previous_end_index + 1
            end_index = _pack(content, spans, token_counts, start_index)

        char_start = spans[start_index][0]
        char_end = spans[end_index][1]
        # ⚠️ 조각을 이어붙이지 않고 원문에서 **다시 잘라** 넣는다. 이어붙이면 분리자가
        #    소실되거나 중복되어 좌표와 내용이 어긋나고, ING-05의 왕복 속성이 깨진다.
        #    이 한 줄이 그 속성이 성립하는 유일한 구조적 이유다.
        chunks.append(
            Chunk(
                index=len(chunks),
                content=content[char_start:char_end],
                char_start=char_start,
                char_end=char_end,
            )
        )

        if end_index >= total_spans - 1:
            break

        previous_end_index = end_index
        start_index = max(start_index + 1, _overlap_start(token_counts, end_index))

    return chunks


def _pack(
    content: str,
    spans: list[tuple[int, int]],
    token_counts: list[int],
    start_index: int,
) -> int:
    """`start_index`부터 목표 토큰을 넘지 않는 마지막 조각의 인덱스를 돌려준다."""
    end_index = start_index
    running = token_counts[start_index]
    while (
        end_index + 1 < len(spans) and running + token_counts[end_index + 1] <= CHUNK_TARGET_TOKENS
    ):
        end_index += 1
        running += token_counts[end_index]

    # ⚠️ 조각별 토큰 수의 합은 근사다 — BPE는 조각 경계를 넘어 병합될 수 있어 실제 값과
    #    다를 수 있다. 상한은 합이 아니라 **실제로 센 값**으로 지켜야 하므로 확인 후 줄인다.
    #    조각 하나는 `_atomic_spans`가 이미 상한 이하임을 보장하므로 이 루프는 반드시 끝난다.
    while (
        end_index > start_index
        and count_tokens(content[spans[start_index][0] : spans[end_index][1]]) > CHUNK_TARGET_TOKENS
    ):
        end_index -= 1

    return end_index


def _overlap_start(token_counts: list[int], end_index: int) -> int:
    """오버랩 예산만큼 되돌아간 조각 인덱스.

    ⚠️ 예산으로만 되돌리면 **산문에서는 오버랩이 아예 생기지 않는다.** 조각 하나가
    문단 단위(수백 토큰)라 64토큰 예산에 들어가는 조각이 하나도 없기 때문이다. 그러면
    D-P5가 오버랩을 둔 이유("문단 경계에서 잘린 문장이 어느 한쪽 청크에는 온전히
    들어간다")가 조용히 사라진다 — 값은 설정되어 있는데 효과가 없는 상태다.
    그래서 예산과 무관하게 **마지막 조각 하나는 반드시 겹치게** 한다.

    청크가 조각 하나뿐일 때만 겹치지 않는다. 그 조각을 되풀이하면 다음 청크가 거의
    전부 오버랩이 되어 진전이 멈추기 때문이며, 그 경우는 호출자의 `previous_end_index`
    가드가 받는다.
    """
    index = end_index
    running = 0
    while index >= 0 and running + token_counts[index] <= CHUNK_OVERLAP_TOKENS:
        running += token_counts[index]
        index -= 1
    return min(end_index, index + 1)


def _atomic_spans(content: str) -> list[tuple[int, int]]:
    """원문을 각각 목표 토큰 이하인 조각들로 나눈다.

    조각들은 `[0, len(content))`를 **빈틈도 겹침도 없이** 덮는다. 분리자를 앞 조각에
    붙여 두기 때문이며, 그래야 조각 경계를 그대로 청크 경계로 쓸 수 있다.
    """
    return _split(content, 0, len(content), 0)


def _split(content: str, start: int, end: int, separator_index: int) -> list[tuple[int, int]]:
    if count_tokens(content[start:end]) <= CHUNK_TARGET_TOKENS:
        return [(start, end)]

    separator = _SEPARATORS[separator_index]
    if separator == "":
        return _force_split(content, start, end)

    pieces = _pieces(content[start:end], separator)
    if len(pieces) <= 1:
        return _split(content, start, end, separator_index + 1)

    spans: list[tuple[int, int]] = []
    for offset, length in pieces:
        spans.extend(_split(content, start + offset, start + offset + length, separator_index + 1))
    return spans


def _pieces(text: str, separator: str) -> list[tuple[int, int]]:
    """`separator`로 나누되 분리자를 **앞 조각에 붙여** 원문 좌표의 연속성을 지킨다."""
    parts = text.split(separator)
    pieces: list[tuple[int, int]] = []
    offset = 0
    last = len(parts) - 1
    for position, part in enumerate(parts):
        length = len(part) + (0 if position == last else len(separator))
        if length > 0:
            pieces.append((offset, length))
        offset += length
    return pieces


def _force_split(content: str, start: int, end: int) -> list[tuple[int, int]]:
    """분리자가 없는 구간을 반씩 갈라 목표 토큰 이하로 만든다.

    코드 포인트 하나가 목표 토큰을 넘을 수는 없으므로 재귀는 반드시 끝난다.
    """
    if count_tokens(content[start:end]) <= CHUNK_TARGET_TOKENS or end - start <= 1:
        return [(start, end)]
    middle = (start + end) // 2
    return _force_split(content, start, middle) + _force_split(content, middle, end)
