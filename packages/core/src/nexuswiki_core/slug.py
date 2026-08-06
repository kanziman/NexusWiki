"""LLM이 낸 title에서 결정적으로 위키 슬러그를 만든다.

관련 태스크: P2-LNK-01
설계 근거: 02-CONTEXT.md > D-20
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Collection

from nexuswiki_core.tokenizer import normalize

SLUG_VERSION: str = "slug_v1"
SLUG_MAX_LENGTH: int = 80

# ⚠️ 한글 음절을 로마자화하지 않고 그대로 남긴다. 로마자화 규칙이 여러 표준으로
# 갈려 "결정적 순수 함수"라는 DOM-07 요구와 충돌하고, 비-ASCII 제거 폴백을 쓰면
# 한국어 title 전체가 사라져 한국어 사용자만 읽을 수 없는 URL을 받게 된다 —
# 설계 의도의 정반대다. 근거: 02-CONTEXT.md > D-20.
# 경로 구분자(`/`)와 점(`.`)이 이 집합 밖이라 슬러그가 경로 조작 표면이 되지 않는다.
_DISALLOWED = re.compile(r"[^0-9a-z가-힣-]")
_HYPHEN_RUN = re.compile(r"-{2,}")

_FALLBACK_PREFIX = "page-"
_FALLBACK_HASH_LENGTH = 12


def slugify(*, title: str, taken: Collection[str]) -> str:
    """title에서 결정적 슬러그를 만들고 `taken`과 충돌하면 숫자 접미로 해소한다.

    `taken`은 호출자가 기존 `wiki_pages.slug`와 `wiki_links.target_slug`를 **합쳐**
    넘기는 집합이다. ⚠️ 한쪽만 보면 레드 링크가 기다리던 슬러그를 다른 페이지가
    가로채 링크가 엉뚱한 곳으로 해소된다. LLM은 `title`만 내고 슬러그를 소유하지
    않는다 — 이 함수가 소유한다. 근거: 02-CONTEXT.md > D-20.
    """
    base = _base_slug(title)
    reserved = set(taken)
    if base not in reserved:
        return base

    suffix = 2
    while True:
        candidate = f"{_truncate(base, SLUG_MAX_LENGTH - len(str(suffix)) - 1)}-{suffix}"
        if candidate not in reserved:
            return candidate
        suffix += 1


def _base_slug(title: str) -> str:
    normalized = normalize(title)
    hyphenated = normalized.replace(" ", "-")
    filtered = _DISALLOWED.sub("", hyphenated)
    collapsed = _HYPHEN_RUN.sub("-", filtered).strip("-")

    truncated = _truncate(collapsed, SLUG_MAX_LENGTH)
    if truncated:
        return truncated
    return _fallback_slug(normalized)


def _fallback_slug(normalized: str) -> str:
    """허용 문자가 하나도 남지 않았을 때만 쓰는 결정적 폴백.

    ⚠️ 빈 문자열을 절대 반환하지 않는다 — `wiki_links.target_slug`에
    `char_length(btrim(...)) > 0` CHECK가 걸려 있어 DB가 거부한다
    (`0002_search_schema.sql:170`).

    실행 간 시드가 바뀌는 `hash()`가 아니라 sha256을 쓴다. 정규화된 문자열을
    해싱하므로 같은 제목을 NFC·NFD·전각 중 무엇으로 써도 같은 폴백을 받는다.
    """
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{_FALLBACK_PREFIX}{digest[:_FALLBACK_HASH_LENGTH]}"


def _truncate(slug: str, limit: int) -> str:
    return slug[:limit].strip("-")
