"""원본 바이트에서 평문을 추출하고 빈 수집을 품질 게이트에서 끊는다.

관련 태스크: P2-ING-02
설계 근거: 03-06-PLAN.md > D-P14, D-P15, D-P16
설계 근거: checklists.json > decisions.original_file_retention

네트워크 경계는 이 모듈 밖에 있다. URL 페치는 `worker.fetch`가 맡고, 이 모듈은 이미
확보한 바이트만 평문으로 바꾼다. 소비자: 03-06의 `worker.handlers.parse`.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from typing import Final

from pypdf import PdfReader

from nexuswiki_core.tokenizer import normalize

__all__ = [
    "EXTRACTOR_VERSION",
    "MIN_CHARS_PER_PAGE",
    "MIN_TOTAL_CHARS",
    "SUPPORTED_MIME_TYPES",
    "ExtractionQualityError",
    "ExtractionResult",
    "assert_extraction_quality",
    "extract_text",
    "significant_chars",
]

EXTRACTOR_VERSION: Final[str] = "pypdf-html-plain-v1"
MIN_CHARS_PER_PAGE: Final[int] = 100
MIN_TOTAL_CHARS: Final[int] = 200
SUPPORTED_MIME_TYPES: Final[frozenset[str]] = frozenset(
    {"application/pdf", "text/plain", "text/markdown", "text/html"}
)
_TEXT_MIME_TYPES: Final[frozenset[str]] = frozenset({"text/plain", "text/markdown"})


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    page_count: int
    extractor: str


class ExtractionQualityError(Exception):
    """추출 결과가 재시도로 바뀌지 않는 품질 또는 형식 문제다."""

    def __init__(self, *, reason: str, chars: int = 0, pages: int = 0, threshold: int = 0) -> None:
        self.reason = reason
        self.chars = chars
        self.pages = pages
        self.threshold = threshold
        super().__init__(f"{reason} (chars={chars}, pages={pages}, threshold={threshold})")


class _TextExtractor(HTMLParser):
    """의존성을 늘리지 않는 최소 HTML 평문 추출기.

    본문 품질의 하한은 아래 품질 게이트가 지킨다. 이 단계에 세 번째 추출 패키지를
    추가할 근거가 없어 표준 라이브러리로 script/style/head와 주석만 확실히 제거한다.
    """

    _BLOCK_TAGS: Final[frozenset[str]] = frozenset(
        {
            "address",
            "article",
            "br",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "p",
            "section",
        }
    )
    _IGNORED_TAGS: Final[frozenset[str]] = frozenset({"head", "script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def significant_chars(text: str) -> int:
    """정규화한 텍스트의 공백 아닌 코드 포인트 수를 돌려준다."""
    # ⚠️ len(text)를 쓰면 스캔본의 레이아웃 공백이 상한을 넘어 게이트를 조용히 무력화한다.
    return sum(not character.isspace() for character in normalize(text))


def extract_text(*, data: bytes, mime_type: str) -> ExtractionResult:
    """지원 MIME 바이트를 평문과 실제 페이지 수로 바꾼다."""
    if not data:
        raise ExtractionQualityError(reason="empty_extraction")
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ExtractionQualityError(reason="unsupported_mime")
    if mime_type == "application/pdf":
        return _extract_pdf(data)
    if mime_type in _TEXT_MIME_TYPES:
        # 한국어 문서 현실의 계약 순서: UTF-8 → UTF-8 BOM → CP949.
        return ExtractionResult(_decode_text(data), 1, EXTRACTOR_VERSION)
    parser = _TextExtractor()
    parser.feed(_decode_text(data))
    parser.close()
    return ExtractionResult("".join(parser.parts), 1, EXTRACTOR_VERSION)


def assert_extraction_quality(
    result: ExtractionResult,
    *,
    min_chars_per_page: int = MIN_CHARS_PER_PAGE,
    min_total_chars: int = MIN_TOTAL_CHARS,
) -> None:
    """페이지·문서 하한을 통과하지 못한 추출을 사유 있는 예외로 끊는다."""
    if result.page_count <= 0:
        raise ExtractionQualityError(reason="unreadable_document", pages=result.page_count)
    chars = significant_chars(result.text)
    if chars < min_total_chars:
        raise ExtractionQualityError(
            reason="needs_ocr", chars=chars, pages=result.page_count, threshold=min_total_chars
        )
    threshold = min_chars_per_page * result.page_count
    # ⚠️ 나눗셈 반올림이 경계 판정을 바꾸지 않도록 정수 곱셈으로만 비교한다.
    if chars < threshold:
        raise ExtractionQualityError(
            reason="needs_ocr", chars=chars, pages=result.page_count, threshold=threshold
        )


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ExtractionQualityError(reason="unreadable_document")


def _extract_pdf(data: bytes) -> ExtractionResult:
    try:
        reader = PdfReader(BytesIO(data))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:  # noqa: BLE001 - 라이브러리 메시지를 jobs.last_error로 보내지 않는다.
        raise ExtractionQualityError(reason="unreadable_document") from error
    return ExtractionResult(text, len(reader.pages), EXTRACTOR_VERSION)
