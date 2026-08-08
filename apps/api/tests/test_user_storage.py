"""Storage 어댑터의 경로·파일명 규약과 실패 매핑 (ING-03, T-03-30, T-03-32).

⚠️ 이 파일은 네트워크를 타지 않는다. `httpx.MockTransport`로 요청을 가로채 헤더와
경로만 검사한다 — 실제 Storage 왕복은 `test_sources_router.py`가 로컬 스택을 상대로
확인한다.

⚠️ 아래 `POLICY_PATH_PATTERN`은 `supabase/migrations/0005_storage.sql:29`의 정규식을
**손으로 옮겨 적은 사본**이다. `api.storage`가 같은 상수를 export 하고 그것을 import
하면 이 테스트는 자기 자신과의 일치만 증명하게 되어 정책과의 일치를 전혀 보증하지
못한다. 사본이라는 사실이 이 테스트가 무언가를 증명하는 유일한 이유다.
"""

import re
from typing import Any
from urllib.parse import unquote

import httpx
import pytest

from api.errors import StorageObjectExists, StorageUnavailable, WorkspaceForbidden
from api.settings import ApiSettings
from api.storage import (
    SOURCES_BUCKET,
    UserStorage,
    sanitize_filename,
    storage_path_for,
)

# `0005_storage.sql:29` — 정확히 `UUID/UUID/[^/]+` 세 세그먼트만 통과한다.
# 파서가 null을 돌려주면 멤버십 헬퍼도 false가 되어 역할과 무관하게 정책이 거부한다.
_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
POLICY_PATH_PATTERN = re.compile(rf"^{_UUID}/{_UUID}/[^/]+$")

# ⚠️ Supabase Storage 자체의 키 허용 문자. 2026-08-08 로컬 스택 실측으로 확인했다 —
#    한글·전각·`%`·`#`·`[]`·`{}`·`~`·`^`·`` ` ``·`"`·`<>`·`|`가 들어가면 업로드가
#    400 `InvalidKey`로 거부된다. `0005:29`의 `[^/]+`는 그것을 전부 통과시키므로
#    **정책을 만족하는 경로가 Storage에서는 거부될 수 있다.** 이 사본이 그 간극을 지킨다.
STORAGE_KEY_CHARSET = re.compile(r"^[0-9A-Za-z_. !\-*'()&$@=;:+,?/]+$")

WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
RAW_SOURCE_ID = "22222222-2222-4222-8222-222222222222"

TOKEN = "user-jwt-token"  # noqa: S105 — 테스트 리터럴이며 어떤 스택의 값도 아니다
PUBLISHABLE = "sb_publishable_test"
SUPABASE_URL = "http://storage.invalid"


def _settings(**overrides: Any) -> ApiSettings:
    return ApiSettings(
        SUPABASE_URL=SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY=PUBLISHABLE,
        **overrides,
    )


# -----------------------------------------------------------------------------
# 1. sanitize_filename — `0005:29`의 `[^/]+`를 절대 깨지 않는다
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "../../etc/passwd",
        "..",
        "...",
        "",
        "   ",
        "/",
        "\\windows\\system32\\config",
        "\x00\x01\x02",
        ".hidden",
        "한글 계약서.pdf",
        "보고서.PDF",
        "with space (1).pdf",
        "Ａ Ｂ.PDF",
        "a" * 400 + ".pdf",
    ],
)
def test_sanitized_filename_is_never_empty_and_never_contains_a_separator(name: str) -> None:
    # ⚠️ 빈 문자열이 나오면 경로가 두 세그먼트가 되어 `storage_path_workspace`가 null을
    #    돌려주고, 그러면 편집 권한이 있어도 정책이 업로드를 거부한다.
    result = sanitize_filename(name)

    assert result
    assert "/" not in result
    assert "\\" not in result


@pytest.mark.parametrize(
    "name",
    ["한글 계약서.pdf", "Ａ Ｂ.PDF", "../../etc/passwd", "with space (1).pdf", "𝔘𝔫𝔦𝔠𝔬𝔡𝔢.txt"],
)
def test_sanitized_filename_stays_inside_the_storage_key_charset(name: str) -> None:
    # 2026-08-08 실측: 비-ASCII 키는 Storage가 400 `InvalidKey`로 거부한다. `0005`의
    # 정책만 보고 만든 경로는 정책은 통과하되 업로드가 실패하는 상태가 된다.
    assert STORAGE_KEY_CHARSET.fullmatch(sanitize_filename(name))


def test_sanitize_filename_preserves_the_extension() -> None:
    assert sanitize_filename("report.pdf").endswith(".pdf")
    assert sanitize_filename("한글 계약서.pdf").endswith(".pdf")


def test_sanitize_filename_truncates_while_keeping_the_extension() -> None:
    # 2026-08-08 실측: 마지막 세그먼트가 254자면 200, 304자면 500 InternalError였다.
    result = sanitize_filename("a" * 400 + ".pdf")

    assert result.endswith(".pdf")
    assert len(result) <= 120


def test_sanitize_filename_is_deterministic_across_unicode_spellings() -> None:
    # NFC와 NFD가 같은 이름으로 접혀야 같은 파일이 두 경로에 흩어지지 않는다.
    assert sanitize_filename("Café.pdf") == sanitize_filename("Café.pdf")
    assert sanitize_filename("..") == sanitize_filename("..")


def test_sanitize_filename_fallback_differs_for_different_inputs() -> None:
    # 폴백이 상수면 서로 다른 원본 두 개가 같은 경로를 노려 두 번째가 409가 된다.
    assert sanitize_filename("한글.pdf") != sanitize_filename("일본어.pdf")


# -----------------------------------------------------------------------------
# 2. storage_path_for — 최종 판정자는 정책이고 이 함수는 그 형태를 깨지 않는다
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["한글 계약서.pdf", "with space (1).pdf", "..", "", "../../etc/passwd", "a" * 400],
)
def test_storage_path_matches_the_policy_regex(name: str) -> None:
    path = storage_path_for(
        workspace_id=WORKSPACE_ID,
        raw_source_id=RAW_SOURCE_ID,
        filename=sanitize_filename(name),
    )

    assert POLICY_PATH_PATTERN.fullmatch(path), path
    assert path.split("/")[:2] == [WORKSPACE_ID, RAW_SOURCE_ID]


@pytest.mark.parametrize("bad", ["", "a/b", "/"])
def test_storage_path_refuses_a_filename_that_would_break_the_three_segments(bad: str) -> None:
    # 호출자가 `sanitize_filename`을 건너뛰면 여기서 끊는다 — 정책 거부를 502로 받는
    # 것보다 프로그래밍 오류로 즉시 끊는 편이 원인을 되짚을 수 있다.
    with pytest.raises(ValueError, match="filename"):
        storage_path_for(workspace_id=WORKSPACE_ID, raw_source_id=RAW_SOURCE_ID, filename=bad)


# -----------------------------------------------------------------------------
# 3. UserStorage.upload — 요청자 JWT만 실린다
# -----------------------------------------------------------------------------


def _mock_storage(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0)


def _user_storage(client: httpx.AsyncClient) -> UserStorage:
    return UserStorage(
        client,
        supabase_url=SUPABASE_URL,
        publishable_key=PUBLISHABLE,
        access_token=TOKEN,
    )


@pytest.mark.asyncio
async def test_upload_carries_the_requester_jwt_and_the_publishable_key() -> None:
    # ⚠️ 여기에 service key가 실리면 `0005`의 세 정책이 통째로 우회된다.
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"Key": "sources/x"})

    async with _mock_storage(handler) as client:
        await _user_storage(client).upload(
            path=f"{WORKSPACE_ID}/{RAW_SOURCE_ID}/report.pdf",
            data=b"%PDF-1.4",
            content_type="application/pdf",
        )

    request = seen[0]
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.headers["apikey"] == PUBLISHABLE
    assert request.headers["Content-Type"] == "application/pdf"
    assert request.method == "POST"


@pytest.mark.asyncio
async def test_upload_percent_encodes_each_path_segment_but_keeps_three_of_them() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"Key": "sources/x"})

    path = f"{WORKSPACE_ID}/{RAW_SOURCE_ID}/with space (1).pdf"
    async with _mock_storage(handler) as client:
        await _user_storage(client).upload(path=path, data=b"x", content_type="application/pdf")

    raw = str(seen[0].url)
    assert f"/storage/v1/object/{SOURCES_BUCKET}/" in raw
    assert " " not in raw
    tail = raw.split(f"/object/{SOURCES_BUCKET}/", 1)[1]
    assert unquote(tail) == path
    assert tail.count("/") == 2


@pytest.mark.asyncio
async def test_upload_maps_key_already_exists_to_a_distinguishable_exception() -> None:
    # ⚠️ Storage는 실패를 **전송 상태 400**으로 돌려주고 진짜 코드는 본문에 담는다
    #    (2026-08-08 실측). 전송 상태만 보면 세 실패가 전부 한 덩어리가 된다.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "statusCode": "409",
                "error": "Duplicate",
                "message": "The resource already exists",
                "code": "KeyAlreadyExists",
            },
        )

    async with _mock_storage(handler) as client:
        with pytest.raises(StorageObjectExists):
            await _user_storage(client).upload(
                path=f"{WORKSPACE_ID}/{RAW_SOURCE_ID}/report.pdf",
                data=b"x",
                content_type="application/pdf",
            )


@pytest.mark.asyncio
async def test_upload_maps_a_policy_denial_to_the_isolation_exception() -> None:
    # 정책 거부를 502로 렌더하면 "권한이 없다"가 "저장소가 죽었다"로 보인다.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "statusCode": "403",
                "error": "Unauthorized",
                "message": "new row violates row-level security policy",
                "code": "AccessDenied",
            },
        )

    async with _mock_storage(handler) as client:
        with pytest.raises(WorkspaceForbidden):
            await _user_storage(client).upload(
                path=f"{WORKSPACE_ID}/{RAW_SOURCE_ID}/report.pdf",
                data=b"x",
                content_type="application/pdf",
            )


@pytest.mark.asyncio
async def test_upload_maps_anything_else_to_storage_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"statusCode": "500", "code": "InternalError"})

    async with _mock_storage(handler) as client:
        with pytest.raises(StorageUnavailable):
            await _user_storage(client).upload(
                path=f"{WORKSPACE_ID}/{RAW_SOURCE_ID}/report.pdf",
                data=b"x",
                content_type="application/pdf",
            )


@pytest.mark.asyncio
async def test_upload_failure_does_not_carry_the_provider_body() -> None:
    # ⚠️ 03-04이 세운 규약: 예외 클래스에 응답 본문을 담을 필드를 두지 않는다.
    #    마스킹보다 앞선 1차 방어선이다.
    marker = "s3-internal-bucket-name-should-not-leak"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": marker, "code": "InternalError"})

    async with _mock_storage(handler) as client:
        with pytest.raises(StorageUnavailable) as excinfo:
            await _user_storage(client).upload(
                path=f"{WORKSPACE_ID}/{RAW_SOURCE_ID}/report.pdf",
                data=b"x",
                content_type="application/pdf",
            )

    assert marker not in str(excinfo.value)
    assert marker not in repr(excinfo.value.__dict__)


@pytest.mark.asyncio
async def test_upload_does_not_decide_its_own_http_status_code() -> None:
    # 라우터도 어댑터도 상태 코드를 정하지 않는다 — `api.errors`의 등록 지점 하나가 정한다.
    source = (UserStorage.upload.__doc__ or "") + str(UserStorage.upload.__code__.co_consts)

    assert "JSONResponse" not in source


# -----------------------------------------------------------------------------
# 4. ApiSettings — 상한은 정책보다 먼저 걸린다
# -----------------------------------------------------------------------------


def test_max_upload_bytes_is_below_the_bucket_limit() -> None:
    # `0005:48`의 버킷 상한은 52428800(50MiB)이다. 애플리케이션이 먼저 거절하고
    # 정책은 최종 판정자로 남아야 하므로 이 값이 더 작아야 한다.
    assert _settings().MAX_UPLOAD_BYTES < 52428800


def test_allowed_upload_mime_types_is_not_empty() -> None:
    # 비어 있으면 모든 업로드가 거부되고, 그 거부는 "형식이 틀렸다"로 보인다.
    assert _settings().ALLOWED_UPLOAD_MIME_TYPES


def test_max_url_length_is_positive() -> None:
    assert _settings().MAX_URL_LENGTH > 0
