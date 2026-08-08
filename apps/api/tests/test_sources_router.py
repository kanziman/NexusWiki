"""수집 라우터의 거부 계약 회귀 테스트 (ING-01, ING-02, OPS-01).

⚠️ 로컬 스택이 없으면 skip된다 — `conftest.py`의 관례를 그대로 따른다. skip은
"검증했다"가 아니며 CI는 `-rs`로 사유를 출력한다
(docs/ops/ci-security-gate.md § DB 의존 테스트).

⚠️ 이 파일은 **LLM을 부르지 않는다.** 워커가 돌고 있지 않으므로 인큐된 `parse` 잡은
큐에 남았다가 워크스페이스 삭제의 cascade로 사라진다. 파이프라인이 실제로 도는 것은
`scripts/smoke_pipeline.sh`가 확인한다.
"""

from collections.abc import Callable
from typing import Any

import pytest

from api.errors import FORBIDDEN_BODY

SOURCES_PATH = "/workspaces/{workspace_id}/sources/text"

# 상한 경계를 정확히 때리기 위한 작은 값. 기본 500,000자를 그대로 왕복시키면 테스트가
# 느려지기만 하고 경계에 대해 아무것도 더 말해주지 않는다.
TINY_LIMIT = 64


def body(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": "수집 테스트", "text": "본문 한 줄."}
    payload.update(overrides)
    return payload


# -----------------------------------------------------------------------------
# 1. 자격증명과 격리 — 라우터는 어느 쪽도 스스로 판정하지 않는다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_without_credentials_is_unauthorized(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    victim, _ = two_workspaces_two_users

    async with authed_client(None) as client:
        response = await client.post(
            SOURCES_PATH.format(workspace_id=victim.workspace_id), json=body()
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cross_tenant_ingest_is_forbidden_with_a_fixed_body(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    # ⚠️ 본문이 고정 문자열이어야 한다. 테이블명·id·SQLSTATE 중 무엇이라도 실리면
    #    다른 테넌트의 리소스 존재 여부가 응답으로 새어나가 열거 공격이 성립한다.
    victim, attacker = two_workspaces_two_users

    async with authed_client(attacker) as client:
        response = await client.post(
            SOURCES_PATH.format(workspace_id=victim.workspace_id), json=body()
        )

    assert response.status_code == 403
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
            SOURCES_PATH.format(workspace_id=owner.workspace_id),
            json=body(created_by="00000000-0000-4000-8000-000000000000"),
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
            SOURCES_PATH.format(workspace_id=owner.workspace_id), json=body(text="")
        )

    assert response.status_code == 422


# -----------------------------------------------------------------------------
# 3. 입력 크기 상한 (OPS-01, T-03-24) — 경계는 포함이다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_text_one_char_over_the_limit_is_rejected(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users

    async with authed_client(owner, MAX_TEXT_CHARS=TINY_LIMIT) as client:
        response = await client.post(
            SOURCES_PATH.format(workspace_id=owner.workspace_id),
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
            SOURCES_PATH.format(workspace_id=owner.workspace_id),
            json=body(text="가" * TINY_LIMIT),
        )

    assert response.status_code == 202, response.text
    payload = response.json()
    assert set(payload) == {"job_id", "raw_source_id"}
    assert payload["job_id"] and payload["raw_source_id"]


# -----------------------------------------------------------------------------
# 4. 중복 수집 (ING-02) — 조용한 성공이 아니라 눈에 보이는 거부
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reingesting_the_same_text_returns_409_with_the_existing_id(
    two_workspaces_two_users: tuple[Any, ...],
    authed_client: Callable[..., Any],
) -> None:
    owner, _ = two_workspaces_two_users
    path = SOURCES_PATH.format(workspace_id=owner.workspace_id)

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
    path = SOURCES_PATH.format(workspace_id=owner.workspace_id)

    async with authed_client(owner) as client:
        first = await client.post(path, json=body(text="ＡＢＣ 문서"))
        second = await client.post(path, json=body(text="ABC 문서"))

    assert first.status_code == 202, first.text
    assert second.status_code == 409
