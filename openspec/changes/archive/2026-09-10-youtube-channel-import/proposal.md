## Why

현재 원문 수집은 파일·URL·텍스트를 **한 건씩** 등록하는 경로뿐이다. 그런데 특정 주제의 지식이 한 유튜브 채널에 수십 편으로 쌓여 있는 경우가 흔하고, 지금은 그것을 영상 URL 하나씩 붙여넣어야 해서 사실상 수집이 불가능하다. 채널을 찾아 관련 영상만 골라 한 번에 수집할 수 있으면, 위키 컴파일의 입력 밀도가 개별 URL 등록과 비교할 수 없게 올라간다.

## What Changes

- 워크스페이스 LNB에 **YouTube 수집** 진입점과 전용 페이지를 추가한다.
- 키워드로 **채널을 검색**하고(YouTube Data API `search.list`, `type=channel`, `regionCode=KR`, `nextPageToken` 페이징) 결과에서 채널 하나를 선택한다.
- 선택한 채널의 **영상 목록을 페이지 단위로 조회**하고, 사용자가 주제와 관련된 영상만 **다중 선택**한다.
- 선택한 영상들의 **자막(스크립트)을 추출해 원문 소스로 일괄 등록**하고, 기존 `parse → compile → link_sync → embed` 파이프라인을 그대로 태워 위키까지 만든다.
- 자막 추출은 **공급자 교체가 가능한 어댑터 계약**으로 둔다. 공식 YouTube API의 `captions.download`는 영상 소유자만 호출할 수 있어 타인 채널 영상에는 원천적으로 쓸 수 없다 — 스펙은 특정 공급자에 묶지 않고, 추출 실패 시 **구분 가능한 사유**만 계약한다.
- 채널 검색 결과를 `(질의, regionCode)` 단위로 **캐싱**한다. `search.list`는 호출당 100유닛이고 일일 한도가 10,000유닛이라, 채널 검색이 이 기능에서 유일하게 비싼 호출이다.

## Capabilities

### New Capabilities

- `youtube-channel-import`: 채널 검색·선택, 채널 영상 목록 조회·다중 선택, 선택 영상의 자막 추출과 원문 소스 일괄 등록, 그리고 이 경로에서만 발생하는 실패(자막 없음·비공개·쿼터 소진) 표면화까지의 경계를 정의한다.

### Modified Capabilities

없음. 이 기능은 기존 계약을 **소비**하되 바꾸지 않는다.

- `source-ingestion`: 등록된 영상은 기존 비동기 등록·중복 판정·청크 좌표 계약을 그대로 따른다.
- `usage-guardrails`: 일괄 등록도 건별 예산 프리플라이트를 그대로 통과하며, 초과 시 기존 402 경로를 쓴다.
- `tenant-data-isolation`: 등록 대상은 항상 요청자가 속한 현재 워크스페이스이며 RLS가 경계를 강제한다.

## Impact

**새로 생기는 것**

- 대시보드: LNB 항목, `/w/[workspaceId]/youtube` 페이지, 채널 검색·영상 선택 UI.
- API: 채널 검색, 채널 영상 목록, 선택 영상 일괄 등록 엔드포인트.
- 워커: 자막 추출 어댑터와 그 실패 사유, 그리고 채널 검색·영상 목록 내부 리스너.
- 설정: YouTube Data API 키(서비스 공용). **키는 워커가 소유하고 API는 내부 토큰으로 프록시한다** — `ApiSettings`는 provider 자격증명을 담을 수 없다(`design.md` D5).
- 검색 결과 캐시. 저장 위치는 `design.md`의 D3이 정한다 — DB 마이그레이션은 없다.

**영향받는 기존 코드**

- `apps/api/src/api/routers/sources.py` — 일괄 등록이 기존 `_insert_and_enqueue` 경로를 재사용한다.
- `apps/worker/src/worker/handlers/parse.py` — 자막 소스의 추출 분기가 붙는다.
- `apps/dashboard/components/WorkspaceSidebar.tsx` — LNB 진입점.

**외부 의존성**

- YouTube Data API v3 (검색·영상 목록). 일일 쿼터 10,000유닛.
- 자막 추출 공급자 1종(어댑터 뒤에 위치, 교체 가능).
