"""바이트 추출과 빈 문서 방지 품질 게이트의 계약 테스트."""

from __future__ import annotations

import unicodedata

import pytest

from nexuswiki_core.extract import (
    EXTRACTOR_VERSION,
    MIN_CHARS_PER_PAGE,
    MIN_TOTAL_CHARS,
    ExtractionQualityError,
    ExtractionResult,
    assert_extraction_quality,
    extract_text,
    significant_chars,
)


def _pdf_with_pages(*texts: str) -> bytes:
    """외부 PDF 생성기를 추가하지 않고, 테스트 안에서 텍스트 PDF를 조립한다."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", ""]
    page_refs: list[int] = []
    for text in texts:
        page_number = len(objects) + 1
        content_number = page_number + 1
        page_refs.append(page_number)
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET"
        objects.extend(
            [
                "<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font "
                "/Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] "
                f"/Contents {content_number} 0 R >>",
                f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream",
            ]
        )
    page_kids = " ".join(f"{item} 0 R" for item in page_refs)
    objects[1] = f"<< /Type /Pages /Kids [{page_kids}] /Count {len(page_refs)} >>"
    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for number, object_text in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{number} 0 obj\n{object_text}\nendobj\n".encode())
    xref = sum(len(part) for part in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    parts.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    parts.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return b"".join(parts)


def test_pdf_extracts_text_and_actual_page_count() -> None:
    result = extract_text(
        data=_pdf_with_pages("first page", "second page"), mime_type="application/pdf"
    )

    assert result.page_count == 2
    assert "first page" in result.text
    assert "second page" in result.text


@pytest.mark.parametrize("mime_type", ["text/plain", "text/markdown"])
def test_plain_and_markdown_decode_as_single_page(mime_type: str) -> None:
    result = extract_text(data="한글 문서".encode(), mime_type=mime_type)

    assert result.text == "한글 문서"
    assert result.page_count == 1


def test_plain_text_falls_back_to_cp949() -> None:
    assert extract_text(data="한글".encode("cp949"), mime_type="text/plain").text == "한글"


def test_html_drops_head_scripts_styles_and_comments() -> None:
    result = extract_text(
        data=(
            b"<html><head>hidden<style>also-hidden</style></head><body>shown"
            b"<script>secret()</script><!-- no --><p>next</p></body></html>"
        ),
        mime_type="text/html",
    )

    assert "shown" in result.text and "next" in result.text
    assert "hidden" not in result.text and "secret" not in result.text


@pytest.mark.parametrize(
    ("data", "mime_type", "reason"),
    [
        (b"", "text/plain", "empty_extraction"),
        (b"broken", "application/pdf", "unreadable_document"),
        (b"x", "image/png", "unsupported_mime"),
    ],
)
def test_extract_rejects_empty_broken_and_unsupported_inputs(
    data: bytes, mime_type: str, reason: str
) -> None:
    with pytest.raises(ExtractionQualityError, match=reason):
        extract_text(data=data, mime_type=mime_type)


def test_quality_accepts_exact_page_threshold() -> None:
    result = ExtractionResult("x" * (MIN_CHARS_PER_PAGE * 2), 2, EXTRACTOR_VERSION)
    assert_extraction_quality(result, min_total_chars=1)


def test_quality_rejects_one_character_below_page_threshold_with_metadata() -> None:
    result = ExtractionResult("x" * (MIN_CHARS_PER_PAGE * 2 - 1), 2, EXTRACTOR_VERSION)
    with pytest.raises(ExtractionQualityError, match="needs_ocr") as raised:
        assert_extraction_quality(result, min_total_chars=1)
    assert (raised.value.chars, raised.value.pages, raised.value.threshold) == (199, 2, 200)


def test_quality_rejects_document_total_below_minimum() -> None:
    with pytest.raises(ExtractionQualityError, match="needs_ocr"):
        assert_extraction_quality(
            ExtractionResult("x" * (MIN_TOTAL_CHARS - 1), 1, EXTRACTOR_VERSION)
        )


def test_quality_rejects_zero_pages() -> None:
    with pytest.raises(ExtractionQualityError, match="unreadable_document"):
        assert_extraction_quality(ExtractionResult("x" * MIN_TOTAL_CHARS, 0, EXTRACTOR_VERSION))


def test_significant_chars_ignores_all_whitespace_and_normalizes_equivalent_text() -> None:
    assert significant_chars(" \n　" * 25000) == 0
    assert significant_chars("é") == significant_chars(unicodedata.normalize("NFD", "é"))
