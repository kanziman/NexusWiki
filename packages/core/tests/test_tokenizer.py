"""색인과 질의가 공유하는 한국어 토크나이저의 회귀 테스트."""

import unicodedata

import pytest
from nexuswiki_core.tokenizer import (
    TSV_TOKENIZER_VERSION,
    bigram,
    is_normalized,
    normalize,
)

_SENTENCE = "한국어 Search 검색"


def _to_fullwidth(text: str) -> str:
    """ASCII 문자를 전각으로 바꾼다 — 전각 입력을 만들기 위한 테스트 헬퍼."""
    converted = []
    for char in text:
        if char == " ":
            converted.append("　")
        elif "!" <= char <= "~":
            converted.append(chr(ord(char) + 0xFEE0))
        else:
            converted.append(char)
    return "".join(converted)


def test_nfc_and_nfd_input_normalize_to_the_same_text() -> None:
    nfc = unicodedata.normalize("NFC", _SENTENCE)
    nfd = unicodedata.normalize("NFD", _SENTENCE)

    assert nfc != nfd
    assert normalize(nfc) == normalize(nfd)


def test_fullwidth_input_normalizes_to_the_same_text() -> None:
    fullwidth = _to_fullwidth(_SENTENCE)

    assert fullwidth != _SENTENCE
    assert normalize(fullwidth) == normalize(_SENTENCE)


def test_mixed_case_latin_is_casefolded() -> None:
    assert normalize("SeArCh Ko") == normalize("search ko")
    assert normalize("SeArCh Ko") == "search ko"


def test_whitespace_runs_collapse_and_edges_are_stripped() -> None:
    messy = "  한국어\t\t검색　　질의  "

    assert normalize(messy) == "한국어 검색 질의"


def test_normalize_is_idempotent() -> None:
    for raw in (
        _SENTENCE,
        unicodedata.normalize("NFD", _SENTENCE),
        _to_fullwidth(_SENTENCE),
        "  SeArCh\t\t한국어　 ",
        "",
    ):
        once = normalize(raw)

        assert normalize(once) == once
        assert is_normalized(once)


def test_bigram_rejects_input_that_was_not_normalized() -> None:
    # ⚠️ 이 거부가 없으면 색인/질의 토크나이저 불일치가 오류 없이 통과하고,
    # 검색 결과가 비는 형태로만 드러난다. 근거: 02-CONTEXT.md > D-19.
    decomposed = unicodedata.normalize("NFD", "한국어")

    assert not is_normalized(decomposed)
    with pytest.raises(ValueError, match="normalize"):
        bigram(decomposed)


def test_bigram_of_empty_string_is_empty_string() -> None:
    assert bigram("") == ""


def test_bigram_of_single_character_is_that_character() -> None:
    assert bigram("가") == "가"


def test_bigram_splits_each_token_and_keeps_token_boundaries() -> None:
    assert bigram(normalize("한국어 검색")) == "한국 국어 검색"


def test_tsv_tokenizer_version_encodes_algorithm_form_and_casefold() -> None:
    # 정규화 형식만 바뀌어도 값이 달라져야 재색인 범위를 좁힐 수 있다 (02-CONTEXT.md > D-19).
    assert TSV_TOKENIZER_VERSION == "bigram-nfkc-cf-v1"
