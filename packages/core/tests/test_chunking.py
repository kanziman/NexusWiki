"""토큰 기준 청킹의 좌표 왕복 속성과 퇴화 입력 계약을 고정하는 회귀 테스트.

ING-05가 요구하는 속성은 하나다 — 어떤 원문에 대해서도
`content[chunk.char_start:chunk.char_end] == chunk.content` 가 성립한다.
이 값이 어긋나면 이중 Citation이 원문의 **엉뚱한 구간**을 가리키고, 그 실패는
오류 없이 "인용이 조금 이상한" 형태로만 드러난다.

외부 property 라이브러리를 들이지 않고 고정 코퍼스 + 고정 시드 생성 입력으로 같은
일을 한다 (`test_tokenizer.py`의 왕복 자가검색 테스트와 같은 결).
"""

import random

from nexuswiki_core.chunking import (
    CHUNK_OVERLAP_TOKENS,
    CHUNK_TARGET_TOKENS,
    CHUNKER_VERSION,
    Chunk,
    chunk_text,
    count_tokens,
)

_KOREAN = (
    "위키는 원문 청크와 컴파일된 페이지 양쪽으로 추적 가능해야 한다. "
    "이중 Citation이 무너지면 이 제품은 그냥 또 하나의 RAG 챗봇이다."
)
_ENGLISH = (
    "Retrieval augmented generation needs verifiable anchors. "
    "Without them the answer is indistinguishable from a fluent guess."
)
_FULLWIDTH = "ＮｅｘｕｓＷｉｋｉ　전각　혼합　입력　１２３４５６７８９０"
_EMOJI = "요약 ✅ 검증 🔍 링크 🔗 그래프 🕸️ 임베딩 🧮 재시도 ♻️"
_NO_SPACE = "가나다라마바사아자차카타파하" * 60
_MARKDOWN = "# 제목\n\n첫 문단이다.\n\n- 항목 하나\n- 항목 둘\n\n## 소제목\n\n마지막 문단."

_FIXED_CORPUS = (
    "",
    "   ",
    "\n\n\t  \n",
    "짧다",
    "a",
    _KOREAN,
    _ENGLISH,
    _FULLWIDTH,
    _EMOJI,
    _MARKDOWN,
    _NO_SPACE,
    _KOREAN * 12,
    _ENGLISH * 12,
    (_KOREAN + "\n\n" + _ENGLISH + "\n" + _EMOJI + "\n\n") * 8,
    _NO_SPACE + "\n\n" + _KOREAN * 6,
    ("문장. " * 400),
    ("word " * 1500),
)

_PIECES = (
    _KOREAN,
    _ENGLISH,
    _FULLWIDTH,
    _EMOJI,
    _MARKDOWN,
    "가나다라마바사아자차카타파하" * 15,
    "\n\n",
    "\n",
    " ",
    ". ",
    "짧은 조각.",
    "🧩",
    "ＡＢＣ",
)


def _generated_corpus(count: int) -> list[str]:
    """고정 시드 생성 입력. 한국어·영어·전각·이모지·개행·긴 무공백 토큰을 섞는다.

    ⚠️ `random`은 여기서 암호 용도가 아니라 **결정적 픽스처 생성기**로만 쓴다 —
    시드가 고정되어 있어 실행마다 같은 입력이 나온다.
    """
    rng = random.Random(20260808)  # noqa: S311
    corpus: list[str] = []
    for _ in range(count):
        piece_count = rng.randint(1, 60)  # noqa: S311
        corpus.append("".join(rng.choice(_PIECES) for _ in range(piece_count)))  # noqa: S311
    return corpus


def _assert_chunk_contract(content: str) -> None:
    chunks = chunk_text(content)

    if not content.strip():
        assert chunks == [], "공백뿐인 원문은 청크를 0개 만들어야 한다"
        return

    assert chunks, "내용이 있는 원문은 최소 1개의 청크를 만들어야 한다"

    for position, chunk in enumerate(chunks):
        assert isinstance(chunk, Chunk)
        # ING-05의 속성 — 좌표와 내용이 어긋나면 인용이 엉뚱한 구간을 가리킨다.
        assert content[chunk.char_start : chunk.char_end] == chunk.content
        # `source_chunks_char_range_check`(0002:99)가 빈 구간 행을 거부한다.
        assert chunk.char_end > chunk.char_start
        assert chunk.index == position
        assert count_tokens(chunk.content) <= CHUNK_TARGET_TOKENS

    starts = [chunk.char_start for chunk in chunks]
    assert starts == sorted(set(starts)), "char_start가 엄격히 증가하지 않는다"

    # 원문 전체가 덮여야 한다 — 빈틈이 있으면 그 구간은 검색에서 영원히 보이지 않는다.
    assert chunks[0].char_start == 0
    assert chunks[-1].char_end == len(content)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.char_start <= previous.char_end, "청크 사이에 빈틈이 있다"


def test_empty_content_produces_no_chunks() -> None:
    assert chunk_text("") == []


def test_whitespace_only_content_produces_no_chunks() -> None:
    for blank in ("   ", "\n", "   \n  ", "\t　 \n\n"):
        assert chunk_text(blank) == [], f"{blank!r}가 청크를 만들었다"


def test_short_content_becomes_exactly_one_chunk_covering_everything() -> None:
    content = _KOREAN
    assert count_tokens(content) <= CHUNK_TARGET_TOKENS

    chunks = chunk_text(content)

    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].char_start == 0
    assert chunks[0].char_end == len(content)
    assert chunks[0].content == content


def test_count_tokens_of_empty_string_is_zero() -> None:
    assert count_tokens("") == 0


def test_count_tokens_grows_with_content() -> None:
    assert count_tokens(_KOREAN) > 0
    assert count_tokens(_KOREAN * 4) > count_tokens(_KOREAN)


def test_fixed_corpus_satisfies_the_chunk_contract() -> None:
    for content in _FIXED_CORPUS:
        _assert_chunk_contract(content)


def test_generated_corpus_satisfies_the_chunk_contract() -> None:
    corpus = _generated_corpus(24)

    assert len(corpus) >= 20
    for content in corpus:
        _assert_chunk_contract(content)


def test_long_content_produces_multiple_chunks() -> None:
    content = _KOREAN * 20

    chunks = chunk_text(content)

    assert count_tokens(content) > CHUNK_TARGET_TOKENS
    assert len(chunks) > 1


def test_adjacent_chunks_overlap_on_prose_input() -> None:
    # 문단 경계에서 잘린 문장이 어느 한쪽 청크에는 온전히 들어가게 하는 것이 오버랩의 목적이다.
    content = (_KOREAN + "\n\n") * 30

    chunks = chunk_text(content)

    assert len(chunks) > 1
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.char_start < previous.char_end, "인접 청크가 겹치지 않는다"


def test_word_longer_than_target_is_split_without_raising() -> None:
    # 분리자가 하나도 없는 초장문. 강제 분할이 없으면 청크 하나가 상한을 넘거나 무한 루프가 된다.
    content = "가" * 6000

    chunks = chunk_text(content)

    assert len(chunks) > 1
    for chunk in chunks:
        assert count_tokens(chunk.content) <= CHUNK_TARGET_TOKENS
    _assert_chunk_contract(content)


def test_chunker_version_encodes_algorithm_tokenizer_and_parameters() -> None:
    # `TSV_TOKENIZER_VERSION`과 같은 규약 — 값이 결과를 바꾸는 축을 전부 인코딩해야
    # 나중에 재청킹 범위를 이 값으로 좁힐 수 있다 (02-CONTEXT.md > D-19).
    assert CHUNK_TARGET_TOKENS == 512
    assert CHUNK_OVERLAP_TOKENS == 64
    assert "cl100k" in CHUNKER_VERSION
    assert str(CHUNK_TARGET_TOKENS) in CHUNKER_VERSION
    assert str(CHUNK_OVERLAP_TOKENS) in CHUNKER_VERSION
    assert CHUNKER_VERSION == "recursive-cl100k-512-64-v1"


def test_chunk_is_frozen() -> None:
    chunk = chunk_text(_KOREAN)[0]

    try:
        chunk.index = 99  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("Chunk는 frozen dataclass여야 한다")
