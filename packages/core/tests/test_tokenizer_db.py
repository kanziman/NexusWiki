"""DOM-06 왕복 자가검색을 실제 Postgres에 대고 확인하는 통합 회귀 테스트.

`test_tokenizer.py`의 `_phrase_matches`는 `phraseto_tsquery`의 `<->` 인접성을
파이썬으로 재현한 시뮬레이션이다. 시뮬레이션만 있으면 그 재현이 실제
Postgres 동작과 어긋나도 스위트가 계속 green이다 — 즉 "색인 시점과 질의 시점
토크나이저가 동일해야 함, 불일치는 조용히 실패함"이라는 바로 그 함정에
시뮬레이션 자신이 빠질 수 있다. 이 파일은 시뮬레이션을 실물에 못 박는다.

계약: `to_tsvector('simple', bigram(indexed)) @@ phraseto_tsquery('simple', bigram(query))`
(`0002_search_schema.sql:79-93`). 설계 근거: 02-CONTEXT.md > D-19.

⚠️ 로컬 psql이 없으므로 컨테이너 안의 psql을 쓴다. 스택이 없으면 에러가 아니라
**skip**이다 — 에러로 두면 스택이 없는 CI 러너에서 잡 전체가 red가 된다
(apps/api/tests/conftest.py:203 · apps/worker/tests/test_queue.py:482과 같은 관례).
"""

import shutil
import subprocess
import unicodedata

import pytest

from nexuswiki_core.tokenizer import bigram, normalize

_CONTAINER = "supabase_db_NexusWiki"
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


def _psql(sql: str) -> str:
    # 인자는 전부 이 파일이 만든 리터럴이고 셸을 거치지 않는다
    # (scripts/spike_db_transport.py:80-81과 같은 관례).
    completed = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "docker",
            "exec",
            "-i",
            _CONTAINER,
            "psql",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
            "-Atc",
            sql,
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"psql 실패: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _local_stack_is_up() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        _psql("select 1")
    except (OSError, subprocess.SubprocessError, RuntimeError):
        return False
    return True


@pytest.fixture(scope="module")
def db() -> None:
    if not _local_stack_is_up():
        pytest.skip(f"로컬 Supabase 스택이 응답하지 않는다: docker exec {_CONTAINER} psql")


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _matches(indexed: str, query: str) -> bool:
    """색인 문자열과 질의 문자열을 실제 tsvector/tsquery 계약에 태운다."""
    sql = (
        f"select to_tsvector('simple', {_quote(bigram(normalize(indexed)))})"
        f" @@ phraseto_tsquery('simple', {_quote(bigram(normalize(query)))})"
    )
    result = _psql(sql)
    assert result in {"t", "f"}, f"예상 밖 psql 출력: {result!r}"
    return result == "t"


@pytest.mark.usefixtures("db")
def test_three_unicode_forms_retrieve_each_other_in_postgres() -> None:
    forms = (
        unicodedata.normalize("NFC", _SENTENCE),
        unicodedata.normalize("NFD", _SENTENCE),
        _to_fullwidth(_SENTENCE),
    )
    assert len(set(forms)) == len(forms)

    for indexed in forms:
        for query in forms:
            assert _matches(indexed, query), f"{indexed!r} 색인이 {query!r} 질의를 못 찾았다"


@pytest.mark.usefixtures("db")
def test_substring_query_matches_indexed_row_in_postgres() -> None:
    for query in ("국어", unicodedata.normalize("NFD", "국어"), "검색", "한국어"):
        assert _matches("한국어 검색", query), f"부분 문자열 질의 {query!r}가 매치되지 않았다"


@pytest.mark.usefixtures("db")
def test_unrelated_query_does_not_match_in_postgres() -> None:
    # 비매치가 실제로 f로 돌아와야 위 매치들이 "전부 t"인 무의미한 테스트가 아니다.
    assert not _matches("한국어 검색", "일본어")


@pytest.mark.usefixtures("db")
def test_token_boundary_is_preserved_in_postgres() -> None:
    # ⚠️ 토큰 경계를 넘는 bigram을 만들면 "검색"과 "색어"가 인접으로 붙어
    #    존재하지 않는 구절이 매치된다. 실물에서 오탐이 없는지 확인한다.
    assert not _matches("한국어 검색", "어검")
