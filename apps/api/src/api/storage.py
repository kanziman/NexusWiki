"""요청자 JWT로 원본 파일을 Supabase Storage에 올리는 어댑터와 경로·파일명 규약.

관련 태스크: P2-ING-01 (ING-03)
설계 근거: checklists.json > decisions.original_file_retention, decisions.db_access
설계 근거: 01-CONTEXT.md > D-05, D-07
설계 근거: 03-05-PLAN.md > D-P12 (Storage 업로드가 `raw_sources` INSERT보다 먼저인 이유)

`UserDb`(`api.db.user`)와 같은 형태를 따른다 — 클라이언트를 주입받고 모듈 전역을 두지
않으며, 실패를 스스로 HTTP 상태로 바꾸지 않고 `api.errors`의 단일 등록 지점에 넘긴다.

`0005_storage.sql`이 정책으로 강제하는 경로 규약을 애플리케이션이 **조립**하고,
**최종 판정자는 정책**이다. 이 파일이 하는 일은 정책이 통과시킬 수 있는 형태를 깨지
않는 것뿐이며, 그것을 보증하는 것은 이 코드가 아니라 정책이다.

소비자: `api.routers.sources`
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Final
from urllib.parse import quote

import httpx

from api.errors import (
    StorageObjectExists,
    StorageUnavailable,
    WorkspaceForbidden,
)
from nexuswiki_core.logging import get_logger
from nexuswiki_core.tokenizer import normalize

__all__ = [
    "SOURCES_BUCKET",
    "UPLOAD_TIMEOUT_SECONDS",
    "UserStorage",
    "sanitize_filename",
    "storage_path_for",
]

SOURCES_BUCKET: Final[str] = "sources"

# `0005_storage.sql:47-49`가 만든 비공개 버킷의 객체 테이블. 로그 필드로만 쓴다.
_OBJECTS_TABLE: Final[str] = "storage.objects"

_logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# 1. 파일명 정규화
# -----------------------------------------------------------------------------

# ⚠️ 이 허용 목록은 두 제약의 **교집합**이며 둘 중 하나만 보면 조용히 깨진다.
#
#    (1) `0005_storage.sql:29`의 정책 정규식은 마지막 세그먼트에 `[^/]+`만 요구한다 —
#        한글도 공백도 통과한다.
#    (2) 그러나 Supabase Storage 자신이 키 문자를 따로 제한한다. 2026-08-08 로컬 스택
#        실측: `한글.pdf` · `ＡＢ.pdf` · `%` · `#` · `[]` · `{}` · `~` · `^` · `` ` `` ·
#        `"` · `<>` · `|`를 담은 키는 업로드가 **400 `InvalidKey`로 거부된다.**
#
#    즉 정책을 만족하는 경로가 Storage에서는 거부될 수 있다. 정책만 보고 만든 한글
#    파일명은 "권한은 있는데 저장이 안 되는" 상태가 되고, 그 실패는 사용자에게
#    502로만 보인다.
#
#    아래 집합은 Storage 허용 집합의 **부분집합**이다. `&` `?` `+` `,` `;` `:` 처럼
#    Storage는 받아주지만 URL에서 의미를 갖는 문자를 일부러 뺐다 — 경로 세그먼트를
#    항상 percent-encode 하지만(`_encode_path`), 인코딩을 빠뜨린 호출자가 나중에
#    생기더라도 요청의 의미가 바뀌지 않게 하는 2차 방어다.
#
#    사람이 읽는 원래 이름은 버리지 않는다 — 라우터가 `raw_sources.metadata`의
#    `original_filename`에 정규화 **이전** 값을 그대로 보존한다.
_DISALLOWED_IN_FILENAME: Final[re.Pattern[str]] = re.compile(r"[^0-9A-Za-z_. -]")

# `..`가 경로 의미를 갖지 못하게 점 연속을 하나로 접는다.
_DOT_RUN: Final[re.Pattern[str]] = re.compile(r"\.{2,}")

# 2026-08-08 실측: 마지막 세그먼트 254자는 200, 304자는 500 `InternalError`였다.
# 경계 근처가 아니라 넉넉히 아래로 잡는다 — 백엔드(로컬 파일 vs S3)마다 세는 단위가
# 다르고, 상한을 바짝 붙이면 그 차이가 곧 운영 사고가 된다.
_FILENAME_MAX_LENGTH: Final[int] = 120

# 이보다 긴 마지막 점 뒤 문자열은 확장자가 아니라 이름의 일부로 본다.
_SUFFIX_MAX_LENGTH: Final[int] = 16

_FALLBACK_PREFIX: Final[str] = "source-"
_FALLBACK_HASH_LENGTH: Final[int] = 12

# ⚠️ `app.state.http_client`의 앱 전역 타임아웃은 2.0초다(`api.main:31`). 그 값은
#    "이 라우터의 왕복은 전부 PostgREST"라는 전제 위에 있었는데, 업로드는 그 전제를
#    깬다 — 20MiB를 싱가포르로 밀어 넣는 데 2초는 부족하고, 그 초과는 사용자에게
#    "저장소 장애"로 보인다.
#    그래서 이 호출에만 별도 상한을 준다. 늘려도 되는 이유는 이 왕복이 **계산 가능하게
#    유한**하기 때문이다 — 최대 바이트가 `MAX_UPLOAD_BYTES`로 미리 잘려 있다. LLM 호출은
#    그렇지 않으므로 여전히 워커의 일이며, 이 예외를 근거로 라우터에 무한정 긴 왕복을
#    들이면 ING-01("요청은 즉시 202")이 무너진다.
UPLOAD_TIMEOUT_SECONDS: Final[float] = 30.0


def sanitize_filename(name: str) -> str:
    """Storage 키로 안전한 파일명을 결정적으로 만든다.

    ⚠️ **빈 문자열을 절대 돌려주지 않는다.** 빈 이름은 경로를 두 세그먼트로 만들고,
    그러면 `storage_path_workspace`(`0005:22-33`)가 null을 돌려주며, null을 받은 멤버십
    헬퍼는 false를 돌려주므로 **편집 권한이 있어도** 업로드가 거부된다. 같은 이유로
    `slug.py:63-74`가 같은 규약을 쓴다.

    처리 순서가 결과를 바꾸므로 순서 자체를 계약으로 못 박는다.
    1. `normalize()` — NFKC + casefold + 공백 접기. 전각·NFD 표기가 여기서 접힌다
    2. 허용 목록 밖 문자 제거 — 경로 구분자(`/` `\\`)·제어문자·비-ASCII가 여기서 사라진다
    3. 점 연속 접기 — `..`가 경로 의미를 갖지 못하게 한다
    4. 확장자 분리 후 각각의 앞뒤 점·공백 제거
    5. 이름이 비면 정규화된 원본에서 유도한 결정적 폴백으로 대체
    6. 확장자를 남기고 전체 길이를 상한으로 자름
    """
    normalized = normalize(name)
    flattened = _DOT_RUN.sub(".", _DISALLOWED_IN_FILENAME.sub("", normalized))

    stem, suffix = _split_suffix(flattened)
    stem = stem.strip(" .")
    suffix = suffix.strip(" .")

    if not stem:
        stem = _fallback_stem(normalized)

    if not suffix:
        return stem[:_FILENAME_MAX_LENGTH]

    keep = _FILENAME_MAX_LENGTH - len(suffix) - 1
    if keep < 1:
        # 확장자만으로 상한을 다 쓰는 병적인 입력. 이름 쪽을 살린다.
        return stem[:_FILENAME_MAX_LENGTH]
    return f"{stem[:keep]}.{suffix}"


def _split_suffix(name: str) -> tuple[str, str]:
    """마지막 점을 기준으로 이름과 확장자를 나눈다.

    이름 쪽이 비어도(`한글.pdf`가 2단계에서 `.pdf`가 된 경우) 확장자를 살린다 —
    거기서 확장자를 버리면 `pdf`라는 이름의 확장자 없는 파일이 남아 워커가 형식을
    되짚을 단서를 잃는다.
    """
    stem, dot, suffix = name.rpartition(".")
    if not dot or not suffix or len(suffix) > _SUFFIX_MAX_LENGTH:
        return name, ""
    return stem, suffix


def _fallback_stem(normalized: str) -> str:
    """허용 문자가 하나도 남지 않았을 때만 쓰는 결정적 폴백.

    실행 간 시드가 바뀌는 `hash()`가 아니라 sha256을 쓴다 — 같은 원본 이름이 항상 같은
    폴백을 받아야 재업로드가 같은 경로를 노린다. 상수 하나로 두지 않는 이유는, 그러면
    서로 다른 두 원본이 같은 경로를 노려 둘째가 `KeyAlreadyExists`로 실패하기 때문이다.
    """
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{_FALLBACK_PREFIX}{digest[:_FALLBACK_HASH_LENGTH]}"


# -----------------------------------------------------------------------------
# 2. 경로 조립
# -----------------------------------------------------------------------------


def storage_path_for(*, workspace_id: str, raw_source_id: str, filename: str) -> str:
    """`{workspace_id}/{raw_source_id}/{filename}` 세 세그먼트를 만든다.

    `0005_storage.sql:29`의 정규식을 그대로 옮겨 적는다 — 이 형태만 통과한다::

        ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}
        /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}
        /[^/]+$

    ⚠️ **최종 판정자는 정책이지 이 함수가 아니다.** 여기서 조립한 문자열이 정규식을
    만족하지 않으면 파서가 null을 돌려주고, 멤버십 헬퍼가 false를 돌려주며, 역할과
    무관하게 정책이 거부한다. 이 함수는 그 형태를 깨지 않을 뿐이다
    (`apps/api/tests/test_user_storage.py`가 정규식 사본으로 그것을 단언한다).
    """
    if not filename or "/" in filename:
        # 호출자가 `sanitize_filename`을 건너뛴 경우. 정책 거부를 502로 받는 것보다
        # 프로그래밍 오류로 즉시 끊는 편이 원인을 되짚을 수 있다.
        raise ValueError(
            "filename은 비어 있지 않고 경로 구분자를 담지 않아야 한다 "
            "— sanitize_filename()을 먼저 통과시킬 것"
        )
    return f"{workspace_id}/{raw_source_id}/{filename}"


def _encode_path(path: str) -> str:
    """세그먼트마다 percent-encode 하되 구분자는 남긴다.

    파일명에 공백이 들어올 수 있고(허용 목록이 공백을 남긴다), 인코딩하지 않으면
    httpx가 URL을 만들 때 형태가 달라진다.
    """
    return "/".join(quote(segment, safe="") for segment in path.split("/"))


# -----------------------------------------------------------------------------
# 3. 업로드 어댑터
# -----------------------------------------------------------------------------

# ⚠️ Storage는 실패를 **전송 상태 400**으로 돌려주고 진짜 구분은 본문 `code`에 담는다
#    (2026-08-08 로컬 스택 실측). 전송 상태만 보고 분기하면 "권한 없음"·"이미 있음"·
#    "잘못된 키"가 전부 한 덩어리가 되어, 정책 거부가 저장소 장애로 위장된다.
_CODE_ALREADY_EXISTS: Final[str] = "KeyAlreadyExists"
_DENIED_CODES: Final[frozenset[str]] = frozenset({"AccessDenied", "Unauthorized", "InvalidJWT"})
_DENIED_STATUS_CODES: Final[frozenset[int]] = frozenset({401, 403})


class UserStorage:
    """요청자 JWT를 실은 Supabase Storage 어댑터.

    ⚠️ 여기에 실리는 것은 요청자 JWT이며 service key가 아니다. service key를 실으면
    `0005`의 세 정책(select/insert/delete)이 통째로 우회되어, 어느 워크스페이스의
    원본이든 올리고 읽을 수 있게 된다. `UserDb:45-47`과 같은 문장이다.
    근거: checklists.json > decisions.db_access.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        supabase_url: str,
        publishable_key: str,
        access_token: str,
    ) -> None:
        self._client = client
        self._base_url = f"{supabase_url.rstrip('/')}/storage/v1"
        self._headers = {
            "apikey": publishable_key,
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    async def upload(self, *, path: str, data: bytes, content_type: str) -> None:
        """원본 바이트를 `path`에 올린다. 성공이면 조용히 돌아온다.

        ⚠️ 이 메서드는 **상태 코드를 스스로 응답으로 정하지 않는다.** 예외를 올리고
        렌더링은 `api.errors`의 단일 등록 지점이 한다 (02-CONTEXT.md > D-13).

        ⚠️ 예외에 응답 본문을 담지 않는다. Storage 오류 본문은 버킷 이름과 키 전문을
        담고 있어 그대로 실으면 내부 경로가 새어 나간다.
        """
        response = await self._client.post(
            f"{self._base_url}/object/{SOURCES_BUCKET}/{_encode_path(path)}",
            content=data,
            headers={**self._headers, "Content-Type": content_type},
            timeout=UPLOAD_TIMEOUT_SECONDS,
        )
        if response.is_success:
            return

        code = _error_code(response)
        # 로그에는 남긴다 — `code`는 공급자가 정한 고정 어휘이지 요청자가 넣은 값이 아니다.
        _logger.warning(
            "api.storage_upload_failed",
            status_code=response.status_code,
            provider_code=code,
        )

        if code == _CODE_ALREADY_EXISTS:
            raise StorageObjectExists
        if code in _DENIED_CODES or response.status_code in _DENIED_STATUS_CODES:
            # 정책이 막은 것을 502로 렌더하면 "편집 권한이 없다"가 "저장소가 죽었다"로
            # 보인다. 쓰기 0행과 같은 판정이므로 같은 단일 핸들러로 보낸다
            # (02-CONTEXT.md > D-11).
            raise WorkspaceForbidden(table=_OBJECTS_TABLE, affected=0)
        # `InvalidKey`도 여기로 온다. `sanitize_filename`이 Storage 허용 집합의
        # 부분집합만 내보내므로 정상 경로에서는 도달할 수 없다 — 도달했다면 그 함수의
        # 회귀이며, 사용자가 고칠 수 있는 것이 없으므로 5xx가 맞다.
        raise StorageUnavailable


def _error_code(response: httpx.Response) -> str | None:
    """실패 응답의 `code`만 꺼낸다. 본문의 나머지는 읽지도 옮기지도 않는다."""
    try:
        body: Any = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    code = body.get("code")
    return code if isinstance(code, str) else None
