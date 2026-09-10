"""핸들러 레지스트리 계약 회귀 테스트 — 미등록 type이 조용히 통과하지 않는다."""

import inspect
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

from nexuswiki_core.citations import BROAD_ANCHOR_PATTERN
from nexuswiki_core.extract import ExtractionQualityError
from nexuswiki_core.tokenizer import TSV_TOKENIZER_VERSION, bigram, normalize
from worker import handlers
from worker.handlers import compile as compile_handler
from worker.handlers import conflict, delete_source_storage, embed, link_sync, noop, parse
from worker.handlers.noop import handle_noop
from worker.transcript import NO_TRANSCRIPT, TranscriptUnavailable

JOB_ID = "22222222-2222-4222-8222-222222222222"
WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"


# -----------------------------------------------------------------------------
# 1. 레지스트리 — 0003이 jobs.type에 CHECK를 걸지 않은 자리를 이 딕셔너리가 대신한다
# -----------------------------------------------------------------------------


def test_registry_holds_exactly_the_job_types_this_phase_registered() -> None:
    # ⚠️ 이 단언은 03-09가 `link_sync`·`embed`를 등록할 때 **의도적으로 red가 된다.**
    #    그것이 목적이다 — 핸들러를 딕셔너리에 넣고 이 열거를 갱신하지 않으면
    #    `HANDLERS`가 사실상의 잡 종류 열거라는 계약(0003_jobs.sql:31-36)이 흐려진다.
    #    깨지면 값을 확인하고 여기 이름을 더할 것. 단언을 지워서 통과시키지 말 것.
    assert set(handlers.HANDLERS) == {
        "noop",
        "parse",
        "compile",
        "link_sync",
        "embed",
        "conflict_check",
        "delete_source_storage",
    }


def test_each_handler_module_exports_a_job_type_constant_matching_its_key() -> None:
    # 등록 키와 모듈 상수가 갈라지면 핸들러는 등록됐는데 인큐 측이 다른 문자열을 쓰는
    # 상태가 되고, 그 잡은 미등록 type으로 데드레터에 간다.
    constants = {
        "noop": noop.NOOP_JOB_TYPE,
        "parse": parse.PARSE_JOB_TYPE,
        "compile": compile_handler.COMPILE_JOB_TYPE,
        "link_sync": link_sync.LINK_SYNC_JOB_TYPE,
        "embed": embed.EMBED_JOB_TYPE,
        "conflict_check": conflict.CONFLICT_CHECK_JOB_TYPE,
        "delete_source_storage": delete_source_storage.DELETE_SOURCE_STORAGE_JOB_TYPE,
    }

    assert set(constants) == set(handlers.HANDLERS)
    for key, constant in constants.items():
        assert constant == key


def test_noop_is_registered_and_satisfies_the_handler_contract() -> None:
    assert "noop" in handlers.HANDLERS, sorted(handlers.HANDLERS)

    registered = handlers.HANDLERS["noop"]

    assert registered is handle_noop
    assert inspect.iscoroutinefunction(registered)
    parameters = inspect.signature(registered).parameters
    assert set(parameters) == {"job_id", "workspace_id", "payload"}
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters.values()
    )


@pytest.mark.asyncio
async def test_handle_noop_succeeds_without_side_effects() -> None:
    payload = {"target_id": "abc"}

    result = await handle_noop(job_id=JOB_ID, workspace_id=WORKSPACE_ID, payload=payload)

    assert result is None
    # 부작용 없음: 넘긴 payload를 건드리지 않는다.
    assert payload == {"target_id": "abc"}


def test_unknown_type_raises_and_names_the_type() -> None:
    # 예외 메시지가 그대로 last_error에 실린다 — 오타는 그 경로로 잡힌다
    # (supabase/migrations/0003_jobs.sql:31-36).
    with pytest.raises(handlers.UnknownJobTypeError) as excinfo:
        handlers.resolve_handler("complie")

    assert "complie" in str(excinfo.value)
    assert excinfo.value.job_type == "complie"


# -----------------------------------------------------------------------------
# 2. workspace 스코프 — service_role은 BYPASSRLS다
# -----------------------------------------------------------------------------


def test_every_registered_handler_requires_workspace_id() -> None:
    # ⚠️ 기본값이 있으면 잊고 호출해도 통과하고, 그 핸들러는 자기 워크스페이스를
    #    모른 채 교차 테넌트를 읽는 쿼리를 쓰게 된다.
    for job_type, handler in handlers.HANDLERS.items():
        parameter = inspect.signature(handler).parameters.get("workspace_id")

        assert parameter is not None, job_type
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, job_type
        assert parameter.default is inspect.Parameter.empty, job_type


# -----------------------------------------------------------------------------
# 3. 예외 전파 — 재시도/데드레터 판정은 큐 루프의 몫이다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_exceptions_are_not_swallowed_by_the_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exploding(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
        del job_id, workspace_id, payload
        raise RuntimeError("handler boom")

    monkeypatch.setitem(handlers.HANDLERS, "exploding", exploding)

    handler = handlers.resolve_handler("exploding")

    with pytest.raises(RuntimeError, match="handler boom"):
        await handler(job_id=JOB_ID, workspace_id=WORKSPACE_ID, payload={})


@pytest.mark.asyncio
async def test_wiki_embed_skips_pages_already_at_the_current_embedding_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """재처리는 같은 version의 위키 벡터에 OpenRouter 비용을 다시 쓰지 않는다."""

    class Db:
        async def list_wiki_pages_for_source(self, **_values: Any) -> list[dict[str, str]]:
            return [{"id": "page-1", "content": "이미 임베딩된 본문"}]

        async def list_wiki_embeddings(self, **_values: Any) -> list[dict[str, int | str]]:
            return [{"chunk_index": 0, "embedding_version": "model@provider-v1"}]

        async def delete_wiki_embeddings_from(self, **_values: Any) -> None:
            return None

        async def complete_job_and_chain(self, _job_id: str, **_values: Any) -> None:
            return None

    @asynccontextmanager
    async def no_op_client(_settings: object):
        yield object()

    async def unexpected_embedding(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("same embedding_version must not call OpenRouter")

    monkeypatch.setattr(embed, "WorkerSettings", lambda: SimpleNamespace(EMBED_BATCH_SIZE=16))
    monkeypatch.setattr(embed, "service_client", no_op_client)
    monkeypatch.setattr(embed, "openrouter_client", no_op_client)
    monkeypatch.setattr(embed, "ServiceDb", lambda _client: Db())
    monkeypatch.setattr(embed, "embedding_version", lambda _settings: "model@provider-v1")
    monkeypatch.setattr(embed, "embed_texts", unexpected_embedding)

    await embed.handle_embed(
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source", "scope": "wiki"},
    )


@pytest.mark.asyncio
async def test_embed_chains_wiki_scope_to_conflict_check_but_leaves_source_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Db:
        def __init__(self) -> None:
            self.chains: list[dict[str, Any]] = []

        async def list_source_chunks_missing_embedding(
            self, **_values: Any
        ) -> list[dict[str, str]]:
            return []

        async def list_wiki_pages_for_source(self, **_values: Any) -> list[dict[str, str]]:
            return []

        async def complete_job_and_chain(self, _job_id: str, **values: Any) -> None:
            self.chains.append(values)

    db = Db()

    @asynccontextmanager
    async def no_op_client(_settings: object):
        yield object()

    monkeypatch.setattr(embed, "WorkerSettings", lambda: SimpleNamespace(EMBED_BATCH_SIZE=16))
    monkeypatch.setattr(embed, "service_client", no_op_client)
    monkeypatch.setattr(embed, "openrouter_client", no_op_client)
    monkeypatch.setattr(embed, "ServiceDb", lambda _client: db)
    monkeypatch.setattr(embed, "embedding_version", lambda _settings: "model@provider-v1")

    await embed.handle_embed(
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source", "scope": "wiki"},
    )
    await embed.handle_embed(
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source", "scope": "source"},
    )

    assert db.chains == [
        {
            "next_type": "conflict_check",
            "next_payload": {
                "target_id": "raw-source:conflict_check",
                "raw_source_id": "raw-source",
            },
        },
        {},
    ]


@pytest.mark.asyncio
async def test_conflict_check_marks_both_pages_only_for_real_contradictions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Db:
        def __init__(self) -> None:
            self.disputed: list[str] = []
            self.completed = False

        async def list_wiki_pages_for_source(self, **_values: Any) -> list[dict[str, str]]:
            return [{"id": "page-a", "content": "The service is available in Seoul."}]

        async def find_similar_wiki_pages(self, **_values: Any) -> list[dict[str, float | str]]:
            return [{"candidate_wiki_id": "page-b", "similarity": 0.93}]

        async def _select(self, _table: str, *, params: dict[str, str]) -> list[dict[str, str]]:
            assert params["id"] == "eq.page-b"
            return [{"id": "page-b", "content": "The service is not available in Seoul."}]

        async def set_wiki_page_disputed(self, wiki_id: str, *, workspace_id: str) -> None:
            assert workspace_id == WORKSPACE_ID
            self.disputed.append(wiki_id)

        async def complete_job_and_chain(self, _job_id: str) -> None:
            self.completed = True

    async def contradiction(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            payload=conflict.ConflictJudgement(is_contradiction=True, rationale="facts clash")
        )

    monkeypatch.setattr(conflict, "complete_structured", contradiction)
    db = Db()
    await conflict.run_conflict_check(
        db,  # type: ignore[arg-type]
        object(),
        settings=object(),
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source"},
    )

    assert db.disputed == ["page-a", "page-b"]
    assert db.completed is True


@pytest.mark.asyncio
async def test_conflict_check_skips_variations_and_zero_candidate_llm_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Db:
        def __init__(self, candidates: list[dict[str, float | str]]) -> None:
            self.candidates = candidates
            self.disputed: list[str] = []

        async def list_wiki_pages_for_source(self, **_values: Any) -> list[dict[str, str]]:
            return [{"id": "page-a", "content": "A"}]

        async def find_similar_wiki_pages(self, **_values: Any) -> list[dict[str, float | str]]:
            return self.candidates

        async def _select(self, _table: str, *, params: dict[str, str]) -> list[dict[str, str]]:
            return [{"id": "page-b", "content": "B"}]

        async def set_wiki_page_disputed(self, wiki_id: str, *, workspace_id: str) -> None:
            self.disputed.append(wiki_id)

        async def complete_job_and_chain(self, _job_id: str) -> None:
            return None

    calls = 0

    async def variation(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            payload=conflict.ConflictJudgement(is_contradiction=False, rationale="scope differs")
        )

    monkeypatch.setattr(conflict, "complete_structured", variation)
    variation_db = Db([{"candidate_wiki_id": "page-b", "similarity": 0.93}])
    await conflict.run_conflict_check(
        variation_db,  # type: ignore[arg-type]
        object(),
        settings=object(),
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source"},
    )
    assert calls == 1
    assert variation_db.disputed == []

    empty_db = Db([])
    await conflict.run_conflict_check(
        empty_db,  # type: ignore[arg-type]
        object(),
        settings=object(),
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source"},
    )
    assert calls == 1


class _ParseDb:
    def __init__(self, source: dict[str, Any]) -> None:
        self.source = source
        self.updated: dict[str, Any] | None = None
        self.chained = False

    async def get_raw_source(self, _raw_source_id: str, *, workspace_id: str) -> dict[str, Any]:
        assert workspace_id == WORKSPACE_ID
        return self.source

    async def update_raw_source_content(self, _raw_source_id: str, **values: Any) -> None:
        self.updated = values

    async def upsert_source_chunks(self, **values: Any) -> list[dict[str, str]]:
        return [
            {"id": f"chunk-{row['chunk_index']}", "content": str(row["content"])}
            for row in values["rows"]
        ]

    async def index_source_chunk_lexical(self, **_values: str) -> None:
        return None

    async def delete_source_chunks_from(self, **_values: Any) -> list[object]:
        return []

    async def enqueue_job(self, **_values: Any) -> None:
        return None

    async def complete_job_and_chain(self, _job_id: str, **_values: Any) -> None:
        self.chained = True


@pytest.mark.asyncio
async def test_parse_materializes_normalized_bigram_lexical_rows() -> None:
    """새 청크와 재처리 청크는 writer RPC로 현재 토크나이저를 남긴다."""

    class Db(_ParseDb):
        def __init__(self) -> None:
            super().__init__({"source_type": "text", "content": "NexusWiki 검색 계약"})
            self.indexed: list[dict[str, str]] = []

        async def upsert_source_chunks(self, **values: Any) -> list[dict[str, str]]:
            return [{"id": "chunk-1", "content": str(row["content"])} for row in values["rows"]]

        async def index_source_chunk_lexical(self, **values: str) -> None:
            self.indexed.append(values)

    db = Db()

    await parse.run_parse(
        db,  # type: ignore[arg-type]
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source"},
    )

    assert db.indexed
    assert all(row["workspace_id"] == WORKSPACE_ID for row in db.indexed)
    assert all(row["tokenizer_version"] == TSV_TOKENIZER_VERSION for row in db.indexed)
    assert db.indexed[0]["bigrams"] == bigram(normalize("NexusWiki 검색 계약"))


@pytest.mark.asyncio
async def test_parse_strips_forged_anchors_before_chunk_offsets_are_calculated() -> None:
    """CITE-06은 원문 전체를 청킹 전에 정리해 ING-05 offset 계약도 보존한다."""

    raw_content = "시작 [[wiki:attacker]] 가짜 지시. 끝 [[src:not-issued]]"

    class Db(_ParseDb):
        def __init__(self) -> None:
            super().__init__({"source_type": "text", "content": raw_content})
            self.rows: list[dict[str, Any]] = []

        async def upsert_source_chunks(self, **values: Any) -> list[dict[str, str]]:
            self.rows = list(values["rows"])
            return [
                {"id": f"chunk-{row['chunk_index']}", "content": str(row["content"])}
                for row in self.rows
            ]

    db = Db()

    await parse.run_parse(
        db,  # type: ignore[arg-type]
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source"},
    )

    stripped_content = "시작  가짜 지시. 끝 "
    assert db.rows
    assert all(BROAD_ANCHOR_PATTERN.search(str(row["content"])) is None for row in db.rows)
    assert all(
        stripped_content[int(row["char_start"]) : int(row["char_end"])] == row["content"]
        for row in db.rows
    )


# -----------------------------------------------------------------------------
# transcript 분기 (youtube-channel-import Task 2.3)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_transcript_fills_content_from_the_adapter() -> None:
    """자막이 원문 본문이 되고, 인용 좌표가 저장된 본문과 정확히 일치한다."""

    transcript = "첫 문장입니다. 둘째 문장입니다. 셋째 문장입니다."

    class Db(_ParseDb):
        def __init__(self) -> None:
            super().__init__(
                {
                    "source_type": "transcript",
                    "content": "",
                    "metadata": {
                        "video_id": "abc12345678",
                        "channel_id": "UC1",
                        "url": "https://www.youtube.com/watch?v=abc12345678",
                    },
                }
            )
            self.rows: list[dict[str, Any]] = []

        async def upsert_source_chunks(self, **values: Any) -> list[dict[str, str]]:
            self.rows = list(values["rows"])
            return [
                {"id": f"chunk-{row['chunk_index']}", "content": str(row["content"])}
                for row in self.rows
            ]

    db = Db()
    seen: list[str] = []

    async def provider(video_id: str) -> str:
        seen.append(video_id)
        return transcript

    await parse.run_parse(
        db,  # type: ignore[arg-type]
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source"},
        transcript_provider=provider,
    )

    assert seen == ["abc12345678"]
    assert db.updated is not None
    assert db.updated["content"] == transcript
    # ⚠️ 이 단언이 이중 Citation의 절반이다. 저장된 자막을 char 구간으로 자른 것이
    #    청크 본문과 다르면 답변에서 원문 영상으로 되짚을 수 없다.
    assert db.rows
    assert all(
        transcript[int(row["char_start"]) : int(row["char_end"])] == row["content"]
        for row in db.rows
    )
    assert db.chained


@pytest.mark.asyncio
async def test_parse_transcript_does_not_use_the_url_fetch_path() -> None:
    """URL 분기의 `fetch_source`와 섞이지 않는다 (design D1)."""

    class Db(_ParseDb):
        def __init__(self) -> None:
            super().__init__(
                {
                    "source_type": "transcript",
                    "content": "",
                    # URL 소스와 같은 키를 실어 두어도 페치 경로로 새면 안 된다.
                    "metadata": {"video_id": "abc12345678", "url": "http://example.invalid/x"},
                }
            )

    async def boom(*_args: Any, **_kwargs: Any) -> Any:  # pragma: no cover - 도달하면 안 된다
        raise AssertionError("자막 소스는 fetch_source를 거치지 않는다")

    async def provider(video_id: str) -> str:
        return "자막 본문"

    with mock.patch.object(parse, "fetch_source", boom):
        await parse.run_parse(
            Db(),  # type: ignore[arg-type]
            job_id=JOB_ID,
            workspace_id=WORKSPACE_ID,
            payload={"raw_source_id": "raw-source"},
            transcript_provider=provider,
        )


@pytest.mark.asyncio
async def test_parse_transcript_failure_stops_before_creating_empty_chunks() -> None:
    """자막 실패는 그대로 올라간다 — 청크 0개짜리 "성공"을 만들지 않는다."""

    class Db(_ParseDb):
        def __init__(self) -> None:
            super().__init__(
                {
                    "source_type": "transcript",
                    "content": "",
                    "metadata": {"video_id": "abc12345678"},
                }
            )
            self.upserted = False

        async def upsert_source_chunks(self, **values: Any) -> list[dict[str, str]]:
            self.upserted = True
            return []

    db = Db()

    async def provider(video_id: str) -> str:
        raise TranscriptUnavailable(reason=NO_TRANSCRIPT)

    with pytest.raises(TranscriptUnavailable) as excinfo:
        await parse.run_parse(
            db,  # type: ignore[arg-type]
            job_id=JOB_ID,
            workspace_id=WORKSPACE_ID,
            payload={"raw_source_id": "raw-source"},
            transcript_provider=provider,
        )

    assert excinfo.value.reason == NO_TRANSCRIPT
    assert not db.upserted
    assert not db.chained


@pytest.mark.parametrize("metadata", [{}, {"video_id": "abc/../../evil"}, {"video_id": "짧다"}])
@pytest.mark.asyncio
async def test_parse_transcript_revalidates_the_video_id(metadata: dict[str, Any]) -> None:
    """워커가 형태를 **다시** 잰다 — 라우터를 거치지 않은 행이 존재할 수 있다.

    ⚠️ `authenticated`에는 `raw_sources` INSERT 권한이 있어(`0007` §8) 사용자가 라우터의
    검증을 우회해 임의 `metadata.video_id`를 실은 행을 직접 만들 수 있다. 그 값을 외부
    URL 조각으로 실제로 쓰는 것은 여기이므로, 소비하는 경계가 스스로 재검증한다.
    """

    class Db(_ParseDb):
        def __init__(self) -> None:
            super().__init__({"source_type": "transcript", "content": "", "metadata": metadata})

    async def provider(video_id: str) -> str:  # pragma: no cover - 도달하면 안 된다
        raise AssertionError("형태가 틀린 video_id로 공급자를 부르지 않는다")

    # 재시도로 고쳐지지 않는 데이터 상태이므로 재시도 불가 사유로 끝낸다.
    with pytest.raises(ExtractionQualityError):
        await parse.run_parse(
            Db(),  # type: ignore[arg-type]
            job_id=JOB_ID,
            workspace_id=WORKSPACE_ID,
            payload={"raw_source_id": "raw-source"},
            transcript_provider=provider,
        )


@pytest.mark.asyncio
async def test_compile_materializes_normalized_bigram_lexical_page() -> None:
    """위키 업서트 결과의 id로 lexical writer RPC를 호출한다."""

    class Db:
        async def get_wiki_page_by_slug(self, **_values: str) -> None:
            return None

        async def upsert_wiki_page(self, **_values: Any) -> dict[str, str]:
            return {"id": "wiki-1"}

        async def index_wiki_page_lexical(self, **values: str) -> None:
            self.indexed = values

    db = Db()
    page = compile_handler.CompiledPage(
        title="NexusWiki 검색",
        category="concepts",
        confidence="high",
        content="NexusWiki 검색 계약",
    )

    await compile_handler._upsert_page(
        db,  # type: ignore[arg-type]
        workspace_id=WORKSPACE_ID,
        raw_source_id="raw-source",
        slug="nexuswiki-search",
        page=page,
    )

    assert db.indexed["workspace_id"] == WORKSPACE_ID
    assert db.indexed["wiki_id"] == "wiki-1"
    assert db.indexed["bigrams"] == bigram(normalize(page.content))
    assert db.indexed["tokenizer_version"] == TSV_TOKENIZER_VERSION


@pytest.mark.asyncio
async def test_parse_file_extracts_then_updates_content(monkeypatch: pytest.MonkeyPatch) -> None:
    source = {
        "source_type": "file",
        "content": "",
        "storage_path": f"{WORKSPACE_ID}/raw-source/document.txt",
        "mime_type": "text/plain",
    }
    db = _ParseDb(source)

    async def download(_client: object, *, path: str) -> bytes:
        assert path == source["storage_path"]
        return b"x" * 200

    monkeypatch.setattr(parse, "download_source_object", download)
    await parse.run_parse(
        db,  # type: ignore[arg-type]
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source"},
        settings=SimpleNamespace(),
        object_client=object(),  # type: ignore[arg-type]
    )

    assert db.updated == {"workspace_id": WORKSPACE_ID, "content": "x" * 200}
    assert db.chained


@pytest.mark.asyncio
async def test_parse_rejects_storage_path_from_another_workspace() -> None:
    db = _ParseDb(
        {
            "source_type": "file",
            "content": "",
            "storage_path": "other-workspace/raw-source/document.txt",
            "mime_type": "text/plain",
        }
    )
    with pytest.raises(parse.StorageObjectMissing):
        await parse.run_parse(
            db,  # type: ignore[arg-type]
            job_id=JOB_ID,
            workspace_id=WORKSPACE_ID,
            payload={"raw_source_id": "raw-source"},
            settings=SimpleNamespace(),
            object_client=object(),  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_parse_url_updates_response_metadata_after_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = _ParseDb({"source_type": "url", "content": "", "metadata": {"url": "https://one.invalid"}})

    async def fetch(_client: object, _url: str, *, settings: object) -> Any:
        del settings
        return SimpleNamespace(
            data=b"y" * 200, mime_type="text/plain", final_url="https://two.invalid"
        )

    monkeypatch.setattr(parse, "fetch_source", fetch)
    await parse.run_parse(
        db,  # type: ignore[arg-type]
        job_id=JOB_ID,
        workspace_id=WORKSPACE_ID,
        payload={"raw_source_id": "raw-source"},
        settings=SimpleNamespace(),
        fetch_client=object(),  # type: ignore[arg-type]
    )

    assert db.updated == {
        "workspace_id": WORKSPACE_ID,
        "content": "y" * 200,
        "mime_type": "text/plain",
        "byte_size": 200,
    }
