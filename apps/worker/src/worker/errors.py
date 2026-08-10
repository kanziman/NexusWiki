"""외부 공급자 호출이 실패했을 때 워커가 던지는 자체 예외.

관련 태스크: P2-LLM-01
설계 근거: 03-CONTEXT.md > D-05
설계 근거: checklists.json > decisions.llm

⚠️ 이 모듈의 존재 이유는 하나다 — **provider 응답 본문이 예외 객체에 실리지 않게 하는
것**. 핸들러 예외는 `worker.queue.process_next_job`이 `sanitize_error()`를 거쳐
`fail_job(error=...)`로 넘기고, 그 문자열은 `jobs.last_error`에 들어간다. 그 컬럼은
워크스페이스 멤버가 SELECT할 수 있고(`0004_rls_policies.sql`) 프론트가 그대로 보여주므로,
OpenRouter 응답 본문이 예외에 담기면 프롬프트·내부 구조가 그 경로로 새어 나간다.

`sanitize_error()`의 provider별 마스킹은 03-08이 완성한다. 그러나 마스킹은 2차 방어선이고
**1차 방어선은 본문이 애초에 예외 객체에 들어오지 않는 것**이다 — 마스킹은 알려진 형태만
지우지만, 담지 않은 것은 지울 필요가 없다.

소비자: `worker.llm` · `worker.handlers.compile` · (03-09) `worker.handlers.embed`
"""

from __future__ import annotations

from typing import Final

from nexuswiki_core.extract import ExtractionQualityError

__all__ = [
    "EmbeddingProviderMismatch",
    "LlmSchemaError",
    "NON_RETRYABLE_ERRORS",
    "ProviderError",
    "StorageObjectMissing",
    "UnsafeFetchTarget",
]


class UnsafeFetchTarget(Exception):
    """사용자 지정 URL이 SSRF 또는 페치 한계를 위반했다."""

    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class StorageObjectMissing(Exception):
    """원본 보관 경로가 가리키는 Storage 객체가 없다."""

    def __init__(self) -> None:
        super().__init__("storage_object_missing")


class ProviderError(Exception):
    """외부 모델 공급자 호출이 실패했다.

    ⚠️ `kind`는 실패의 **분류**이지 공급자가 돌려준 메시지가 아니다. 응답 본문을 담을
    필드를 두지 않는 것이 이 클래스의 설계다 — 필드가 없으면 실수로 담을 수도 없다.
    """

    def __init__(self, *, provider: str, status_code: int | None = None, kind: str) -> None:
        self.provider = provider
        self.status_code = status_code
        self.kind = kind
        super().__init__(self._describe())

    def _describe(self) -> str:
        status = "없음" if self.status_code is None else str(self.status_code)
        return f"{self.provider} 호출 실패 (kind={self.kind}, status={status})"

    def __str__(self) -> str:
        return self._describe()


class LlmSchemaError(ProviderError):
    """구조화 출력이 재시도를 모두 소진하고도 스키마를 만족하지 못했다.

    `last_error_summary`에는 Pydantic 오류의 **필드 경로와 오류 타입만** 담는다.
    ⚠️ 값(`input`)을 담으면 모델이 그대로 되뱉은 원문 조각이 `jobs.last_error`를 거쳐
    프론트에 노출된다 — 이 프로젝트에서 그것은 수집한 소스 본문의 유출이다.
    """

    def __init__(
        self,
        *,
        provider: str,
        attempts: int,
        last_error_summary: str,
        status_code: int | None = None,
    ) -> None:
        self.attempts = attempts
        self.last_error_summary = last_error_summary
        super().__init__(provider=provider, status_code=status_code, kind="schema")

    def _describe(self) -> str:
        return (
            f"{self.provider} 구조화 출력이 {self.attempts}회 시도에도 스키마를 만족하지 못했다 "
            f"({self.last_error_summary})"
        )


class EmbeddingProviderMismatch(ProviderError):
    """요청한 공급자 호스트가 아닌 다른 호스트가 임베딩을 서빙했다.

    ⚠️ 이 예외는 03-09(COMP-06)의 임베딩 핸들러가 소비한다. 여기서 함께 정의하는 이유는
    예외 모듈 하나를 두 wave가 동시에 열지 않게 하기 위해서다 — 이 페이즈에서 가장 흔한
    충돌 형태가 그것이다.

    왜 불일치가 실패여야 하는가: 공급자마다 정규화·풀링이 달라 같은 모델명이어도 벡터가
    미묘하게 다를 수 있고, 섞인 벡터는 재임베딩 외에 복구 수단이 없다. 잡 실패는 재시도로
    복구되므로 **복구 가능한 실패를 복구 불가능한 성공보다 택한다**.
    근거: 03-CONTEXT.md > D-05.
    """

    def __init__(self, *, provider: str, requested: str, served: str) -> None:
        self.requested = requested
        self.served = served
        super().__init__(provider=provider, status_code=None, kind="provider_mismatch")

    def _describe(self) -> str:
        return (
            f"{self.provider} 임베딩 공급자 불일치 — 요청 {self.requested!r}, 실제 {self.served!r}"
        )


# ⚠️ 이 목록은 재시도해도 결과가 같은 실패만 담는다. ProviderError는 공급자 복구로
# 성공할 수 있어 넣지 않는다. queue가 이 목록으로 즉시 dead-letter 하는 배선은 03-08 몫이다.
NON_RETRYABLE_ERRORS: Final[tuple[type[BaseException], ...]] = (
    ExtractionQualityError,
    UnsafeFetchTarget,
    StorageObjectMissing,
)
