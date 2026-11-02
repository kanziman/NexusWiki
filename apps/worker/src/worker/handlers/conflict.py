"""Write-time semantic conflict detection for compiled wiki pages."""

from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

from nexuswiki_core.context_budget import truncate_text_to_tokens
from nexuswiki_core.logging import get_logger
from worker.db.service import ServiceDb, service_client
from worker.errors import LlmSchemaError
from worker.llm import openrouter_client
from worker.llm_gateway import LlmCallContext, LlmGateway
from worker.settings import WorkerSettings

__all__ = [
    "CONFLICT_CHECK_JOB_TYPE",
    "ConflictJudgement",
    "handle_conflict_check",
    "run_conflict_check",
]

CONFLICT_CHECK_JOB_TYPE: Final[str] = "conflict_check"

_logger = get_logger(__name__)

_CONFLICT_SYSTEM_PROMPT: Final[str] = """You judge whether two wiki pages genuinely contradict.
Classify a factual disagreement as a contradiction. Do not classify different scope,
complementary detail, or pages about different sub-topics as a contradiction. Return
only the requested two-field JSON object."""


class ConflictJudgement(BaseModel):
    """Bounded LLM result: it can only authorize a disputed-state write."""

    model_config = ConfigDict(extra="ignore")

    is_contradiction: bool
    rationale: str = Field(min_length=1)


def _conflict_user_prompt(page_a_content: str, page_b_content: str) -> str:
    return (
        "First page:\n"
        f"{page_a_content}\n\n"
        "Second page:\n"
        f"{page_b_content}\n\n"
        "Does the second page genuinely contradict the first?"
    )


async def handle_conflict_check(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
    settings = WorkerSettings()
    async with service_client(settings) as db_client, openrouter_client(settings) as llm_client:
        await run_conflict_check(
            ServiceDb(db_client),
            llm_client,
            settings=settings,
            job_id=job_id,
            workspace_id=workspace_id,
            payload=payload,
        )


async def run_conflict_check(
    db: ServiceDb,
    llm_client: Any,
    *,
    settings: WorkerSettings,
    job_id: str,
    workspace_id: str,
    payload: dict[str, Any],
) -> None:
    """Judge only cosine-filtered candidates, then terminally complete the job."""
    raw_source_id = str(payload.get("raw_source_id") or payload.get("target_id") or "")
    if not raw_source_id:
        raise ValueError("conflict_check 잡 payload에 raw_source_id가 없다")

    gateway = LlmGateway(db, llm_client, settings)
    max_input_tokens = int(getattr(settings, "CONFLICT_MAX_INPUT_TOKENS", 4000))
    max_output_tokens = int(getattr(settings, "CONFLICT_MAX_OUTPUT_TOKENS", 512))
    per_page_budget = max(1, max_input_tokens // 2)
    already_flagged: set[str] = set()
    unjudged_pairs = 0
    pages = await db.list_wiki_pages_for_source(
        workspace_id=workspace_id, raw_source_id=raw_source_id
    )
    for page in pages:
        page_a_text, trunc_a = truncate_text_to_tokens(
            str(page.get("content") or ""), per_page_budget
        )
        candidates = await db.find_similar_wiki_pages(
            workspace_id=workspace_id, wiki_id=str(page["id"])
        )
        for candidate in candidates:
            candidate_rows = await db._select(  # noqa: SLF001 - narrow single-id lookup seam
                "wiki_pages",
                params={
                    "id": f"eq.{candidate['candidate_wiki_id']}",
                    "workspace_id": f"eq.{workspace_id}",
                    "limit": "1",
                },
            )
            if not candidate_rows:
                continue
            candidate_row = candidate_rows[0]
            page_b_text, trunc_b = truncate_text_to_tokens(
                str(candidate_row.get("content") or ""), per_page_budget
            )
            context = LlmCallContext(
                workspace_id=workspace_id,
                job_id=job_id,
                call=CONFLICT_CHECK_JOB_TYPE,
                metadata={
                    "raw_source_id": raw_source_id,
                    "truncated_input": trunc_a or trunc_b,
                    "max_input_tokens": max_input_tokens,
                },
            )
            # 판정을 적용하기 전에 게이트웨이가 이 호출의 비용을 기록한다.
            # ⚠️ 한 쌍의 스키마 소진이 잡을 실패시키면 끝난 쌍까지 다시 판정해 비용이 는다.
            #    판정하지 못한 쌍은 충돌이 아니므로 표시하지 않고 넘어간다. 전송 실패는
            #    일시 장애일 수 있어 여기서 잡지 않고 큐 재시도에 맡긴다.
            try:
                result = await gateway.complete_structured(
                    context,
                    system_prompt=_CONFLICT_SYSTEM_PROMPT,
                    user_prompt=_conflict_user_prompt(page_a_text, page_b_text),
                    schema_model=ConflictJudgement,
                    max_tokens=max_output_tokens,
                )
            except LlmSchemaError:
                unjudged_pairs += 1
                continue
            judgement = result.payload
            if judgement.is_contradiction:
                for wiki_id in (str(page["id"]), str(candidate["candidate_wiki_id"])):
                    if wiki_id not in already_flagged:
                        await db.set_wiki_page_disputed(wiki_id, workspace_id=workspace_id)
                        already_flagged.add(wiki_id)

    if unjudged_pairs:
        _logger.warning(
            "worker.conflict_pairs_unjudged",
            raw_source_id=raw_source_id,
            unjudged_pairs=unjudged_pairs,
        )
    await db.complete_job_and_chain(job_id)
