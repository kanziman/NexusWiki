"""배포 메타데이터 — 설정 계층이 아니라 런타임 플랫폼이 소유하는 값.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-07, D-10

git SHA와 리슨 포트는 Railway가 주입하는 배포 메타데이터이지 애플리케이션 설정이
아니다. `BaseAppSettings`에 넣으면 "없으면 못 뜨는 값"이 되어 D-10의 기동 실패 규칙이
빌드 메타데이터에까지 번진다. 그래서 설정 계층 밖의 이 모듈 한 곳에서만 읽고,
api·worker 진입 경로는 반환값만 받는다 — 두 진입 경로에서 `os.environ`을 없애는
단일 지점이 여기다.
"""

from __future__ import annotations

import os

__all__ = ["UNKNOWN_GIT_SHA", "resolve_git_sha", "resolve_port"]

UNKNOWN_GIT_SHA = "unknown"
DEFAULT_PORT = 8000


def resolve_git_sha() -> str:
    """Railway 주입값을 우선하고, 없으면 수동 주입값, 그것도 없으면 `unknown`."""
    # 빈 문자열을 "설정되지 않음"과 같이 취급한다 — `BaseAppSettings`의 규칙과 동일.
    # Railway가 변수를 만들되 값을 비워 두는 경우가 실제로 있다.
    for key in ("RAILWAY_GIT_COMMIT_SHA", "GIT_SHA"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return UNKNOWN_GIT_SHA


def resolve_port(default: int = DEFAULT_PORT) -> int:
    """플랫폼이 지정한 리슨 포트. 값이 없거나 숫자가 아니면 기본값으로 떨어진다."""
    raw = os.environ.get("PORT", "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
