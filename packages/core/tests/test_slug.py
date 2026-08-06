"""결정적 슬러그 생성의 회귀 테스트."""

import re
import unicodedata

from nexuswiki_core.slug import SLUG_MAX_LENGTH, SLUG_VERSION, slugify

_SLUG_SHAPE = re.compile(r"^[0-9a-z가-힣][0-9a-z가-힣-]*$")


def test_same_title_yields_the_same_slug_across_a_thousand_calls() -> None:
    results = {slugify(title="한국어 위키 제목", taken=()) for _ in range(1000)}

    assert len(results) == 1


def test_korean_title_is_not_degraded_to_hash() -> None:
    # ⚠️ 비-ASCII 제거 폴백을 쓰면 한국어 title 전체가 사라져 한국어 사용자만
    # 읽을 수 없는 URL을 받는다 — 설계 의도의 정반대다 (02-CONTEXT.md > D-20).
    slug = slugify(title="한국어 위키 제목", taken=())

    assert "한국어" in slug
    assert "위키" in slug
    assert "제목" in slug
    assert slug == "한국어-위키-제목"


def test_unicode_forms_of_the_same_title_share_one_slug() -> None:
    title = "한국어 Wiki 제목"
    forms = (
        unicodedata.normalize("NFC", title),
        unicodedata.normalize("NFD", title),
        "한국어　Ｗｉｋｉ　제목",
    )

    assert len({slugify(title=form, taken=()) for form in forms}) == 1


def test_spaces_become_hyphens_and_disallowed_characters_are_dropped() -> None:
    slug = slugify(title="한국어  Wiki / 제목!! v2", taken=())

    assert slug == "한국어-wiki-제목-v2"
    # 경로 구분자와 점이 남으면 슬러그가 URL 경로 조작 표면이 된다.
    assert "/" not in slug
    assert "." not in slug
    assert _SLUG_SHAPE.match(slug)


def test_long_title_is_capped_at_the_maximum_length() -> None:
    slug = slugify(title="가나다라마바사 " * 40, taken=())

    assert 0 < len(slug) <= SLUG_MAX_LENGTH
    assert not slug.endswith("-")


def test_collision_appends_two_then_three() -> None:
    first = slugify(title="제목", taken=())
    second = slugify(title="제목", taken=(first,))
    third = slugify(title="제목", taken=(first, second))

    assert first == "제목"
    assert second.endswith("-2")
    assert third.endswith("-3")
    assert len({first, second, third}) == 3


def test_collision_resolution_respects_the_length_cap() -> None:
    base = slugify(title="가나다라마바사 " * 40, taken=())
    resolved = slugify(title="가나다라마바사 " * 40, taken=(base,))

    assert resolved != base
    assert len(resolved) <= SLUG_MAX_LENGTH


def test_taken_may_merge_existing_slugs_and_wiki_link_target_slugs() -> None:
    # 호출자는 `wiki_pages.slug`와 `wiki_links.target_slug`를 **합쳐** 넘긴다.
    # 한쪽만 보면 레드 링크가 기다리던 슬러그를 다른 페이지가 가로챈다.
    existing_page_slugs = {"제목"}
    unresolved_target_slugs = {"제목-2"}
    taken = existing_page_slugs | unresolved_target_slugs

    slug = slugify(title="제목", taken=taken)

    assert slug == "제목-3"
    assert slug not in taken


def test_empty_normalization_uses_deterministic_fallback() -> None:
    slug = slugify(title="!!! ???", taken=())

    assert slug.strip()
    assert slug == slugify(title="!!! ???", taken=())
    assert _SLUG_SHAPE.match(slug)
    # 폴백은 허용 문자가 하나도 남지 않은 경우에만 쓴다 — 서로 다른 title은
    # 서로 다른 폴백을 받아야 페이지가 뭉개지지 않는다.
    assert slug != slugify(title="???", taken=())


def test_whitespace_only_title_still_returns_a_non_empty_slug() -> None:
    # `wiki_links.target_slug`에 char_length(btrim(...)) > 0 CHECK가 걸려 있어
    # 빈 슬러그는 DB에서 거부된다 (`0002_search_schema.sql:170`).
    slug = slugify(title="   \t　 ", taken=())

    assert slug.strip()
    assert _SLUG_SHAPE.match(slug)


def test_slug_version_is_pinned() -> None:
    assert SLUG_VERSION == "slug_v1"
