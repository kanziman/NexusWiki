"""OpenRouter 채팅 클라이언트와 오류 되먹임 구조화 출력.

관련 태스크: P2-LLM-01 (COMP-01, COMP-03)
설계 근거: 03-CONTEXT.md > D-04
설계 근거: checklists.json > decisions.llm, decisions.structured_output
설계 근거: supabase/migrations/0006_seed_prompts.sql:13-17 (플레이스홀더 규약)

`worker.db.service`의 팩토리 형태를 그대로 따른다 — 모듈 전역 클라이언트를 두지 않는다.
전역을 두는 순간 import가 키를 읽으려 시도하게 되어 "막히는 것은 import가 아니라 키다"라는
02-CONTEXT.md > D-06의 인과가 흐려진다.

⚠️ 이 모듈은 프롬프트 본문도 응답 본문도 **로그 필드로 싣지 않는다** (T-03-21).
`nexuswiki_core.logging`의 `REDACTED_KEYS`는 필드 이름만 보므로 이름을 바꾸면 그대로
새어 나간다 — 마스킹에 기대지 않고 애초에 싣지 않는 것이 유일하게 믿을 수 있는 규율이다.

소비자: `worker.handlers.compile`
"""

from __future__ import annotations

import math
import re
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any, Final

import httpx
from pydantic import BaseModel, ValidationError

from nexuswiki_core.logging import get_logger
from worker.errors import LlmSchemaError, ProviderError
from worker.settings import WorkerSettings

__all__ = [
    "LLM_REQUEST_TIMEOUT_SECONDS",
    "OPENROUTER_BASE_URL",
    "PROVIDER_NAME",
    "STRUCTURED_OUTPUT_MAX_ATTEMPTS",
    "LlmResult",
    "cost_micros",
    "complete_structured",
    "openrouter_client",
    "render_template",
    "stream_chat",
]

OPENROUTER_BASE_URL: Final[str] = "https://openrouter.ai/api/v1"
PROVIDER_NAME: Final[str] = "openrouter"

# ⚠️ `SERVICE_REQUEST_TIMEOUT_SECONDS`(PostgREST, 10초)와 **의도적으로 다른 값**이다.
#    PostgREST 왕복은 인덱스 조회라 10초를 넘으면 그 자체가 장애 신호지만, LLM 완성은
#    정상 동작이 수십 초다. 두 값을 같게 두면 정상적인 컴파일이 타임아웃으로 실패해
#    at-least-once 재시도가 같은 비용을 다시 지불한다.
LLM_REQUEST_TIMEOUT_SECONDS: Final[float] = 120.0

# 프롬프트 + Pydantic 검증 + 3회 재시도는 `response_format` 지원 여부와 **무관하게 항상**
# 도는 필수 백스톱이다 (checklists.json > decisions.structured_output).
STRUCTURED_OUTPUT_MAX_ATTEMPTS: Final[int] = 3

# `{{변수}}` 이중 중괄호. 이름은 `0006`이 쓰는 ASCII 스네이크 케이스로 한정한다.
_PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")

_logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class LlmResult:
    """검증을 통과한 payload와 그 호출의 사용량.

    `cost_micros`는 **정수 micro-dollar**다 — `usage_events.cost_micros`(bigint)와 같은
    축이며 비용 경로 어디에도 부동소수를 두지 않는다 (03-02-PLAN.md > D-P2).
    """

    payload: BaseModel
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_micros: int
    provider: str
    model: str


def openrouter_client(
    settings: WorkerSettings,
    *,
    timeout_seconds: float = LLM_REQUEST_TIMEOUT_SECONDS,
) -> httpx.AsyncClient:
    """`WorkerSettings`를 인자로 받아야만 OpenRouter 클라이언트를 만든다.

    ⚠️ `ApiSettings`에는 `OPENROUTER_API_KEY` 필드가 존재하지 않는다. 아래 `TypeError`는
    그 사실의 표면일 뿐 방어선 자체가 아니다 — 실제로 막는 것은 담을 그릇이 없다는 것과
    Railway가 api 서비스 env에 키를 주입하지 않는다는 것이다. 근거: 02-CONTEXT.md > D-06.
    """
    api_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if not isinstance(api_key, str) or not api_key:
        raise TypeError(
            "openrouter_client는 OPENROUTER_API_KEY를 가진 WorkerSettings를 요구한다 — "
            f"{type(settings).__name__}에는 그 필드가 없다 (02-CONTEXT.md > D-06)"
        )

    return httpx.AsyncClient(
        base_url=OPENROUTER_BASE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(timeout_seconds),
    )


def render_template(template: str, values: Mapping[str, str]) -> str:
    """`{{key}}`를 단순 문자열 치환으로 바꾼다.

    ⚠️ `str.format`을 쓰지 않는다. 프롬프트와 주입될 본문에 마크다운·코드·JSON의 **단일**
    중괄호가 그대로 들어오므로 format이 `KeyError`로 터지거나 내용을 망친다.
    근거: `supabase/migrations/0006_seed_prompts.sql:13-17`.

    ⚠️ 치환은 **한 번의 스캔**으로 끝난다 (`re.sub` 콜백). 치환 결과를 다시 스캔하지
    않는 것이 T-03-19(프롬프트 인젝션) 완화의 실물이다 — 수집된 소스 본문이 `{{...}}`를
    담고 있어도 그것은 새 플레이스홀더가 되지 못하고 리터럴로 남는다.

    치환할 값이 없는 플레이스홀더는 조용히 남기지 않고 예외로 끊는다. 오타 난
    플레이스홀더가 프롬프트에 그대로 남으면 모델은 그것을 지시로 읽을 수 있다.
    """
    matched = _PLACEHOLDER.findall(template)
    if template.count("{{") != len(matched):
        raise ValueError(
            "템플릿에 형식을 벗어난 `{{`가 있다 — 플레이스홀더 이름은 [A-Za-z0-9_]+ 여야 한다"
        )

    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise ValueError(f"플레이스홀더 {{{{{key}}}}}에 대응하는 값이 없다")
        return values[key]

    return _PLACEHOLDER.sub(substitute, template)


def _chat_stream_body(
    *, settings: WorkerSettings, messages: list[dict[str, str]]
) -> dict[str, Any]:
    """스트리밍 채팅 요청 본문. `_chat_body`와 형제 함수이지 그 대체가 아니다.

    ⚠️ `response_format`을 넣지 않는다 — 스트리밍과 구조화-출력-재시도는 서로 다른 호출
    형태다(05-RESEARCH.md "State of the Art"). `usage.include`는 `_chat_body`와 같은
    이유로 필요하다: 비어 있으면 비용 회계가 조용히 0이 된다.
    """
    return {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "stream": True,
        "usage": {"include": True},
    }


async def stream_chat(
    client: httpx.AsyncClient,
    *,
    settings: WorkerSettings,
    messages: list[dict[str, str]],
) -> AsyncIterator[bytes]:
    """OpenRouter 채팅 완성을 원문 SSE 바이트로 그대로 릴레이한다.

    `complete_structured()`의 형제 함수다 — 구조화 출력·재시도 경로를 고치지 않는다.

    ⚠️ 여기서 `choices[0].delta.content`를 파싱하지 않는다. 그 파싱은 API 쪽(05-01-PLAN.md
    Task 2)의 몫이다 — 이 함수는 투명한 바이트 릴레이일 뿐이다.
    """
    body = _chat_stream_body(settings=settings, messages=messages)
    async with client.stream("POST", "/chat/completions", json=body) as response:
        if response.status_code >= 400:
            raise ProviderError(
                provider=PROVIDER_NAME,
                status_code=response.status_code,
                kind="chat_completion",
            )
        async for line in response.aiter_lines():
            if line:
                yield (line + "\n").encode("utf-8")


async def complete_structured(
    client: httpx.AsyncClient,
    *,
    settings: WorkerSettings,
    system_prompt: str,
    user_prompt: str,
    schema_model: type[BaseModel],
) -> LlmResult:
    """스키마를 만족하는 응답이 나올 때까지 오류를 되먹여 최대 3회 시도한다.

    ⚠️ 재시도가 **같은 본문을 다시 보내는 형태여서는 안 된다.** 같은 입력에 같은 모델을
    다시 부르면 같은 실패가 돌아올 뿐이고, 그것은 재시도가 아니라 비용을 3배로 만드는
    반복이다. 그래서 시도마다 `messages`에 되먹임 턴 두 개를 덧붙인다 — assistant 역할로
    모델이 실제로 낸 원문을, user 역할로 어긴 필드 경로와 오류 타입을. 이것이 COMP-03이
    요구하는 "2·3회차가 1회차와 달라진다"의 실물이다.

    ⚠️ 되먹임 user 턴에 **오류의 필드 경로와 타입만** 싣고 값(`input`)은 싣지 않는다.
    실패 시 그 요약이 `LlmSchemaError`를 거쳐 `jobs.last_error`로 흐르기 때문이다.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    # `response_format`은 엔드포인트별 지원이라 **선택적 최적화**다. 지원하지 않으면
    # 프롬프트 전용 경로로 조용히 내려가고, 그 사실이 로그에 남는다.
    structured_supported = True
    last_summary = "원인 미상"

    for attempt in range(1, STRUCTURED_OUTPUT_MAX_ATTEMPTS + 1):
        body, structured_supported, response = await _post_chat(
            client,
            settings=settings,
            messages=messages,
            schema_model=schema_model,
            structured_supported=structured_supported,
        )
        del body  # 요청 본문은 로그에도 예외에도 남기지 않는다.
        content, usage, provider, model = _read_completion(response)

        try:
            payload = schema_model.model_validate_json(content)
        except ValidationError as error:
            last_summary = _summarise_validation_error(error)
        except ValueError:
            last_summary = "json_decode_error"
        else:
            return LlmResult(
                payload=payload,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                cost_micros=cost_micros(usage),
                provider=provider,
                model=model,
            )

        _logger.warning(
            "worker.llm_schema_violation",
            attempt=attempt,
            max_attempts=STRUCTURED_OUTPUT_MAX_ATTEMPTS,
            error_summary=last_summary,
        )
        if attempt < STRUCTURED_OUTPUT_MAX_ATTEMPTS:
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": _feedback_prompt(last_summary)})

    raise LlmSchemaError(
        provider=PROVIDER_NAME,
        attempts=STRUCTURED_OUTPUT_MAX_ATTEMPTS,
        last_error_summary=last_summary,
    )


# -- 내부 ----------------------------------------------------------------------


def _chat_body(
    *,
    settings: WorkerSettings,
    messages: list[dict[str, str]],
    schema_model: type[BaseModel],
    structured: bool,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        # ⚠️ 비용 회계를 명시적으로 요청한다. 이 키가 없으면 응답에 비용 필드가 없을 수
        #    있고, 그러면 `cost_micros = 0`이 기록되어 `0009`의 월 상한이 **영원히**
        #    걸리지 않는다 (T-03-27). 상한이 있는데 걸리지 않는 것이 상한이 없는 것보다
        #    나쁘다 — 있다고 믿게 만들기 때문이다.
        "usage": {"include": True},
    }
    if structured:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_model.__name__,
                "strict": True,
                "schema": schema_model.model_json_schema(),
            },
        }
        # 능력 탐지. 이 플래그가 있으면 OpenRouter는 위 파라미터를 실제로 지원하는
        # 엔드포인트로만 라우팅하고, 그런 엔드포인트가 없으면 4xx로 끊는다.
        body["provider"] = {"require_parameters": True}
    return body


async def _post_chat(
    client: httpx.AsyncClient,
    *,
    settings: WorkerSettings,
    messages: list[dict[str, str]],
    schema_model: type[BaseModel],
    structured_supported: bool,
) -> tuple[dict[str, Any], bool, httpx.Response]:
    """한 번의 완성 요청. 능력 탐지 실패는 시도 횟수를 소모하지 않는다."""
    body = _chat_body(
        settings=settings,
        messages=messages,
        schema_model=schema_model,
        structured=structured_supported,
    )
    response = await _send(client, body)

    if structured_supported and 400 <= response.status_code < 500:
        # 능력 탐지 실패 — `response_format`/`provider`를 빼고 프롬프트 전용으로 내려간다.
        # ⚠️ 상태 코드만 로그에 남긴다. 응답 본문에는 라우팅된 엔드포인트 목록이 실릴 수
        #    있고 그것은 우리 계정의 내부 정보다.
        _logger.warning(
            "worker.llm_structured_output_unsupported",
            status_code=response.status_code,
            model=settings.LLM_MODEL,
        )
        structured_supported = False
        body = _chat_body(
            settings=settings,
            messages=messages,
            schema_model=schema_model,
            structured=False,
        )
        response = await _send(client, body)

    if response.status_code >= 400:
        raise ProviderError(
            provider=PROVIDER_NAME,
            status_code=response.status_code,
            kind="chat_completion",
        )
    return body, structured_supported, response


async def _send(client: httpx.AsyncClient, body: dict[str, Any]) -> httpx.Response:
    try:
        return await client.post("/chat/completions", json=body)
    except httpx.HTTPError:
        # ⚠️ 원래 예외를 `from`으로 잇지 않는다. httpx 예외 문자열에 URL과 헤더가 실릴 수
        #    있고, 예외 체인은 `sanitize_error`가 보는 문자열에 들어오지 않지만 로그의
        #    스택 트레이스에는 들어온다.
        raise ProviderError(provider=PROVIDER_NAME, status_code=None, kind="transport") from None


def _read_completion(response: httpx.Response) -> tuple[str, dict[str, Any], str, str]:
    try:
        body = response.json()
    except ValueError:
        raise ProviderError(
            provider=PROVIDER_NAME,
            status_code=response.status_code,
            kind="non_json_response",
        ) from None

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError(
            provider=PROVIDER_NAME,
            status_code=response.status_code,
            kind="empty_choices",
        )
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str):
        raise ProviderError(
            provider=PROVIDER_NAME,
            status_code=response.status_code,
            kind="missing_content",
        )

    usage = body.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    # OpenRouter는 실제로 라우팅한 호스트를 최상위 `provider`로 알려준다. 없으면
    # 게이트웨이 이름으로 두되 지어내지 않는다.
    provider = body.get("provider") or PROVIDER_NAME
    model = body.get("model") or "unknown"
    return content, usage, str(provider), str(model)


def cost_micros(usage: Mapping[str, Any]) -> int:
    """달러 비용을 정수 micro-dollar로 **올림** 변환한다.

    올림인 이유: 상한 판정이 지출을 과소평가하는 방향으로 틀리면 상한을 넘긴 뒤에야
    걸린다. 과대평가 방향의 오차는 상한을 조금 일찍 걸 뿐이다.
    """
    for key in ("cost", "total_cost"):
        value = usage.get(key)
        if isinstance(value, int | float):
            return max(0, math.ceil(float(value) * 1_000_000))
    _logger.warning("worker.llm_cost_unavailable", usage_keys=sorted(usage))
    return 0


def _summarise_validation_error(error: ValidationError) -> str:
    """필드 경로와 오류 타입만 남긴다 — 값(`input`)은 절대 담지 않는다."""
    parts = [
        f"{'.'.join(str(item) for item in detail['loc']) or '<root>'}:{detail['type']}"
        for detail in error.errors()[:5]
    ]
    return ", ".join(parts) or "unknown_validation_error"


def _feedback_prompt(summary: str) -> str:
    return (
        "직전 출력이 요구된 JSON 스키마를 어겼습니다. 아래는 어긴 위치와 오류 종류입니다.\n\n"
        f"{summary}\n\n"
        "설명이나 코드펜스 없이, 스키마를 정확히 만족하는 JSON 객체 하나만 다시 출력하세요."
    )
