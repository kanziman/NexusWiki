"""수집 라우터 세 경로의 거부 계약 회귀 테스트 (ING-01, ING-02, ING-03, OPS-01).

⚠️ 로컬 스택이 없으면 skip된다 — `conftest.py`의 관례를 그대로 따른다. skip은
"검증했다"가 아니며 CI는 `-rs`로 사유를 출력한다
(docs/ops/ci-security-gate.md § DB 의존 테스트).

⚠️ 이 파일은 **LLM을 부르지 않는다.** 워커가 돌고 있지 않으므로 인큐된 `parse` 잡은
큐에 남았다가 워크스페이스 삭제의 cascade로 사라진다. 파이프라인이 실제로 도는 것은
`scripts/smoke_pipeline.sh`가 확인한다.

⚠️ 파일 경로는 **실제 Supabase Storage에 객체를 만든다.** 워크스페이스가 지워져도
`storage.objects`의 행은 cascade 대상이 아니므로 로컬 스택에 잔여 객체가 남는다 —
그 정리 스윕은 Phase 7의 일이며(D-P12), 로컬 개발 스택에서는 무해하다.
"""

import unicodedata
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest

from api.errors import FORBIDDEN_BODY

TEXT_PATH = "/workspaces/{workspace_id}/sources/text"
FILE_PATH = "/workspaces/{workspace_id}/sources/file"
URL_PATH = "/workspaces/{workspace_id}/sources/url"

# 상한 경계를 정확히 때리기 위한 작은 값. 기본값(500,000자 / 20MiB)을 그대로
# 왕복시키면 테스트가 느려지기만 하고 경계에 대해 아무것도 더 말해주지 않는다.
TINY_LIMIT = 64
TINY_UPLOAD_LIMIT = 1024

PDF = "application/pdf"


def body(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": "수집 테스트", "text": "본문 한 줄."}
    payload.update(overrides)
    return payload


def file_query(filename: str = "report.pdf", title: str = "보고서") -> dict[str, str]:
    return {"filename": filename, "title": title}


# 세 엔드포인트를 한 번에 도는 파라미터. 자격증명·격리 판정은 경로마다 다시 결정되는
# 것이 아니므로 셋 중 하나만 검사하면 나머지 둘이 조용히 빠진다.
THREE_ENDPOINTS = [
    pytest.param(TEXT_PATH, {"json": body()}, id="text"),
    pytest.param(
        FILE_PATH,
        {"params": file_query(), "content": b"%PDF-1.4 x", "headers": {"Content-Type": PDF}},
        id="file",
    ),
    pytest.param(URL_PATH, {"json": {"url": "https://example.test/doc"}}, id="url"),
]


# -----------------------------------------------------------------------------
# 1. 자격증명과 격리 — 라우터는 어느 쪽도 스스로 판정하지 않는다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(("path", "kwargs"), THREE_ENDPOINTS)
async def test_request_without_credentials_is_unauthorized(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    path: str,
    kwargs: dict[str, Any],
) -> None:
    victim, _ = two_workspaces_two_users

    async with authed_client(None) as client:
        response = await client.post(path.format(workspace_id=victim.workspace_id), **kwargs)

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(("path", "kwargs"), THREE_ENDPOINTS)
async def test_cross_tenant_ingest_is_forbidden_with_a_fixed_body(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    path: str,
    kwargs: dict[str, Any],
) -> None:
    # ⚠️ 본문이 고정 문자열이어야 한다. 테이블명·id·SQLSTATE 중 무엇이라도 실리면
    #    다른 테넌트의 리소스 존재 여부가 응답으로 새어나가 열거 공격이 성립한다.
    # ⚠️ 파일 경로는 `raw_sources`가 아니라 **Storage 정책**이 먼저 막는다 — 업로드가
    #    INSERT보다 앞이기 때문이다(D-P12). 그 거부가 502로 렌더되면 "권한이 없다"가
    #    "저장소가 죽었다"로 보이므로, 여기서 셋이 같은 403·같은 본문이어야 한다.
    victim, attacker = two_workspaces_two_users
    assert victim.workspace_id != attacker.workspace_id

    async with authed_client(attacker) as client:
        response = await client.post(path.format(workspace_id=victim.workspace_id), **kwargs)

    assert response.status_code == 403, response.text
    assert response.json() == FORBIDDEN_BODY


# -----------------------------------------------------------------------------
# 2. 요청 모델 — 모르는 필드를 조용히 버리지 않는다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_fields_are_rejected_rather_than_silently_dropped(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # `created_by`를 실은 요청이 "성공했는데 아무 일도 일어나지 않았다"로 보이면 안 되고,
    # 통과시키면 이 라우터가 곧 소유권 위조 경로가 된다. 둘 다 아니고 거절한다.
    owner, _ = two_workspaces_two_users

    async with authed_client(owner) as client:
        response = await client.post(
            TEXT_PATH.format(workspace_id=owner.workspace_id),
            json=body(created_by="00000000-0000-4000-8000-000000000000"),
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_fields_are_rejected_on_the_url_endpoint_too(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users

    async with authed_client(owner) as client:
        response = await client.post(
            URL_PATH.format(workspace_id=owner.workspace_id),
            json={"url": "https://example.test/a", "storage_path": "x/y/z"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_empty_text_is_rejected(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users

    async with authed_client(owner) as client:
        response = await client.post(
            TEXT_PATH.format(workspace_id=owner.workspace_id), json=body(text="")
        )

    assert response.status_code == 422


# -----------------------------------------------------------------------------
# 3. 입력 크기 상한 (OPS-01, T-03-24, T-03-31) — 경계는 포함이다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_text_one_char_over_the_limit_is_rejected(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users

    async with authed_client(owner, MAX_TEXT_CHARS=TINY_LIMIT) as client:
        response = await client.post(
            TEXT_PATH.format(workspace_id=owner.workspace_id),
            json=body(text="가" * (TINY_LIMIT + 1)),
        )

    assert response.status_code == 413
    assert response.json()["detail"] == "text_too_large"
    assert response.json()["limit"] == TINY_LIMIT


@pytest.mark.asyncio
async def test_text_exactly_at_the_limit_is_accepted_and_enqueued(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # ⚠️ 길이는 **코드 포인트** 기준이다. 한글 한 글자는 UTF-8에서 3바이트이므로,
    #    바이트로 재는 구현이라면 이 요청이 상한의 세 배로 세어져 거부된다.
    owner, _ = two_workspaces_two_users

    async with authed_client(owner, MAX_TEXT_CHARS=TINY_LIMIT) as client:
        response = await client.post(
            TEXT_PATH.format(workspace_id=owner.workspace_id),
            json=body(text="가" * TINY_LIMIT),
        )

    assert response.status_code == 202, response.text
    payload = response.json()
    assert set(payload) == {"job_id", "raw_source_id"}
    assert payload["job_id"] and payload["raw_source_id"]


@pytest.mark.asyncio
async def test_upload_exactly_at_the_byte_limit_is_accepted(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # ⚠️ 업로드 상한의 단위는 **바이트**다 — 텍스트 상한(코드 포인트)과 축이 다르다.
    owner, _ = two_workspaces_two_users

    async with authed_client(owner, MAX_UPLOAD_BYTES=TINY_UPLOAD_LIMIT) as client:
        response = await client.post(
            FILE_PATH.format(workspace_id=owner.workspace_id),
            params=file_query(),
            content=b"x" * TINY_UPLOAD_LIMIT,
            headers={"Content-Type": PDF},
        )

    assert response.status_code == 202, response.text
    assert set(response.json()) == {"job_id", "raw_source_id"}


@pytest.mark.asyncio
async def test_upload_one_byte_over_the_limit_is_rejected(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # 이 거부는 **버퍼링 이후의 사후 통보가 아니라** 누적치가 상한을 넘는 순간 일어난다
    # (D-P11 (2), T-03-31). 그 조기 중단이 multipart를 쓰지 않은 이유다.
    owner, _ = two_workspaces_two_users

    async with authed_client(owner, MAX_UPLOAD_BYTES=TINY_UPLOAD_LIMIT) as client:
        response = await client.post(
            FILE_PATH.format(workspace_id=owner.workspace_id),
            params=file_query(),
            content=b"x" * (TINY_UPLOAD_LIMIT + 1),
            headers={"Content-Type": PDF},
        )

    assert response.status_code == 413
    assert response.json()["detail"] == "payload_too_large"
    assert response.json()["limit"] == TINY_UPLOAD_LIMIT


@pytest.mark.asyncio
async def test_zero_byte_upload_is_rejected(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # 빈 원문이 조용히 수집되면 `parse`가 추출 실패로 dead에 수렴하고 사용자는
    # "올렸는데 아무 일도 안 일어난다"만 보게 된다.
    owner, _ = two_workspaces_two_users

    async with authed_client(owner) as client:
        response = await client.post(
            FILE_PATH.format(workspace_id=owner.workspace_id),
            params=file_query(),
            content=b"",
            headers={"Content-Type": PDF},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_source", "reason": "empty_body"}


@pytest.mark.asyncio
async def test_unsupported_mime_is_rejected_without_reflecting_the_request(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # ⚠️ `reason`은 짧은 고정 토큰이어야 한다. 요청 헤더나 본문의 조각을 실으면 그
    #    자체가 반사형 노출 경로가 된다 (T-03-34).
    owner, _ = two_workspaces_two_users
    marker = "reflect-me-please"

    async with authed_client(owner) as client:
        response = await client.post(
            FILE_PATH.format(workspace_id=owner.workspace_id),
            params=file_query(filename=f"{marker}.svg"),
            content=b"<svg/>",
            headers={"Content-Type": f"image/svg+xml; boundary={marker}"},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_source", "reason": "unsupported_mime"}
    assert marker not in response.text


@pytest.mark.asyncio
async def test_mime_parameters_do_not_break_the_allow_list(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # `text/plain; charset=utf-8`이 허용 목록과 맞지 않아 거부되면, 브라우저가 보내는
    # 정상 요청이 전부 422가 된다.
    owner, _ = two_workspaces_two_users

    async with authed_client(owner) as client:
        response = await client.post(
            FILE_PATH.format(workspace_id=owner.workspace_id),
            params=file_query(filename="note.txt", title="메모"),
            content="한 줄 메모".encode(),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    assert response.status_code == 202, response.text


# -----------------------------------------------------------------------------
# 4. 중복 수집 (ING-02) — 조용한 성공이 아니라 눈에 보이는 거부
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reingesting_the_same_text_returns_409_with_the_existing_id(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users
    path = TEXT_PATH.format(workspace_id=owner.workspace_id)

    async with authed_client(owner) as client:
        first = await client.post(path, json=body())
        second = await client.post(path, json=body())

    assert first.status_code == 202, first.text
    assert second.status_code == 409
    assert second.json()["detail"] == "already_ingested"
    # 노출되는 id는 요청자 **자신의** 워크스페이스 안의 행이다 (T-03-26).
    assert second.json()["raw_source_id"] == first.json()["raw_source_id"]


@pytest.mark.asyncio
async def test_the_duplicate_key_is_the_normalised_text_not_the_raw_bytes(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # `content_hash`는 정규화된 문자열의 sha256이므로 전각·반각 표기 차이가 같은
    # 해시로 접힌다. 접히지 않으면 같은 글을 다른 입력기로 붙여 넣을 때마다 새
    # 원문이 생기고 컴파일 비용이 그만큼 늘어난다.
    owner, _ = two_workspaces_two_users
    path = TEXT_PATH.format(workspace_id=owner.workspace_id)

    async with authed_client(owner) as client:
        first = await client.post(path, json=body(text="ＡＢＣ 문서"))
        second = await client.post(path, json=body(text="ABC 문서"))

    assert first.status_code == 202, first.text
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_reuploading_the_same_bytes_returns_409_with_the_existing_id(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users
    path = FILE_PATH.format(workspace_id=owner.workspace_id)
    data = b"%PDF-1.4 same bytes twice"

    async with authed_client(owner) as client:
        first = await client.post(
            path, params=file_query(), content=data, headers={"Content-Type": PDF}
        )
        second = await client.post(
            path, params=file_query(), content=data, headers={"Content-Type": PDF}
        )

    assert first.status_code == 202, first.text
    assert second.status_code == 409
    assert second.json()["detail"] == "already_ingested"
    assert second.json()["raw_source_id"] == first.json()["raw_source_id"]


@pytest.mark.asyncio
async def test_the_file_duplicate_key_comes_from_the_bytes_not_the_filename(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # ⚠️ 파일의 `content_hash`는 **원본 바이트**의 sha256이며 파일명은 들어가지 않는다.
    #    같은 파일을 NFC와 NFD 어느 표기의 이름으로 올려도 두 번째가 409여야 한다 —
    #    이름이 해시에 섞이면 표기만 다른 같은 파일이 두 번 컴파일된다.
    owner, _ = two_workspaces_two_users
    path = FILE_PATH.format(workspace_id=owner.workspace_id)
    data = b"%PDF-1.4 identical content"

    nfc = unicodedata.normalize("NFC", "Café 보고서.pdf")
    nfd = unicodedata.normalize("NFD", "Café 보고서.pdf")
    assert nfc != nfd

    async with authed_client(owner) as client:
        first = await client.post(
            path, params=file_query(filename=nfc), content=data, headers={"Content-Type": PDF}
        )
        second = await client.post(
            path, params=file_query(filename=nfd), content=data, headers={"Content-Type": PDF}
        )

    assert first.status_code == 202, first.text
    assert second.status_code == 409
    assert second.json()["raw_source_id"] == first.json()["raw_source_id"]


# -----------------------------------------------------------------------------
# 5. 원본 보존 (ING-03) — 경로는 `0005`가 최종 판정한다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uploaded_source_records_the_three_segment_storage_path(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    user_db: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users

    async with authed_client(owner) as client:
        response = await client.post(
            FILE_PATH.format(workspace_id=owner.workspace_id),
            params=file_query(filename="한글 계약서.pdf", title="계약서"),
            content=b"%PDF-1.4 stored",
            headers={"Content-Type": PDF},
        )

    assert response.status_code == 202, response.text
    raw_source_id = response.json()["raw_source_id"]

    async with user_db(owner) as db:
        rows = await db.select("raw_sources", match={"id": raw_source_id})

    row = rows[0]
    assert row["storage_path"].startswith(f"{owner.workspace_id}/{raw_source_id}/")
    assert row["storage_path"].count("/") == 2
    assert row["source_type"] == "file"
    assert row["mime_type"] == PDF
    assert row["byte_size"] == len(b"%PDF-1.4 stored")
    # 사람이 읽는 원래 이름은 Storage 키가 아니라 여기에 남는다 — 키는 ASCII
    # 부분집합으로 접히므로 한글이 살아남지 못한다.
    assert row["metadata"]["original_filename"] == "한글 계약서.pdf"
    # ⚠️ `content = ""`는 "아직 추출되지 않음" sentinel이다 (03-06이 채운다).
    assert row["content"] == ""


# -----------------------------------------------------------------------------
# 6. URL 수집 (ING-01) — 요청 안에서 페치하지 않는다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "reason"),
    [
        pytest.param("file:///etc/passwd", "bad_url_scheme", id="file-scheme"),
        pytest.param("ftp://example.test/a", "bad_url_scheme", id="ftp-scheme"),
        pytest.param("https://user:secret@example.test/a", "url_credentials", id="credentials"),
        pytest.param("http://", "bad_url_host", id="no-host"),
    ],
)
async def test_unfetchable_urls_are_rejected_at_the_request_boundary(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    url: str,
    reason: str,
) -> None:
    # ⚠️ 자격증명을 담은 URL을 저장하면 그것이 `raw_sources.metadata`에 남고 워크스페이스
    #    멤버 SELECT로 노출된다 (T-03-36). 그래서 저장 전에 끊는다.
    owner, _ = two_workspaces_two_users

    async with authed_client(owner) as client:
        response = await client.post(
            URL_PATH.format(workspace_id=owner.workspace_id), json={"url": url}
        )

    assert response.status_code == 422, response.text
    assert response.json() == {"detail": "invalid_source", "reason": reason}
    assert "secret" not in response.text


@pytest.mark.asyncio
async def test_url_source_is_recorded_without_being_fetched(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    user_db: Callable[..., Any],
) -> None:
    # ⚠️ 이 호스트는 존재하지 않는다(`.test`는 예약 TLD다). 요청이 202로 돌아온다는
    #    사실 자체가 "요청 안에서 페치하지 않는다"의 증거다 — 페치했다면 DNS 실패로
    #    끊겼을 것이다. 권위 있는 SSRF 판정은 접속 시점의 워커 몫이다 (T-03-37).
    owner, _ = two_workspaces_two_users
    url = "https://nonexistent.example.test/doc"

    async with authed_client(owner) as client:
        response = await client.post(
            URL_PATH.format(workspace_id=owner.workspace_id), json={"url": url}
        )

    assert response.status_code == 202, response.text
    async with user_db(owner) as db:
        rows = await db.select("raw_sources", match={"id": response.json()["raw_source_id"]})

    row = rows[0]
    assert row["source_type"] == "url"
    assert row["storage_path"] is None
    assert row["metadata"]["url"] == url
    assert row["content"] == ""
    # `raw_sources.title`이 not null이므로 제목이 없으면 URL이 제목이 된다.
    assert row["title"] == url


@pytest.mark.asyncio
async def test_url_longer_than_the_limit_is_rejected(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users

    async with authed_client(owner, MAX_URL_LENGTH=64) as client:
        response = await client.post(
            URL_PATH.format(workspace_id=owner.workspace_id),
            json={"url": "https://example.test/" + "a" * 64},
        )

    assert response.status_code == 422
    assert response.json()["reason"] == "url_too_long"


# -----------------------------------------------------------------------------
# 7. 비용 상한 (OPS-01) — 거부되는 것은 인큐이지 수집이 아니다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enqueue_over_the_budget_is_refused_with_402(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    set_workspace_budget: Callable[..., None],
) -> None:
    # 상한 비교는 **포함**이다(`0009:295`, `spent >= cap`). 지출이 0이어도 상한이 0이면
    # 거부된다 — 사용 기록을 위조하지 않고 이 경계를 정확히 겨냥한다.
    owner, _ = two_workspaces_two_users
    set_workspace_budget(owner, 0)

    async with authed_client(owner) as client:
        response = await client.post(TEXT_PATH.format(workspace_id=owner.workspace_id), json=body())

    assert response.status_code == 402, response.text
    # ⚠️ 본문에 지출액도 상한도 싣지 않는다. 금액 표면은 03-07이 소유한다 (T-03-35).
    assert response.json() == {"detail": "budget_exceeded"}


@pytest.mark.asyncio
async def test_the_source_row_survives_a_budget_refusal(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    set_workspace_budget: Callable[..., None],
    user_db: Callable[..., Any],
) -> None:
    # ⚠️ 402는 "수집이 실패했다"가 아니라 "인큐가 거부됐다"이다. `raw_sources` 행은
    #    남아야 한다 — 상한이 풀린 뒤 그 행을 다시 인큐할 수 있어야 하고, 행까지
    #    사라지면 사용자는 파일을 다시 올려야 한다. 응답과 DB 상태가 그 둘을 구분한다.
    owner, _ = two_workspaces_two_users
    set_workspace_budget(owner, 0)
    text = "상한 초과 뒤에도 남아야 하는 본문."

    async with authed_client(owner) as client:
        response = await client.post(
            TEXT_PATH.format(workspace_id=owner.workspace_id), json=body(text=text)
        )

    assert response.status_code == 402
    async with user_db(owner) as db:
        rows = await db.select(
            "raw_sources", match={"workspace_id": owner.workspace_id}, columns="id,content"
        )

    assert [row for row in rows if row["content"] == text], rows


@pytest.mark.asyncio
async def test_budget_refusal_also_covers_the_file_path(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    set_workspace_budget: Callable[..., None],
) -> None:
    # 상한이 텍스트 경로에만 걸리면 파일 업로드가 상한을 우회하는 통로가 된다.
    owner, _ = two_workspaces_two_users
    set_workspace_budget(owner, 0)

    async with authed_client(owner) as client:
        response = await client.post(
            FILE_PATH.format(workspace_id=owner.workspace_id),
            params=file_query(),
            content=b"%PDF-1.4 over budget",
            headers={"Content-Type": PDF},
        )

    assert response.status_code == 402, response.text
    assert response.json() == {"detail": "budget_exceeded"}


@pytest.mark.asyncio
async def test_delete_source_as_owner_succeeds(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    user_db: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(owner) as client:
        ingest_res = await client.post(
            TEXT_PATH.format(workspace_id=owner.workspace_id),
            json=body(title="삭제 대상 소스", text="삭제될 본문 내용"),
        )
        assert ingest_res.status_code == 202, ingest_res.text
        raw_source_id = ingest_res.json()["raw_source_id"]

        del_res = await client.delete(f"/workspaces/{owner.workspace_id}/sources/{raw_source_id}")
        assert del_res.status_code == 200, del_res.text
        assert del_res.json()["id"] == raw_source_id

    async with user_db(owner) as db:
        rows = await db.select(
            "raw_sources", match={"id": raw_source_id, "workspace_id": owner.workspace_id}
        )
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_delete_source_cross_tenant_is_forbidden(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    victim, attacker = two_workspaces_two_users
    async with authed_client(victim) as client:
        ingest_res = await client.post(
            TEXT_PATH.format(workspace_id=victim.workspace_id),
            json=body(title="피해자 소스", text="비공개 내용"),
        )
        assert ingest_res.status_code == 202
        raw_source_id = ingest_res.json()["raw_source_id"]

    async with authed_client(attacker) as client:
        del_res = await client.delete(f"/workspaces/{victim.workspace_id}/sources/{raw_source_id}")
        assert del_res.status_code == 403, del_res.text
        assert del_res.json() == FORBIDDEN_BODY


@pytest.mark.asyncio
async def test_delete_nonexistent_source_is_forbidden(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users
    non_existent_id = uuid4()
    async with authed_client(owner) as client:
        del_res = await client.delete(f"/workspaces/{owner.workspace_id}/sources/{non_existent_id}")
        assert del_res.status_code == 403, del_res.text
        assert del_res.json() == FORBIDDEN_BODY


@pytest.mark.asyncio
async def test_delete_source_cleans_up_wiki_sources_reference(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
    user_db: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users
    async with authed_client(owner) as client:
        ingest_res = await client.post(
            TEXT_PATH.format(workspace_id=owner.workspace_id),
            json=body(title="인용 대상 소스", text="참조될 본문"),
        )
        assert ingest_res.status_code == 202, ingest_res.text
        raw_source_id = ingest_res.json()["raw_source_id"]

    async with user_db(owner) as db:
        # wiki_page 하나 생성하고 sources 컬럼에 raw_source_id 연결
        page = await db.insert_one(
            "wiki_pages",
            values={
                "workspace_id": owner.workspace_id,
                "slug": f"test-page-{uuid4().hex[:8]}",
                "title": "테스트 위키 문서",
                "content": "이 문서는 소스를 참조합니다.",
                "category": "concepts",
                "sources": [raw_source_id, str(uuid4())],
                "created_by": owner.user_id,
            },
        )
        page_id = page["id"]

    async with authed_client(owner) as client:
        del_res = await client.delete(f"/workspaces/{owner.workspace_id}/sources/{raw_source_id}")
        assert del_res.status_code == 200, del_res.text

    async with user_db(owner) as db:
        pages = await db.select("wiki_pages", match={"id": str(page_id)})
        assert len(pages) == 1
        assert raw_source_id not in (pages[0].get("sources") or [])
