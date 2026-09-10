"""youtube-channel-import 슬라이스 2 — 자막 어댑터 경계의 회귀 (Task 2.2).

⚠️ 이 파일은 어댑터의 **계약**만 검증한다. 공급자 이름으로 분기하는 단언을 여기 두면
공급자를 갈아 끼울 때 스펙이 아니라 테스트가 먼저 막아선다 — design D2가 어댑터를 둔
이유가 사라진다. 공급자 예외 타입이 등장하는 곳은 분류 테스트 하나뿐이다.
"""

from __future__ import annotations

from typing import Any

import pytest
from youtube_transcript_api import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)

from worker.errors import NON_RETRYABLE_ERRORS
from worker.transcript import (
    _PERMANENT_REASONS,
    _TRANSIENT_REASONS,
    NO_TRANSCRIPT,
    PROVIDER_UNAVAILABLE,
    TRANSCRIPT_FAILURE_REASONS,
    VIDEO_UNAVAILABLE,
    TranscriptPermanentlyUnavailable,
    TranscriptProviderUnavailable,
    TranscriptUnavailable,
    _classify,
    _select_transcript,
    fetch_transcript,
    transcript_failure,
)


class _Snippet:
    def __init__(self, text: str) -> None:
        self.text = text


class _Transcript:
    def __init__(self, label: str, snippets: list[str] | None = None) -> None:
        self.label = label
        self._snippets = [_Snippet(text) for text in (snippets or ["본문"])]

    def fetch(self) -> list[_Snippet]:
        return self._snippets


class _TranscriptList:
    """`find_*` 셋과 반복만 흉내 낸다 — 어댑터가 실제로 쓰는 표면이 그뿐이다."""

    def __init__(
        self,
        *,
        manual: dict[str, _Transcript] | None = None,
        generated: dict[str, _Transcript] | None = None,
    ) -> None:
        self._manual = manual or {}
        self._generated = generated or {}

    def _pick(self, pool: dict[str, _Transcript], languages: list[str]) -> _Transcript:
        for language in languages:
            if language in pool:
                return pool[language]
        raise NoTranscriptFound("v1", languages, self)

    def find_manually_created_transcript(self, languages: list[str]) -> _Transcript:
        return self._pick(self._manual, languages)

    def find_generated_transcript(self, languages: list[str]) -> _Transcript:
        return self._pick(self._generated, languages)

    def find_transcript(self, languages: list[str]) -> _Transcript:
        try:
            return self._pick(self._manual, languages)
        except NoTranscriptFound:
            return self._pick(self._generated, languages)

    def __iter__(self) -> Any:
        return iter([*self._manual.values(), *self._generated.values()])


# -----------------------------------------------------------------------------
# 언어 우선순위 — 한국어 자동생성이 영어 수동보다 앞선다
# -----------------------------------------------------------------------------


def test_korean_manual_transcript_wins() -> None:
    chosen = _select_transcript(
        _TranscriptList(
            manual={"ko": _Transcript("ko-manual"), "en": _Transcript("en-manual")},
            generated={"ko": _Transcript("ko-generated")},
        )
    )
    assert chosen.label == "ko-manual"


def test_korean_generated_beats_english_manual() -> None:
    # ⚠️ 공급자의 `find_transcript(["ko", "en"])`을 그대로 쓰면 여기서 en-manual이
    #    이긴다. 이 서비스의 기본 독자에게는 뒤집힌 순서다.
    chosen = _select_transcript(
        _TranscriptList(
            manual={"en": _Transcript("en-manual")},
            generated={"ko": _Transcript("ko-generated")},
        )
    )
    assert chosen.label == "ko-generated"


def test_english_is_used_when_korean_is_absent() -> None:
    chosen = _select_transcript(
        _TranscriptList(generated={"en": _Transcript("en-generated")}),
    )
    assert chosen.label == "en-generated"


def test_any_available_transcript_beats_giving_up() -> None:
    # 언어 선택 UI가 없는 범위(design Non-Goals)에서 있는 자막을 안 쓰고 "자막 없음"으로
    # 끝내면 그것이 조용한 실패다.
    chosen = _select_transcript(_TranscriptList(manual={"ja": _Transcript("ja-manual")}))
    assert chosen.label == "ja-manual"


def test_empty_transcript_list_is_no_transcript() -> None:
    with pytest.raises(TranscriptUnavailable) as excinfo:
        _select_transcript(_TranscriptList())
    assert excinfo.value.reason == NO_TRANSCRIPT


# -----------------------------------------------------------------------------
# 실패 사유 — 재시도가 무의미한 것과 그렇지 않은 것을 가른다
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TranscriptsDisabled("v1"), NO_TRANSCRIPT),
        (NoTranscriptFound("v1", ["ko"], None), NO_TRANSCRIPT),
        (VideoUnavailable("v1"), VIDEO_UNAVAILABLE),
        (InvalidVideoId("v1"), VIDEO_UNAVAILABLE),
        # 인증 없이는 몇 번을 재시도해도 같다 — 일시 장애로 두면 재시도를 전부 태운다.
        (AgeRestricted("v1"), VIDEO_UNAVAILABLE),
        (IpBlocked("v1"), PROVIDER_UNAVAILABLE),
        (RequestBlocked("v1"), PROVIDER_UNAVAILABLE),
        (RuntimeError("알 수 없는 실패"), PROVIDER_UNAVAILABLE),
    ],
)
def test_provider_failures_fold_into_three_reasons(error: Exception, expected: str) -> None:
    assert _classify(error) == expected


def test_unknown_reason_cannot_be_constructed() -> None:
    # 사유 어휘가 조용히 늘어나면 호출부의 분기가 그 값을 모른 채 기본 경로로 흘린다.
    with pytest.raises(ValueError, match="자막 실패 사유"):
        TranscriptUnavailable(reason="made_up")


# -----------------------------------------------------------------------------
# 재시도 판정 — 사유가 아니라 타입으로 드러난다 (Task 4.2)
# -----------------------------------------------------------------------------


def test_every_reason_declares_whether_retrying_is_pointless() -> None:
    # ⚠️ 새 사유를 더하면서 어느 쪽인지 정하지 않으면 그 사유는 조용히 "재시도 가능"으로
    #    흘러가 자막 없는 영상처럼 `max_attempts`를 태운다. 이 단언이 그때 red가 된다.
    assert _PERMANENT_REASONS | _TRANSIENT_REASONS == TRANSCRIPT_FAILURE_REASONS
    assert not (_PERMANENT_REASONS & _TRANSIENT_REASONS)


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (NO_TRANSCRIPT, TranscriptPermanentlyUnavailable),
        (VIDEO_UNAVAILABLE, TranscriptPermanentlyUnavailable),
        (PROVIDER_UNAVAILABLE, TranscriptProviderUnavailable),
    ],
)
def test_factory_picks_the_type_that_encodes_retryability(
    reason: str, expected: type[TranscriptUnavailable]
) -> None:
    failure = transcript_failure(reason)

    assert type(failure) is expected
    assert failure.reason == reason


def test_permanent_failures_are_dead_lettered_and_transient_ones_are_not() -> None:
    """큐는 `NON_RETRYABLE_ERRORS`에 대한 isinstance로 dead-letter를 정한다."""
    assert isinstance(transcript_failure(NO_TRANSCRIPT), NON_RETRYABLE_ERRORS)
    assert isinstance(transcript_failure(VIDEO_UNAVAILABLE), NON_RETRYABLE_ERRORS)
    # ⚠️ 공급자 일시 장애까지 dead로 확정하면, 프록시 교체로 풀릴 수 있었던 영상이
    #    되살아날 수 없게 된다 (design이 꼽은 최대 리스크의 복구 경로).
    assert not isinstance(transcript_failure(PROVIDER_UNAVAILABLE), NON_RETRYABLE_ERRORS)


def test_base_class_alone_is_not_dead_lettered() -> None:
    # 기반 클래스를 목록에 넣으면 일시 장애까지 함께 dead가 된다 — 그래서 넣지 않았고,
    # 그 대가로 `transcript_failure`를 거치지 않은 raise는 재시도된다. 이 사실을 못
    # 박아 두지 않으면 다음 사람이 기반 클래스를 직접 raise 한다.
    assert not isinstance(TranscriptUnavailable(reason=NO_TRANSCRIPT), NON_RETRYABLE_ERRORS)


def test_adapter_never_raises_the_retryable_base_class() -> None:
    """어댑터가 실제로 올리는 것은 언제나 재시도 여부가 정해진 하위 타입이다."""
    import inspect

    import worker.transcript as module

    source = inspect.getsource(module)
    # 위 테스트가 못 박은 함정을 어댑터 자신이 밟지 않는지 본다.
    assert "raise TranscriptUnavailable(" not in source


# -----------------------------------------------------------------------------
# 진입점 — 공급자 예외가 밖으로 새지 않는다
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_transcript_joins_snippets_into_plain_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import worker.transcript as module

    monkeypatch.setattr(
        module, "_fetch_blocking", lambda video_id: "안녕하세요 오늘은 파이썬을 다룹니다"
    )

    assert await fetch_transcript("v1") == "안녕하세요 오늘은 파이썬을 다룹니다"


@pytest.mark.asyncio
async def test_provider_exception_never_escapes_the_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import worker.transcript as module

    def boom(video_id: str) -> str:
        raise IpBlocked("v1")

    monkeypatch.setattr(module, "_fetch_blocking", boom)

    # ⚠️ 공급자 예외 타입이 그대로 올라가면 공급자를 바꾸는 순간 호출부가 함께 깨진다.
    with pytest.raises(TranscriptUnavailable) as excinfo:
        await fetch_transcript("v1")
    assert excinfo.value.reason == PROVIDER_UNAVAILABLE


@pytest.mark.asyncio
async def test_blank_transcript_body_is_no_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    import worker.transcript as module

    monkeypatch.setattr(module, "_fetch_blocking", lambda video_id: "   ")

    with pytest.raises(TranscriptUnavailable) as excinfo:
        await fetch_transcript("v1")
    # 트랙은 있는데 본문이 비었다 — 재시도해도 같으므로 일시 장애가 아니다.
    assert excinfo.value.reason == NO_TRANSCRIPT


@pytest.mark.asyncio
async def test_missing_video_id_fails_without_calling_the_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import worker.transcript as module

    def boom(video_id: str) -> str:  # pragma: no cover - 도달하면 안 된다
        raise AssertionError("video_id가 없으면 공급자를 부르지 않아야 한다")

    monkeypatch.setattr(module, "_fetch_blocking", boom)

    with pytest.raises(TranscriptUnavailable) as excinfo:
        await fetch_transcript("")
    assert excinfo.value.reason == VIDEO_UNAVAILABLE
