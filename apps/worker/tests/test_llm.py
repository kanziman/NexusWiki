"""구조화 출력 계약 회귀 테스트 — 재시도가 같은 요청의 반복이 아님을 고정한다.

⚠️ 네트워크를 타지 않는다. `httpx.MockTransport`로 응답을 짜고 **캡처한 요청 본문을
검사**한다 (`test_service_client.py:41-55`의 형태). 실제 OpenRouter 호출의 계약 관측은
`docs/ops/openrouter-contract-record.md`가 소유한다.
"""

import json
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, Field

from worker import llm
from worker.errors import LlmSchemaError
from worker.settings import WorkerSettings

COMPLETE_WORKER_ENV = {
    "SUPABASE_URL": "https://example.invalid",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
    "SUPABASE_SECRET_KEY": "sb_secret_test",
    "DATABASE_URL": "postgresql://postgres:pw@127.0.0.1:54422/postgres",
    "OPENROUTER_API_KEY": "sk-or-v1-test",
    "OPENAI_API_KEY": "sk-proj-test",
    "LLM_MODEL": "anthropic/claude-sonnet-4.6",
}

# 응답 본문에 실어 두고 "예외 문자열에 들어 있지 않다"를 단언할 표식.
PROVIDER_BODY_MARKER = "provider-internal-routing-detail-DO-NOT-LEAK"


class Page(BaseModel):
    title: str = Field(min_length=1)


class Result(BaseModel):
    pages: list[Page]


def build_settings() -> WorkerSettings:
    return WorkerSettings(**COMPLETE_WORKER_ENV)


def scripted_client(
    responses: list[httpx.Response], seen: list[dict[str, Any]]
) -> httpx.AsyncClient:
    """미리 정한 응답을 순서대로 돌려주며 요청 본문을 기록하는 클라이언트."""
    queue = list(responses)

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return queue.pop(0) if queue else httpx.Response(500, json={})

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=llm.OPENROUTER_BASE_URL
    )


def completion(content: str, *, cost: float | None = 0.0, status: int = 200) -> httpx.Response:
    usage: dict[str, Any] = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    if cost is not None:
        usage["cost"] = cost
    return httpx.Response(
        status,
        json={
            "provider": "Anthropic",
            "model": COMPLETE_WORKER_ENV["LLM_MODEL"],
            "choices": [{"message": {"content": content}}],
            "usage": usage,
            "_routing": PROVIDER_BODY_MARKER,
        },
    )


VALID = json.dumps({"pages": [{"title": "제목"}]})
# `title`이 최소 길이를 어긴다 — 오류 경로가 `pages.0.title`로 나온다.
INVALID = json.dumps({"pages": [{"title": ""}]})


async def run(client: httpx.AsyncClient) -> llm.LlmResult:
    return await llm.complete_structured(
        client,
        settings=build_settings(),
        system_prompt="시스템",
        user_prompt="사용자",
        schema_model=Result,
    )


# -----------------------------------------------------------------------------
# 1. 오류 되먹임 재시도 — 2·3회차가 1회차와 **달라야** 한다 (COMP-03)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_after_schema_violation_sends_a_longer_message_list() -> None:
    # ⚠️ 이 단언이 red가 되는 방식이 이 테스트의 존재 이유다. 재시도가 같은 본문을
    #    다시 보내는 구현으로 바꾸면 두 messages 길이가 같아져 여기서 깨진다.
    #    같은 입력에 같은 모델을 다시 부르는 것은 재시도가 아니라 비용 3배다.
    seen: list[dict[str, Any]] = []
    async with scripted_client([completion(INVALID), completion(VALID)], seen) as client:
        await run(client)

    assert len(seen) == 2
    assert len(seen[1]["messages"]) > len(seen[0]["messages"])
    assert seen[0]["messages"] != seen[1]["messages"]


@pytest.mark.asyncio
async def test_feedback_turn_carries_the_violated_field_path_and_not_the_value() -> None:
    seen: list[dict[str, Any]] = []
    async with scripted_client([completion(INVALID), completion(VALID)], seen) as client:
        await run(client)

    last_user = [m for m in seen[1]["messages"] if m["role"] == "user"][-1]
    assert "pages.0.title" in last_user["content"]
    # 직전 assistant 턴에 모델이 낸 원문이 들어간다 — 되먹임의 나머지 절반.
    assert seen[1]["messages"][-2] == {"role": "assistant", "content": INVALID}


@pytest.mark.asyncio
async def test_exhausted_retries_raise_without_leaking_the_provider_body() -> None:
    seen: list[dict[str, Any]] = []
    responses = [completion(INVALID) for _ in range(llm.STRUCTURED_OUTPUT_MAX_ATTEMPTS)]
    async with scripted_client(responses, seen) as client:
        with pytest.raises(LlmSchemaError) as excinfo:
            await run(client)

    assert len(seen) == llm.STRUCTURED_OUTPUT_MAX_ATTEMPTS
    message = str(excinfo.value)
    # ⚠️ 이 문자열은 `sanitize_error`를 거쳐 `jobs.last_error`가 되고 멤버에게 보인다.
    assert PROVIDER_BODY_MARKER not in message
    assert INVALID not in message
    assert excinfo.value.attempts == llm.STRUCTURED_OUTPUT_MAX_ATTEMPTS


# -----------------------------------------------------------------------------
# 2. 능력 탐지 폴백 — response_format은 선택적 최적화다 (COMP-01)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_request_declares_the_schema_and_requires_parameters() -> None:
    seen: list[dict[str, Any]] = []
    async with scripted_client([completion(VALID)], seen) as client:
        await run(client)

    assert seen[0]["response_format"]["type"] == "json_schema"
    assert seen[0]["provider"] == {"require_parameters": True}
    # 비용 회계를 명시적으로 요청하지 않으면 cost_micros가 0으로 굳는다 (T-03-27).
    assert seen[0]["usage"] == {"include": True}


@pytest.mark.asyncio
async def test_a_4xx_on_the_structured_request_falls_back_to_prompt_only() -> None:
    seen: list[dict[str, Any]] = []
    responses = [httpx.Response(404, json={"error": "no allowed providers"}), completion(VALID)]
    async with scripted_client(responses, seen) as client:
        result = await run(client)

    assert "response_format" in seen[0]
    assert "response_format" not in seen[1]
    assert "provider" not in seen[1]
    # 폴백은 **시도 횟수를 소모하지 않는다** — 스키마 재시도 예산은 검증 실패의 몫이다.
    assert isinstance(result.payload, Result)


# -----------------------------------------------------------------------------
# 3. 비용 — 정수 micro-dollar, 올림 (03-02-PLAN.md > D-P2)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_is_an_integer_rounded_up_from_dollars() -> None:
    seen: list[dict[str, Any]] = []
    async with scripted_client([completion(VALID, cost=0.0000123)], seen) as client:
        result = await run(client)

    # 12.3 micro-dollar → 13. 내림하면 상한 판정이 지출을 과소평가하는 방향으로 틀린다.
    assert result.cost_micros == 13
    assert isinstance(result.cost_micros, int)
    assert result.provider == "Anthropic"


@pytest.mark.asyncio
async def test_a_missing_cost_field_records_zero_rather_than_guessing() -> None:
    seen: list[dict[str, Any]] = []
    async with scripted_client([completion(VALID, cost=None)], seen) as client:
        result = await run(client)

    # 0을 기록하되 `worker.llm_cost_unavailable` 경고가 남는다 (T-03-27).
    assert result.cost_micros == 0


# -----------------------------------------------------------------------------
# 4. render_template — 0006의 `{{변수}}` 규약 (str.format 금지)
# -----------------------------------------------------------------------------


def test_render_template_substitutes_double_brace_placeholders() -> None:
    assert llm.render_template("a {{x}} b {{y}}", {"x": "1", "y": "2"}) == "a 1 b 2"


def test_render_template_refuses_a_placeholder_it_cannot_substitute() -> None:
    # 오타 난 플레이스홀더가 조용히 프롬프트에 남으면 모델이 그것을 지시로 읽을 수 있다.
    with pytest.raises(ValueError, match="source_titel"):
        llm.render_template("제목: {{source_titel}}", {"source_title": "값"})


def test_render_template_rejects_malformed_double_braces() -> None:
    with pytest.raises(ValueError, match=r"\{\{"):
        llm.render_template("{{ 이름 }}", {"이름": "값"})


def test_render_template_leaves_single_braces_in_values_untouched() -> None:
    # 프롬프트에 JSON·코드가 그대로 들어오므로 단일 중괄호를 건드리면 내용이 망가진다.
    rendered = llm.render_template("본문: {{body}}", {"body": '{"pages": []}'})

    assert rendered == '본문: {"pages": []}'


def test_render_template_does_not_rescan_substituted_content() -> None:
    # ⚠️ T-03-19. 수집된 소스 본문이 `{{...}}`를 담고 있어도 새 플레이스홀더가 되지
    #    못하고 리터럴로 남는다 — 이것이 단일 스캔 치환을 쓰는 유일한 이유다.
    rendered = llm.render_template("{{content}}", {"content": "{{source_title}}"})

    assert rendered == "{{source_title}}"
