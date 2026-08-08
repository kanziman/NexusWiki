"""원문 수집 라우터 — 텍스트 한 건을 받아 즉시 202로 인큐한다.

관련 태스크: P2-ING-01 (ING-01, ING-02, OPS-01)
설계 근거: 02-CONTEXT.md > D-11, D-12, D-13
설계 근거: 03-04-PLAN.md > D-P10 (잡 4종과 dedup 키 규약)
설계 근거: checklists.json > decisions.db_access

⚠️ 이 라우터는 **어떤 블로킹 작업도 하지 않는다.** 추출·청킹·LLM·임베딩은 전부 워커의
일이다. 그것이 ING-01의 요구("수집 요청은 즉시 202로 돌아온다")이며, 여기서 한 줄이라도
길어지는 작업을 하면 요청 타임아웃이 곧 수집 실패가 된다.

⚠️ 인큐는 `public.enqueue_source_job` **하나뿐**이다. `jobs`에는 어느 사용자 롤에도
INSERT 권한이 없어(`0007` 섹션 8) 이 definer RPC가 유일한 통로이며, 그 함수 안에
멤버십 확인과 월 비용 상한이 함께 들어 있다 — 다른 경로를 만들면 그 둘을 건너뛴다.

소비자: `scripts/smoke_pipeline.sh` · `apps/api/tests/test_sources_router.py`
"""

from __future__ import annotations

import hashlib
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from api.db.user import UserDb
from api.errors import (
    BUDGET_SQLSTATE,
    DUPLICATE_SQLSTATE,
    BudgetExceeded,
    DatabaseError,
    SourceAlreadyIngested,
    TextTooLarge,
)
from api.settings import ApiSettings
from nexuswiki_core.domain import SourceType
from nexuswiki_core.tokenizer import normalize

router = APIRouter(prefix="/workspaces", tags=["sources"])

# ⚠️ 이 모듈에는 상태 코드 리터럴도 인라인 상태 코드 응답도 두지 않는다. 아래 데코레이터의
#    `status_code`는 **성공 코드 선언**이지 판정이 아니다. 거부(403 · 409 · 402 · 413)는
#    전부 `api.errors`의 등록된 핸들러가 렌더한다. 근거: 02-CONTEXT.md > D-12, D-13.
_bearer = HTTPBearer()

_RAW_SOURCES_TABLE = "raw_sources"
_ENQUEUE_FUNCTION = "enqueue_source_job"


class TextSourceRequest(BaseModel):
    """텍스트 직접 입력 요청.

    ⚠️ `extra="forbid"`가 이 모델의 핵심이다. 모르는 필드를 조용히 버리면
    `workspace_id`나 `created_by`를 실은 요청이 "성공했는데 아무 일도 일어나지 않았다"로
    보이고, 통과시키면 이 라우터가 곧 소유권 위조 경로가 된다. 둘 다 아니고 거절한다.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    source_type: SourceType = SourceType.TEXT
    collection_purpose: str | None = Field(default=None, max_length=500)


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


def _content_hash(text: str) -> str:
    """`raw_sources.content_hash` — 정규화된 문자열의 UTF-8 바이트 sha256.

    정규화를 먼저 거치므로 NFC·NFD·전각 표기 차이가 같은 해시로 접힌다. 그래서 같은
    글을 다른 입력기로 두 번 붙여 넣어도 두 번째가 409로 걸린다.

    ⚠️ 파일 경로(03-05)는 **원본 바이트**를 해싱하는 다른 규칙을 쓴다 — 파일은 정규화할
    대상이 텍스트가 아니라 바이트열이고, 추출 결과가 아니라 원본이 동일성의 기준이기
    때문이다. 두 규칙이 다르다는 사실을 여기 미리 남긴다.
    `0001_core_schema.sql:102-104`가 그 두 규칙을 이미 컬럼 주석으로 규정했다.
    """
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


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
    # id를 **서버가 만든다.** Storage 경로(03-05)와 `content_hash`를 같은 요청 안에서
    # 확정해야 하고, 클라이언트가 id를 정하면 그것이 곧 남의 행을 가리키는 시도가 된다.
    raw_source_id = str(uuid4())
    content_hash = _content_hash(payload.text)

    values = {
        "id": raw_source_id,
        "workspace_id": str(workspace_id),
        "title": payload.title,
        "source_type": payload.source_type.value,
        "content": payload.text,
        "content_hash": content_hash,
        "collection_purpose": payload.collection_purpose,
        "metadata": {},
        # `created_by`는 넣지 않는다 — 채우려면 JWT의 `sub`를 파싱해 신뢰해야 하고
        # 그 검증은 이 라우터의 책임이 아니다. 컬럼은 nullable이며(`0001:92`)
        # `on delete set null`이라 애초에 없을 수 있는 값으로 설계되어 있다.
    }

    try:
        row = await db.insert_one(_RAW_SOURCES_TABLE, values=values)
    except DatabaseError as error:
        if error.sqlstate != DUPLICATE_SQLSTATE:
            raise
        existing = await db.select(
            _RAW_SOURCES_TABLE,
            match={"workspace_id": str(workspace_id), "content_hash": content_hash},
            columns="id",
            limit=1,
        )
        raise SourceAlreadyIngested(
            raw_source_id=str(existing[0]["id"]) if existing else None
        ) from None

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
