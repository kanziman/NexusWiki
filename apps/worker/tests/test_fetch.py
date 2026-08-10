"""SSRF 경계와 유한 URL 페치 계약 — DNS와 HTTP 모두 로컬 mock으로만 검증한다."""

from __future__ import annotations

import socket
from types import SimpleNamespace

import httpx
import pytest

from worker.errors import UnsafeFetchTarget
from worker.fetch import assert_public_target, fetch_source


def _addresses(*values: str) -> list[tuple[object, ...]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (value, 443)) for value in values]


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "ALLOW_PRIVATE_FETCH_TARGETS": False,
        "FETCH_MAX_BYTES": 10,
        "FETCH_TIMEOUT_SECONDS": 20.0,
        "FETCH_MAX_REDIRECTS": 1,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://example.com", "ftp://example.com"])
def test_public_target_rejects_non_http_schemes(url: str) -> None:
    with pytest.raises(UnsafeFetchTarget, match="bad_scheme"):
        assert_public_target(url, allow_private=False)


@pytest.mark.parametrize("url", ["https:///no-host", "https://user:pass@example.com"])
def test_public_target_rejects_missing_host_and_userinfo(url: str) -> None:
    with pytest.raises(UnsafeFetchTarget, match="bad_target"):
        assert_public_target(url, allow_private=False)


def test_public_target_rejects_any_private_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *_args, **_kwargs: _addresses("8.8.8.8", "127.0.0.1")
    )
    with pytest.raises(UnsafeFetchTarget, match="private_target"):
        assert_public_target("https://example.com", allow_private=False)


def test_public_target_rejects_ipv4_mapped_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::ffff:127.0.0.1", 443, 0, 0))
        ],
    )
    with pytest.raises(UnsafeFetchTarget, match="private_target"):
        assert_public_target("https://example.com", allow_private=False)


def test_public_target_allows_private_addresses_only_for_local_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: _addresses("127.0.0.1"))
    assert_public_target("https://example.com", allow_private=True)


@pytest.mark.asyncio
async def test_fetch_rechecks_public_target_for_each_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def resolver(host: str, *_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
        return _addresses("127.0.0.1" if host == "private.invalid" else "8.8.8.8")

    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(302, headers={"Location": "https://private.invalid/x"})
        )
    ) as client:
        with pytest.raises(UnsafeFetchTarget, match="private_target"):
            await fetch_source(client, "https://public.invalid/start", settings=_settings())


@pytest.mark.asyncio
async def test_fetch_returns_bytes_mime_and_final_url_without_automatic_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: _addresses("8.8.8.8"))
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/final"})
        return httpx.Response(
            200, content=b"hello", headers={"Content-Type": "text/plain; charset=utf-8"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_source(client, "https://public.invalid/start", settings=_settings())

    assert (result.data, result.mime_type, result.final_url) == (
        b"hello",
        "text/plain",
        "https://public.invalid/final",
    )
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_fetch_rejects_too_many_redirects_too_large_and_unsupported_mime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: _addresses("8.8.8.8"))

    async def redirected(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "/again"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(redirected)) as client:
        with pytest.raises(UnsafeFetchTarget, match="too_many_redirects"):
            await fetch_source(client, "https://public.invalid/start", settings=_settings())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, content=b"x" * 11, headers={"Content-Type": "text/plain"}
            )
        )
    ) as client:
        with pytest.raises(UnsafeFetchTarget, match="too_large"):
            await fetch_source(client, "https://public.invalid/start", settings=_settings())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, content=b"x", headers={"Content-Type": "image/png"}
            )
        )
    ) as client:
        with pytest.raises(UnsafeFetchTarget, match="unsupported_mime"):
            await fetch_source(client, "https://public.invalid/start", settings=_settings())
