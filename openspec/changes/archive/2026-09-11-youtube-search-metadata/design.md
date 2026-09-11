## Context

See proposal.md - Why. `search_channels()`와 `list_channel_videos()`는 이미 워커 단일 경계(`apps/worker/src/worker/youtube.py`)에서 YouTube Data API v3를 호출하고 결과를 파싱해 pydantic 모델로 돌려준다. 이번 변경은 같은 호출 경계 안에서 파싱하는 필드를 늘리고, `search.list`에 파라미터를 몇 개 더 얹고, `channels.list` 호출을 하나 추가하는 정도라 새 아키텍처 패턴이 필요하지 않다.

## Goals / Non-Goals

**Goals:**
- 이미 응답에 들어있던 필드(caption, statistics) 및 저비용 추가 호출(channels.list 배치)로 채널·영상 카드의 정보 밀도를 높인다.
- 자막 유무를 선택 이전에 보여줘 `no_transcript` 실패를 사전에 줄인다.
- 검색 정렬·언어·지역을 사용자가 직접 조정할 수 있게 한다.

**Non-Goals:**
- `region_code`가 실제로 검색 결과에 미치는 영향(YouTube 알고리즘 내부)을 재설계하거나 검증하지 않는다 — 기존 파라미터를 그대로 노출할 뿐이다.
- `topicId`, `videoCaption`(video 전용 필터), `publishedAfter/Before` 등 이번에 채택하지 않기로 한 파라미터는 다루지 않는다(지난 대화에서 이미 배제 근거를 논의함).
- 캡션 배지가 "true"를 보장하는 것은 아니다 — `contentDetails.caption`은 공식 캡션 트랙 존재 여부만 알려주며, 이 앱의 실제 자막 수집 경로(비공식)와 100% 일치한다는 보장은 하지 않는다. 배지는 힌트이지 확정 판정이 아니다.

## Decisions

**결정: `channels.list` 배치 조회는 `search_channels()` 내부에서 동기적으로 이어서 호출한다(별도 API 왕복 없음).**

거부된 대안 — *프론트엔드가 채널 카드를 렌더링한 뒤 통계를 별도로 lazy-fetch*: 카드가 통계 없이 먼저 뜨고 나중에 채워지는 2단계 렌더링이 되어 체감 복잡도가 늘고, 워커·API 내부 토큰 경계를 하나 더 추가해야 한다(`YOUTUBE_SEARCH_INTERNAL_TOKEN` 하나로 검색 전체를 인증하는 현재 구조와 어긋남). `channels.list`가 최대 50개 ID를 한 번에 받고 비용이 1유닛뿐이라 동기 호출의 지연이 무시할 만하다.

**결정: 채널 통계 조회 실패는 검색 전체를 실패시키지 않는다.**

`search.list`가 성공했는데 `channels.list`가 실패(네트워크 일시 장애 등)하면, 통계 없이 핵심 필드(채널 ID·이름·설명·썸네일)만이라도 돌려준다 — 이미 100유닛을 쓴 검색 결과를 통계 하나 때문에 통째로 버리지 않는다. delta spec의 "Channel statistics cannot be enriched" 시나리오가 이 결정을 명시한다.

**결정: `order`/`relevanceLanguage`/`region_code`는 검색 페이지네이션 키에 포함한다.**

`youtube-channel-import` 스펙의 "Search quota conservation" 요구사항(동일 키워드 재검색은 저장된 결과로 서빙)이 키워드+지역만 보고 있었다면, 정렬이나 언어를 바꿨는데 캐시된 이전 결과를 그대로 돌려주는 버그가 생긴다. 캐시 키(있다면)에 새 파라미터를 포함시켜야 한다 — 구현 단계에서 `apps/api/src/api/routers/youtube.py`의 캐시 키 구성을 확인하고 필요시 확장한다.

## Risks / Trade-offs

- [`channels.list` 배치 호출이 실패하면 채널 카드가 통계 없이 뜬다] → 위 "실패해도 핵심 필드는 반환" 결정으로 완화. UI는 통계 필드가 `null`일 때 해당 배지를 숨긴다.
- [사용자가 정렬/언어/지역을 바꿀 때마다 새 `search.list` 호출(100유닛)이 나간다] → 기존에도 키워드 재검색은 100유닛이었고, 이번 변경이 새로운 비용 패턴을 만들지 않는다. 다만 캐시 키 확장(위 결정)을 빠뜨리면 정렬을 바꿔도 옛 결과가 나오는 조용한 실패가 생길 수 있어 tasks.md에서 명시적으로 확인한다.
- [`contentDetails.caption`이 이 앱의 실제 자막 수집 성공 여부와 완전히 일치하지 않을 수 있음] → 배지 문구를 "자막 없음 확정"이 아니라 "자막 없을 수 있음" 톤으로 잡아, 배지가 없어도 선택 자체는 막지 않는다(정보 제공이지 차단이 아님).
