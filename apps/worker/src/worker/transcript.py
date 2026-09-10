"""자막 획득 어댑터 — 본문을 돌려주거나 구분 가능한 사유로 실패한다.

관련 태스크: openspec/changes/youtube-channel-import/tasks.md Task 2.2 · 4.1 · 4.2
설계 근거: 같은 change의 `design.md` > D2

⚠️ **이 모듈의 경계가 이 기능의 유일한 방어선이다.** 공식 `captions.download`는 영상
소유자 OAuth를 요구해 타인 채널에는 원천적으로 못 쓰고, 남는 비공식 경로는 언제든
막힌다 — design이 꼽은 가장 현실적인 실패 시나리오가 "자막 공급자가 Railway의
데이터센터 IP를 차단한다"이다. 그래서 계약은 **"자막을 얻거나, 구분 가능한 사유로
실패한다"까지**이고 공급자 이름은 이 파일 밖으로 나가지 않는다. 차단이 확인되면
프록시나 유료 API로 아래 `fetch_transcript`의 속만 갈아 끼운다.

⚠️ 호출부(`worker.handlers.parse`)는 `TranscriptUnavailable.reason`만 본다. 공급자
예외 타입을 그대로 위로 올리면 공급자를 바꾸는 순간 호출부와 테스트가 함께 깨진다.

소비자: `worker.handlers.parse`
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Any, Final

__all__ = [
    "NO_TRANSCRIPT",
    "PROVIDER_UNAVAILABLE",
    "TRANSCRIPT_FAILURE_REASONS",
    "VIDEO_UNAVAILABLE",
    "TranscriptPermanentlyUnavailable",
    "TranscriptProvider",
    "TranscriptProviderUnavailable",
    "TranscriptUnavailable",
    "fetch_transcript",
    "transcript_failure",
]

# 자막 자체가 없다 — 재시도해도 결과가 같다.
NO_TRANSCRIPT: Final[str] = "no_transcript"
# 영상이 비공개·삭제·연령 제한이라 접근할 수 없다 — 재시도해도 결과가 같다.
VIDEO_UNAVAILABLE: Final[str] = "video_unavailable"
# 공급자 쪽 일시 장애(차단·요청 실패·응답 파싱 불가) — 재시도로 풀릴 수 있다.
PROVIDER_UNAVAILABLE: Final[str] = "provider_unavailable"

# ⚠️ 이 셋의 구분이 없으면 자막 없는 영상이 `max_attempts`까지 헛돈다. 앞의 둘은
#    재시도가 무의미하고 마지막 하나만 재시도로 풀린다.
TRANSCRIPT_FAILURE_REASONS: Final[frozenset[str]] = frozenset(
    {NO_TRANSCRIPT, VIDEO_UNAVAILABLE, PROVIDER_UNAVAILABLE}
)

# ⚠️ 아래 두 집합의 합집합이 `TRANSCRIPT_FAILURE_REASONS`와 정확히 같아야 한다.
#    새 사유를 더하면서 어느 쪽인지 정하지 않으면 그 사유는 재시도 판정에서 조용히
#    "재시도 가능"으로 흘러가 자막 없는 영상처럼 `max_attempts`를 태운다.
#    `tests/test_transcript.py`가 이 합집합을 단언한다.
_PERMANENT_REASONS: Final[frozenset[str]] = frozenset({NO_TRANSCRIPT, VIDEO_UNAVAILABLE})
_TRANSIENT_REASONS: Final[frozenset[str]] = frozenset({PROVIDER_UNAVAILABLE})

# 자막 언어 우선순위 (design의 Open Question을 구현 중에 확정).
# 한국어 수동 → 한국어 자동생성 → 영어(수동 우선) → 그 외 아무 자막.
# ⚠️ 공급자의 `find_transcript(["ko", "en"])` 한 방으로 대신하지 않는다. 그 함수는
#    **모든 언어의 수동 자막을 모든 자동생성 자막보다 앞세우므로** 영어 수동 자막이
#    한국어 자동생성 자막을 이긴다 — 이 서비스의 기본 독자에게는 뒤집힌 순서다.
_PRIMARY_LANGUAGES: Final[tuple[str, ...]] = ("ko",)
_FALLBACK_LANGUAGES: Final[tuple[str, ...]] = ("en",)

_WHITESPACE = re.compile(r"\s+")

# `video_id` -> 자막 평문. 실패는 `TranscriptUnavailable`로 던진다.
TranscriptProvider = Callable[[str], Awaitable[str]]


class TranscriptUnavailable(Exception):
    """자막을 얻지 못했다.

    ⚠️ 공급자 응답 본문을 담을 필드를 두지 않는다 — `worker.errors`가 세운 규약과 같다.
    이 예외 메시지는 `jobs.last_error`를 거쳐 워크스페이스 멤버에게 그대로 보이므로,
    담지 않은 것은 마스킹할 필요도 없다.
    """

    def __init__(self, *, reason: str) -> None:
        if reason not in TRANSCRIPT_FAILURE_REASONS:
            raise ValueError(f"알 수 없는 자막 실패 사유: {reason}")
        self.reason = reason
        super().__init__(reason)


class TranscriptPermanentlyUnavailable(TranscriptUnavailable):
    """재시도해도 결과가 같다 — 자막이 없거나 영상에 접근할 수 없다.

    ⚠️ 재시도 가능 여부를 `reason` 문자열이 아니라 **타입**으로 드러내는 것이 요점이다.
    큐(`worker.queue`)는 `NON_RETRYABLE_ERRORS`에 대한 `isinstance`로 dead-letter를
    판정하므로, 이 구분이 타입에 없으면 자막 없는 영상이 `max_attempts`까지 헛돌고
    그동안 정상 잡의 처리량을 갉아먹는다.
    """


class TranscriptProviderUnavailable(TranscriptUnavailable):
    """공급자 쪽 일시 장애 — 재시도로 풀릴 수 있다.

    데이터센터 IP 차단(design이 꼽은 최대 리스크)이 여기로 들어온다. 차단은 재시도로
    풀리지 않지만 프록시 교체로 풀리므로, 잡을 dead로 확정하는 대신 재시도에 맡기고
    `jobs.last_error`에 사유를 남겨 운영자가 차단을 관측할 수 있게 한다.
    """


def transcript_failure(reason: str) -> TranscriptUnavailable:
    """사유에 맞는 예외를 만든다 — 재시도 가능 여부가 타입으로 결정되도록.

    ⚠️ `TranscriptUnavailable`을 직접 raise 하지 않는다. 기반 클래스는
    `NON_RETRYABLE_ERRORS`에 없으므로 직접 raise 하면 `no_transcript`조차 재시도된다.
    """
    if reason in _PERMANENT_REASONS:
        return TranscriptPermanentlyUnavailable(reason=reason)
    if reason in _TRANSIENT_REASONS:
        return TranscriptProviderUnavailable(reason=reason)
    raise ValueError(f"재시도 여부가 정해지지 않은 자막 실패 사유: {reason}")


def _classify(error: Exception) -> str:
    """공급자 예외를 이 모듈의 세 사유 중 하나로 접는다.

    ⚠️ import를 함수 안에 두는 것이 의도다. 공급자 패키지가 없거나 못 뜨는 환경에서도
    이 모듈을 import 하는 쪽(핸들러·테스트)이 죽지 않아야, 어댑터를 갈아 끼우는 동안
    나머지 파이프라인이 계속 돈다.
    """
    from youtube_transcript_api import (
        AgeRestricted,
        InvalidVideoId,
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
        VideoUnplayable,
    )

    if isinstance(error, TranscriptsDisabled | NoTranscriptFound):
        return NO_TRANSCRIPT
    if isinstance(error, VideoUnavailable | VideoUnplayable | InvalidVideoId | AgeRestricted):
        # ⚠️ 연령 제한을 일시 장애로 분류하지 않는다. 인증 없이는 몇 번을 재시도해도
        #    같은 결과이므로, 일시 장애로 두면 그 영상이 재시도를 전부 태운다.
        return VIDEO_UNAVAILABLE
    # 차단(IpBlocked · RequestBlocked) · 요청 실패 · 응답 파싱 불가가 여기 모인다.
    # 이 하나만 재시도로 풀릴 수 있다.
    return PROVIDER_UNAVAILABLE


def _select_transcript(transcript_list: Any) -> Any:
    """`_PRIMARY_LANGUAGES` → 자동생성 → `_FALLBACK_LANGUAGES` → 아무 자막 순으로 고른다."""
    from youtube_transcript_api import NoTranscriptFound

    for finder, languages in (
        (transcript_list.find_manually_created_transcript, _PRIMARY_LANGUAGES),
        (transcript_list.find_generated_transcript, _PRIMARY_LANGUAGES),
        (transcript_list.find_transcript, _FALLBACK_LANGUAGES),
    ):
        try:
            return finder(list(languages))
        except NoTranscriptFound:
            continue

    # ⚠️ 여기서 포기하지 않는다. 한국어도 영어도 없는 채널의 자막이 여전히 쓸모 있는
    #    원문이고, 언어 선택 UI는 이번 범위 밖(design Non-Goals)이라 사람이 고를 수단이
    #    없다. 있는 자막을 안 쓰고 "자막 없음"으로 끝내면 그것이 조용한 실패다.
    for transcript in transcript_list:
        return transcript
    raise transcript_failure(NO_TRANSCRIPT)


def _fetch_blocking(video_id: str) -> str:
    """공급자 호출 — **동기**다. 이벤트 루프에서 직접 부르지 않는다."""
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    transcript = _select_transcript(api.list(video_id))
    fetched = transcript.fetch()
    # ⚠️ 시간축 정보를 여기서 버린다. 인용 좌표를 기존 청크 규약(char 구간)과 맞추기
    #    위한 의도된 대가이며(design의 Risks), 타임코드 인용은 후속 change의 몫이다.
    return _WHITESPACE.sub(" ", " ".join(snippet.text for snippet in fetched)).strip()


async def fetch_transcript(video_id: str) -> str:
    """영상 하나의 자막 평문을 돌려준다. 못 얻으면 `TranscriptUnavailable`.

    ⚠️ 공급자 라이브러리가 동기(`requests` 기반)라 `to_thread`로 밀어낸다. 이벤트 루프에서
    직접 부르면 자막 한 건의 네트워크 왕복이 워커의 큐 루프 전체를 멈춰 세운다 — 잡이
    at-least-once라 그 멈춤은 곧 `reap_stale_jobs`의 15분 타임아웃을 향해 흐르는 시간이다.
    """
    if not video_id:
        raise transcript_failure(VIDEO_UNAVAILABLE)
    try:
        text = await asyncio.to_thread(_fetch_blocking, video_id)
    except TranscriptUnavailable:
        raise
    except Exception as error:
        raise transcript_failure(_classify(error)) from None

    # ⚠️ `_fetch_blocking`이 이미 strip 하지만 여기서 다시 판정한다. 빈 본문 판정이
    #    구현체 안에만 있으면 공급자를 갈아 끼울 때 그 판정이 함께 사라지고, 빈 문자열이
    #    정상 자막으로 통과해 `parse`가 청크 0개를 만든다.
    text = text.strip()
    if not text:
        # 자막 트랙은 있는데 본문이 비었다 — 재시도해도 같으므로 "자막 없음"이다.
        raise transcript_failure(NO_TRANSCRIPT)
    return text
