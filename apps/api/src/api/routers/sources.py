"""원문 수집 라우터 — 텍스트·파일·URL 세 경로를 받아 즉시 202로 인큐한다.

관련 태스크: P2-ING-01 (ING-01, ING-02, ING-03, OPS-01)
설계 근거: 02-CONTEXT.md > D-11, D-12, D-13
설계 근거: 03-04-PLAN.md > D-P10 (잡 4종과 dedup 키 규약)
설계 근거: 03-05-PLAN.md > D-P11 (원시 바이트 본문), D-P12 (업로드 순서), D-P13 (상한값)
설계 근거: checklists.json > decisions.db_access

⚠️ 이 라우터는 **어떤 블로킹 작업도 하지 않는다.** 추출·페치·청킹·LLM·임베딩은 전부
워커의 일이다. 그것이 ING-01의 요구("수집 요청은 즉시 202로 돌아온다")이며, 여기서
한 줄이라도 길어지는 작업을 하면 요청 타임아웃이 곧 수집 실패가 된다. 유일한 예외는
Storage 업로드이고, 그것이 예외일 수 있는 이유는 `MAX_UPLOAD_BYTES`가 최악의 경우를
미리 유한하게 잘라 두기 때문이다 (`api.storage.UPLOAD_TIMEOUT_SECONDS`).

⚠️ 인큐는 `public.enqueue_source_job` **하나뿐**이다. `jobs`에는 어느 사용자 롤에도
INSERT 권한이 없어(`0007` 섹션 8) 이 definer RPC가 유일한 통로이며, 그 함수 안에
멤버십 확인과 월 비용 상한이 함께 들어 있다 — 다른 경로를 만들면 그 둘을 건너뛴다.

⚠️ `content_hash`는 **경로마다 규칙이 다르다.** 파일은 원본 바이트의 sha256이고,
텍스트·URL은 `normalize()`한 문자열의 UTF-8 바이트 sha256이다. 같은 컬럼에 두 규칙이
들어가므로 어느 쪽인지 모르면 재수집 판정이 설명되지 않는다 — 그래서 아래 두 해시
함수를 각각 이름으로 구분하고, 공용 헬퍼는 해시를 **계산하지 않고 인자로 받는다.**
`0001_core_schema.sql:102-104`가 그 두 규칙을 이미 컬럼 주석으로 규정했다.

소비자: `scripts/smoke_pipeline.sh` · `apps/api/tests/test_sources_router.py`
"""

from __future__ import annotations

import hashlib
from typing import Annotated, Any, Final
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from api.db.user import UserDb
from api.errors import (
    BUDGET_SQLSTATE,
    DUPLICATE_SQLSTATE,
    BudgetExceeded,
    DatabaseError,
    InvalidSourceInput,
    PayloadTooLarge,
    SourceAlreadyIngested,
    TextTooLarge,
)
from api.settings import ApiSettings
from api.storage import UserStorage, sanitize_filename, storage_path_for
from nexuswiki_core.domain import SourceType
from nexuswiki_core.logging import get_logger
from nexuswiki_core.tokenizer import normalize

router = APIRouter(prefix="/workspaces", tags=["sources"])

# ⚠️ 이 모듈에는 상태 코드 리터럴도 인라인 상태 코드 응답도 두지 않는다. 아래 데코레이터의
#    `status_code`는 **성공 코드 선언**이지 판정이 아니다. 거부(403 · 409 · 402 · 413 ·
#    422 · 502)는 전부 `api.errors`의 등록된 핸들러가 렌더한다.
#    근거: 02-CONTEXT.md > D-12, D-13.
_bearer = HTTPBearer()

_logger = get_logger(__name__)

_RAW_SOURCES_TABLE = "raw_sources"
_ENQUEUE_FUNCTION = "enqueue_source_job"

_TITLE_MAX_LENGTH: Final[int] = 200
_FILENAME_MAX_LENGTH: Final[int] = 255

# ⚠️ 워커가 실제로 접속할 수 있는 스킴만 받는다. `file:` 을 통과시키면 워커의 페치가
#    곧 로컬 파일 읽기가 된다.
_FETCHABLE_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})


class TextSourceRequest(BaseModel):
    """텍스트 직접 입력 요청.

    ⚠️ `extra="forbid"`가 이 모델의 핵심이다. 모르는 필드를 조용히 버리면
    `workspace_id`나 `created_by`를 실은 요청이 "성공했는데 아무 일도 일어나지 않았다"로
    보이고, 통과시키면 이 라우터가 곧 소유권 위조 경로가 된다. 둘 다 아니고 거절한다.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=_TITLE_MAX_LENGTH)
    text: str = Field(min_length=1)
    source_type: SourceType = SourceType.TEXT
    collection_purpose: str | None = Field(default=None, max_length=500)


class UrlSourceRequest(BaseModel):
    """URL 수집 요청.

    ⚠️ `url`의 길이 상한을 `Field(max_length=...)`로 두지 않는다. 상한값은
    `ApiSettings.MAX_URL_LENGTH`가 소유하는 **운영 토글**이고 Field 인자는 클래스
    정의 시점에 고정되므로, 여기 박으면 설정을 바꿔도 검증이 따라오지 않는다.
    판정은 아래 핸들러가 설정을 읽어서 한다.
    """

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1, max_length=_TITLE_MAX_LENGTH)
    collection_purpose: str | None = Field(default=None, max_length=500)


# -----------------------------------------------------------------------------
# 1. 어댑터 팩토리 — 둘 다 요청자 JWT를 싣는다
# -----------------------------------------------------------------------------


def _user_db(request: Request, credentials: HTTPAuthorizationCredentials) -> UserDb:
    """요청자 JWT를 실은 어댑터를 만든다.

    ⚠️ 여기에 실리는 것은 요청자 JWT이며 service key가 아니다. service key를 실으면
    BYPASSRLS라 `0004`의 격리 정책이 통째로 우회된다.
    근거: checklists.json > decisions.db_access.
    """
    settings: ApiSettings = request.app.state.settings
    return UserDb(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


def _user_storage(request: Request, credentials: HTTPAuthorizationCredentials) -> UserStorage:
    """Storage 어댑터도 같은 JWT를 싣는다 — `0005`의 세 정책이 그 위에서만 성립한다."""
    settings: ApiSettings = request.app.state.settings
    return UserStorage(
        request.app.state.http_client,
        supabase_url=settings.SUPABASE_URL,
        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
        access_token=credentials.credentials,
    )


# -----------------------------------------------------------------------------
# 2. content_hash — 두 규칙
# -----------------------------------------------------------------------------


def _text_content_hash(text: str) -> str:
    """텍스트·URL용 — 정규화된 문자열의 UTF-8 바이트 sha256.

    정규화를 먼저 거치므로 NFC·NFD·전각 표기 차이가 같은 해시로 접힌다. 그래서 같은
    글을 다른 입력기로 두 번 붙여 넣어도 두 번째가 409로 걸린다.

    ⚠️ 파일 경로는 `_bytes_content_hash`라는 **다른 규칙**을 쓴다 — 파일은 정규화할
    대상이 텍스트가 아니라 바이트열이고, 추출 결과가 아니라 원본이 동일성의 기준이기
    때문이다.
    """
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def _bytes_content_hash(data: bytes) -> str:
    """파일용 — **원본 바이트** 그대로의 sha256.

    ⚠️ 텍스트·URL 경로(`_text_content_hash`)와 다른 규칙이다. 여기서 정규화를 끼워
    넣으면 같은 PDF가 업로드 경로에 따라 다른 해시를 받아 중복 판정이 무너지고,
    반대로 텍스트에 바이트 해싱을 쓰면 같은 글의 표기 차이가 전부 새 원문이 된다.
    파일명은 해시에 들어가지 않는다 — 동일성의 기준은 내용이지 이름이 아니다.
    """
    return hashlib.sha256(data).hexdigest()


# -----------------------------------------------------------------------------
# 3. 세 경로가 공유하는 조립·인큐 절차
# -----------------------------------------------------------------------------


async def _existing_source_id(db: UserDb, *, workspace_id: UUID, content_hash: str) -> str | None:
    rows = await db.select(
        _RAW_SOURCES_TABLE,
        match={"workspace_id": str(workspace_id), "content_hash": content_hash},
        columns="id",
        limit=1,
    )
    return str(rows[0]["id"]) if rows else None


async def _insert_and_enqueue(
    db: UserDb, *, workspace_id: UUID, values: dict[str, Any]
) -> dict[str, Any]:
    """`raw_sources` 한 행을 만들고 `parse` 잡을 인큐한다.

    ⚠️ 이 헬퍼는 `content_hash`를 **계산하지 않고 `values`로 받는다.** 한 함수가 두
    해시 규칙을 분기로 갖는 순간 어느 규칙이 쓰였는지가 호출부에서 보이지 않게 된다.
    """
    try:
        row = await db.insert_one(_RAW_SOURCES_TABLE, values=values)
    except DatabaseError as error:
        if error.sqlstate != DUPLICATE_SQLSTATE:
            raise
        storage_path = values.get("storage_path")
        if storage_path:
            # D-P12: 선조회를 통과했는데 여기서 23505가 났다는 것은 경쟁 조건에서 졌다는
            # 뜻이고, 그때 아무도 참조하지 않는 Storage 객체가 하나 남는다. 경로에는
            # secret이 없다(uuid 둘 + 정규화된 파일명). 정리 스윕은 Phase 7의 일이다.
            _logger.warning("api.storage_orphan_object", storage_path=storage_path)
        existing = await _existing_source_id(
            db, workspace_id=workspace_id, content_hash=str(values["content_hash"])
        )
        raise SourceAlreadyIngested(raw_source_id=existing) from None

    try:
        jobs = await db.rpc(
            _ENQUEUE_FUNCTION,
            params={
                "p_workspace_id": str(workspace_id),
                "p_raw_source_id": str(row["id"]),
            },
        )
    except DatabaseError as error:
        if error.sqlstate == BUDGET_SQLSTATE:
            # ⚠️ 여기서 거부되는 것은 **인큐**이지 수집이 아니다. `raw_sources` 행은
            #    이미 만들어졌고 남는다 — 상한이 풀리면 03-07의 재시도 경로가 그 행을
            #    다시 인큐할 수 있어야 하기 때문이다. 응답과 DB 상태가 그 둘을 구분한다.
            raise BudgetExceeded from None
        raise

    # ⚠️ 0행은 여기서 비정상이다. `enqueue_source_job`은 중복 인큐도 기존 잡을 돌려주도록
    #    설계되어 있어(`0009:314-324`) 0행이 나올 정상 경로가 없다. 조용히 null을 돌려주면
    #    프론트가 따라갈 진행이 없는 채 "접수됨"만 보게 된다.
    if not jobs:
        raise DatabaseError(
            sqlstate=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"{_ENQUEUE_FUNCTION}가 0행을 돌려줬다",
        )

    return {"job_id": str(jobs[0]["id"]), "raw_source_id": str(row["id"])}


async def _read_limited_body(request: Request, *, limit: int) -> bytes:
    """본문을 청크 단위로 읽되 누적치가 상한을 넘는 순간 끊는다.

    ⚠️ 이것이 D-P11이 multipart를 쓰지 않는 두 번째 이유다. `UploadFile`/`Form`은
    FastAPI가 본문 전체를 먼저 버퍼링(디스크 스풀 포함)한 뒤 핸들러에 넘기므로, 크기
    상한이 **버퍼링 이후**에만 걸린다 — 상한이 방어가 아니라 사후 통보가 된다.
    여기서는 상한을 넘는 순간 읽기를 멈추므로 20MiB 상한에 1GiB를 밀어 넣어도
    메모리에 남는 것은 상한 언저리뿐이다.

    경계는 **포함**이다: 정확히 `limit` 바이트는 통과하고 1바이트 큰 요청은 거부된다.
    """
    buffer = bytearray()
    async for chunk in request.stream():
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise PayloadTooLarge(limit=limit)
    return bytes(buffer)


def _declared_mime(request: Request) -> str:
    """`Content-Type` 헤더에서 매개변수를 떼어낸 미디어 타입만 돌려준다.

    `text/plain; charset=utf-8`이 허용 목록과 맞지 않아 거부되는 일이 없어야 한다.
    """
    header = request.headers.get("content-type", "")
    return header.split(";", 1)[0].strip().casefold()


def _assert_fetchable_url(url: str) -> None:
    """스킴·호스트·자격증명만 본다.

    ⚠️ **여기서 페치하지 않는다.** 이유 둘.
    (1) ING-01이 블로킹 작업을 요청 안에서 금지한다 — 외부 서버의 응답 시간이 곧 이
        API의 응답 시간이 되면 "즉시 202"가 남의 서버 사정에 달리게 된다.
    (2) 요청 시점에 DNS를 해석해 사설 대역을 걸러도, 워커가 실제로 접속할 때 같은
        이름이 다른 주소로 풀릴 수 있다(TOCTOU). **권위 있는 SSRF 판정은 접속 시점**
        에만 가능하고 그것은 워커의 일이다(03-06, T-03-37). 여기서 DNS를 보면 막지도
        못하면서 막았다고 믿게 된다.
    """
    try:
        parts = urlsplit(url)
        host = parts.hostname
        username = parts.username
        password = parts.password
    except ValueError:
        # 깨진 IPv6 리터럴이나 포트 표기. 파싱 실패를 500으로 흘리지 않는다.
        raise InvalidSourceInput(reason="bad_url_form") from None

    if parts.scheme.casefold() not in _FETCHABLE_SCHEMES:
        raise InvalidSourceInput(reason="bad_url_scheme")
    if username or password:
        # 저장하면 자격증명이 `raw_sources.metadata`에 남고 멤버 SELECT로 노출된다
        # (T-03-36). 그래서 저장 전에 끊는다.
        raise InvalidSourceInput(reason="url_credentials")
    if not host:
        raise InvalidSourceInput(reason="bad_url_host")


# -----------------------------------------------------------------------------
# 4. 엔드포인트 셋
# -----------------------------------------------------------------------------


@router.post("/{workspace_id}/sources/text", status_code=status.HTTP_202_ACCEPTED)
async def ingest_text_source(
    workspace_id: UUID,
    payload: TextSourceRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """텍스트 한 건을 저장하고 `parse` 잡을 인큐한 뒤 즉시 돌아온다."""
    settings: ApiSettings = request.app.state.settings
    # ⚠️ 길이는 **유니코드 코드 포인트** 기준이다. 바이트로 재면 한글이 3배로 세어져
    #    같은 상한이 언어마다 다른 값이 된다.
    if len(payload.text) > settings.MAX_TEXT_CHARS:
        raise TextTooLarge(limit=settings.MAX_TEXT_CHARS)

    db = _user_db(request, credentials)
    # id를 **서버가 만든다.** Storage 경로와 `content_hash`를 같은 요청 안에서 확정해야
    # 하고, 클라이언트가 id를 정하면 그것이 곧 남의 행을 가리키는 시도가 된다.
    values: dict[str, Any] = {
        "id": str(uuid4()),
        "workspace_id": str(workspace_id),
        "title": payload.title,
        "source_type": payload.source_type.value,
        "content": payload.text,
        "content_hash": _text_content_hash(payload.text),
        "collection_purpose": payload.collection_purpose,
        "metadata": {},
        # `created_by`는 넣지 않는다 — 채우려면 JWT의 `sub`를 파싱해 신뢰해야 하고
        # 그 검증은 이 라우터의 책임이 아니다. 컬럼은 nullable이며(`0001:92`)
        # `on delete set null`이라 애초에 없을 수 있는 값으로 설계되어 있다.
    }
    return await _insert_and_enqueue(db, workspace_id=workspace_id, values=values)


@router.post("/{workspace_id}/sources/file", status_code=status.HTTP_202_ACCEPTED)
async def ingest_file_source(
    workspace_id: UUID,
    filename: Annotated[str, Query(min_length=1, max_length=_FILENAME_MAX_LENGTH)],
    title: Annotated[str, Query(min_length=1, max_length=_TITLE_MAX_LENGTH)],
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """원시 바이트 본문을 Storage에 보존하고 `parse` 잡을 인큐한다 (D-P11).

    본문은 multipart가 아니라 **원시 바이트**이고 파일명·제목은 쿼리 파라미터다.
    대시보드는 `fetch(url, {method: "POST", body: file})`로 그대로 보낼 수 있다.
    """
    settings: ApiSettings = request.app.state.settings

    content_type = _declared_mime(request)
    if content_type not in settings.ALLOWED_UPLOAD_MIME_TYPES:
        # ⚠️ `reason`에 받은 Content-Type을 실지 않는다 — 요청 헤더 조각을 응답에
        #    되비추면 그 자체가 반사형 노출 경로다 (T-03-34).
        raise InvalidSourceInput(reason="unsupported_mime")

    data = await _read_limited_body(request, limit=settings.MAX_UPLOAD_BYTES)
    if not data:
        # 빈 원문이 조용히 수집되면 `parse`가 추출 실패로 dead에 수렴하고, 사용자는
        # "올렸는데 아무 일도 안 일어난다"만 보게 된다. 요청 경계에서 끊는다.
        raise InvalidSourceInput(reason="empty_body")

    content_hash = _bytes_content_hash(data)
    db = _user_db(request, credentials)

    # D-P12 (1) 업로드 **이전에** 중복을 한 번 조회한다. 이 선조회는 고아 객체를
    #          스팸으로 만들지 않기 위한 편의이고, 최종 판정자는
    #          `(workspace_id, content_hash)` 유니크 제약이다.
    existing = await _existing_source_id(db, workspace_id=workspace_id, content_hash=content_hash)
    if existing is not None:
        raise SourceAlreadyIngested(raw_source_id=existing)

    # D-P12 (2)(3) `raw_sources`보다 Storage가 먼저다. 순서를 뒤집으면 업로드 실패가
    #              객체 없는 `storage_path`를 가리키는 행을 남기는데, `raw_sources`에는
    #              사용자 UPDATE 정책이 없어(0004:209-211) 고칠 수 없고 DELETE는 owner
    #              전용이라 editor가 치울 수도 없다. 반대 순서에서 남는 것은 아무도
    #              참조하지 않는 난수 uuid 경로의 비공개 객체뿐이다.
    raw_source_id = str(uuid4())
    storage_path = storage_path_for(
        workspace_id=str(workspace_id),
        raw_source_id=raw_source_id,
        filename=sanitize_filename(filename),
    )
    await _user_storage(request, credentials).upload(
        path=storage_path, data=data, content_type=content_type
    )

    values: dict[str, Any] = {
        "id": raw_source_id,
        "workspace_id": str(workspace_id),
        "title": title,
        "source_type": SourceType.FILE.value,
        # ⚠️ `content = ""`는 "아직 추출되지 않음"의 sentinel이다. 추출에 성공한 행이
        #    빈 `content`를 갖는 경우는 없다 — ING-04의 품질 게이트가 그런 문서를
        #    실패시키기 때문이다(03-06). 그리고 `raw_sources`에 사용자 UPDATE 정책이
        #    없으므로 이 값을 채울 수 있는 것은 워커(`service_role`)뿐이다.
        "content": "",
        "content_hash": content_hash,
        "storage_path": storage_path,
        "mime_type": content_type,
        "byte_size": len(data),
        # 정규화 **이전**의 원본 이름. Storage 키는 ASCII 부분집합으로 접히므로
        # (`api.storage`의 허용 목록) 사람이 읽는 이름은 여기에만 남는다.
        "metadata": {"original_filename": filename},
    }
    return await _insert_and_enqueue(db, workspace_id=workspace_id, values=values)


@router.post("/{workspace_id}/sources/url", status_code=status.HTTP_202_ACCEPTED)
async def ingest_url_source(
    workspace_id: UUID,
    payload: UrlSourceRequest,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """URL을 등록하고 `parse` 잡을 인큐한다. 페치는 워커가 한다."""
    settings: ApiSettings = request.app.state.settings

    url = payload.url.strip()
    if len(url) > settings.MAX_URL_LENGTH:
        raise InvalidSourceInput(reason="url_too_long")
    _assert_fetchable_url(url)

    db = _user_db(request, credentials)
    values: dict[str, Any] = {
        "id": str(uuid4()),
        "workspace_id": str(workspace_id),
        # `raw_sources.title`이 not null이므로 제목이 없으면 URL을 쓴다.
        "title": payload.title or url[:_TITLE_MAX_LENGTH],
        "source_type": SourceType.URL.value,
        # 파일 경로와 같은 sentinel — 페치와 추출은 03-06의 워커가 한다.
        "content": "",
        "content_hash": _text_content_hash(url),
        "storage_path": None,
        "collection_purpose": payload.collection_purpose,
        "metadata": {"url": url},
    }
    return await _insert_and_enqueue(db, workspace_id=workspace_id, values=values)


@router.delete("/{workspace_id}/sources/{source_id}")
async def delete_source(
    workspace_id: UUID,
    source_id: UUID,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """원문 소스를 영구 삭제한다.

    소유자만 삭제할 수 있으며(RLS raw_sources_delete_owner),
    DB 외래키 on delete cascade에 의해 source_chunks와 source_embeddings가 함께 삭제된다.
    DB 행 삭제 성공 후 스토리지 원본 파일 및 wiki_pages.sources 인용 목록을 정리한다.
    """
    db = _user_db(request, credentials)
    ws_id = str(workspace_id)
    s_id = str(source_id)

    # 1. DB 행을 먼저 삭제하여 RLS 소유자 권한 확인 및 외래키 CASCADE 적용 (무결성 보장)
    deleted_row = await db.delete_one(
        _RAW_SOURCES_TABLE,
        match={"id": s_id, "workspace_id": ws_id},
    )

    # 2. 스토리지 원본 파일 정리 (스토리지 삭제 실패가 DB 삭제 상태를 깨뜨리지 않도록 안전 처리)
    storage_path = deleted_row.get("storage_path")
    if storage_path:
        try:
            storage = _user_storage(request, credentials)
            await storage.delete(path=storage_path)
        except Exception as err:
            _logger.warning(
                "Failed to delete storage path %s for deleted raw source %s: %s",
                storage_path,
                s_id,
                err,
            )

    # 3. wiki_pages.sources JSONB 인용 목록에서 삭제된 source_id 정리
    try:
        wiki_rows = await db.select(
            "wiki_pages",
            match={"workspace_id": ws_id},
            columns="id,sources",
        )
        for w in wiki_rows:
            sources_list = w.get("sources") or []
            if s_id in sources_list:
                updated_sources = [sid for sid in sources_list if sid != s_id]
                await db.update_one(
                    "wiki_pages",
                    match={"id": str(w["id"]), "workspace_id": ws_id},
                    values={"sources": updated_sources},
                )
    except Exception as err:
        _logger.warning(
            "Failed to clean up wiki_pages.sources for deleted raw source %s: %s",
            s_id,
            err,
        )

    return {
        "id": deleted_row["id"],
        "workspace_id": deleted_row["workspace_id"],
        "title": deleted_row["title"],
    }
