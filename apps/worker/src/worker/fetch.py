"""사용자 지정 URL을 SSRF 경계 뒤에서 유한하게 읽는다.

관련 태스크: P2-ING-01
설계 근거: 03-06-PLAN.md > D-P17
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit

import httpx

from nexuswiki_core.extract import SUPPORTED_MIME_TYPES
from worker.errors import UnsafeFetchTarget

if TYPE_CHECKING:
    from worker.settings import WorkerSettings

__all__ = ["FetchedSource", "UnsafeFetchTarget", "assert_public_target", "fetch_source"]


@dataclass(frozen=True)
class FetchedSource:
    data: bytes
    mime_type: str
    final_url: str


def assert_public_target(url: str, *, allow_private: bool) -> None:
    """URL 문법과 모든 DNS 결과가 외부 공인 주소인지 확인한다."""
    target = urlsplit(url)
    if target.scheme not in {"http", "https"}:
        raise UnsafeFetchTarget(reason="bad_scheme")
    if not target.hostname or target.username is not None or target.password is not None:
        raise UnsafeFetchTarget(reason="bad_target")
    if allow_private:
        return
    try:
        addresses = socket.getaddrinfo(target.hostname, target.port or 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise UnsafeFetchTarget(reason="unresolvable_target") from error
    for address in addresses:
        resolved = ipaddress.ip_address(address[4][0])
        # ⚠️ IPv4 매핑 IPv6를 풀지 않으면 ::ffff:127.0.0.1이 공개 주소로 통과한다.
        if resolved.version == 6 and resolved.ipv4_mapped is not None:
            resolved = resolved.ipv4_mapped
        if (
            resolved.is_private
            or resolved.is_loopback
            or resolved.is_link_local
            or resolved.is_reserved
            or resolved.is_multicast
            or resolved.is_unspecified
        ):
            raise UnsafeFetchTarget(reason="private_target")


async def fetch_source(
    client: httpx.AsyncClient,
    url: str,
    *,
    settings: WorkerSettings,
) -> FetchedSource:
    """자동 리다이렉트 없이 매 홉을 다시 검사해 지원 MIME 바이트를 읽는다."""
    current_url = url
    redirects = 0
    while True:
        assert_public_target(current_url, allow_private=settings.ALLOW_PRIVATE_FETCH_TARGETS)
        request = client.build_request("GET", current_url)
        # ⚠️ 자동 추적은 공개 URL이 사설 URL로 보내는 리다이렉트를 그대로 열어 버린다.
        async with client.stream(request.method, request.url, follow_redirects=False) as response:
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise UnsafeFetchTarget(reason="bad_redirect")
                if redirects >= settings.FETCH_MAX_REDIRECTS:
                    raise UnsafeFetchTarget(reason="too_many_redirects")
                redirects += 1
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            mime_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if mime_type not in SUPPORTED_MIME_TYPES:
                raise UnsafeFetchTarget(reason="unsupported_mime")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > settings.FETCH_MAX_BYTES:
                    raise UnsafeFetchTarget(reason="too_large")
            return FetchedSource(bytes(body), mime_type, str(response.url))
