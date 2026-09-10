# Tenant Isolation 리뷰 — youtube-channel-import r1

- 판정: needs_fix
- 대상: `git diff main...HEAD` (c0176fb) + 커밋되지 않은 워킹트리 (슬라이스 2~4)
- 일시: 2026-09-10T05:41:19Z

리뷰 범위는 이 change가 만든 표면으로 한정한다. `main...HEAD`에는 이미 머지된 PR
(#111 · #118~#124)의 diff가 함께 들어오지만, 그것은 각자의 리뷰를 이미 통과한 코드다.
아래 마이그레이션 항목(E-15)에서만 그 부분을 명시적으로 확인했다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `routers/youtube.py:73-80` · `routers/sources.py:584`가 전부 요청자 JWT `UserDb`를 만든다. `apps/api/src` 전체에 `service_client` 호출이 없다. YouTube 키는 워커만 소유하고(`worker/youtube.py`) API는 내부 호출자 토큰으로 프록시한다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 이 change에 마이그레이션이 없다 (`design.md > Migration Plan`). `transcript`는 `0001:97`의 기존 check 값이다 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | SQL 변경이 0줄이다 |
| A-4 | service_role 코드의 workspace_id 필터 | 통과 | 새 워커 경로가 건드리는 DB는 `update_raw_source_content` 하나이며 `db/service.py:246`에서 `id` + `workspace_id` 두 필터를 건다. `handlers/parse.py`의 transcript 분기는 `get_raw_source(…, workspace_id=workspace_id)`로 읽은 행만 쓴다. 내부 리스너 두 개는 DB를 아예 만지지 않는다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음. transcript 소스는 기존 `raw_sources` → `source_chunks(raw_source_id, workspace_id)` 경로를 그대로 탄다 |
| B-6 | 0행 → 403 매핑 | 통과 (단서 1건) | `routers/youtube.py:90-95`가 `has_workspace_role` RPC의 0행/false를 `WorkspaceForbidden(affected=0)`으로 올린다. 일괄 등록에는 UPDATE/DELETE가 없고, `insert_one`의 0행은 `db/user.py:151-152`가 `WorkspaceForbidden`으로 바꾸며 그 예외는 `_register_one_video`의 `except DatabaseError`에 **걸리지 않으므로**(별개 클래스) 403으로 그대로 나간다. 단서는 아래 조치 1번 |
| B-7 | SQLSTATE 42501 → 403 | 통과 | `routers/sources.py:544-546`이 42501만 재raise하고 나머지를 영상별 `failed`로 접는다. `errors.py:243-246`의 단일 핸들러가 403 고정 본문으로 렌더한다. `test_sources_router.py:732`가 왕복으로 단언한다 |
| C-8 | 멱등성 (upsert 키) | 통과 | 중복 키는 정규화된 영상 URL 해시다 — `_canonical_video_url()` → `_text_content_hash()` → `(workspace_id, content_hash)` 유니크(`0001:118`). 자막 본문이 아니라 영상 신원이 기준이라 자막이 바뀌어도 두 번 수집되지 않는다. parse 재실행은 `(raw_source_id, chunk_index)` 업서트 + `delete_source_chunks_from` 잔여 삭제로 파생 레코드를 늘리지 않는다 |
| C-9 | jobs 직접 UPDATE 금지 | 통과 (테스트 한정 예외) | 프로덕션 코드는 `enqueue_source_job` · `complete_job_and_chain` · `dead_letter_job` RPC만 쓴다. `apps/api/tests/conftest.py`의 신규 `dead_letter_job` 픽스처만 admin 키로 `jobs`를 PATCH 하며, 준비 전용임이 주석에 명시돼 있다 — 아래 관찰 3번 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 검색 질의 코드 변경 없음 |
| D-11 | 색인·질의 토크나이저 일치 | 통과 | transcript 분기는 다른 소스 유형과 **같은 합류 지점 이후**에 청킹된다(`handlers/parse.py`의 `strip_forged_anchors` 아래). 색인도 같은 `bigram(normalize(content))` + `TSV_TOKENIZER_VERSION` 경로다 — 자막만의 별도 토크나이저가 없다 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 변경 없음. 신규 코드의 `.format(` 사용은 테스트의 URL 조립뿐이다 |
| D-14 | 인용 앵커 | 통과 | transcript 소스는 기존 `raw_source_id` + `chunk_index` + char 구간 좌표를 그대로 얻고, 원문 영상으로 돌아갈 `metadata.url`이 행에 남는다(`routers/sources.py:530`). 타임코드를 버리는 것은 design의 명시적 대가다 |
| D (쿼터·소멸·설정 누락 구분) | | **위반 1건** | 404는 본문 토큰까지 대조해 "라우트 미등록"과 "채널 소멸"을 가르지만(`routers/youtube.py:187`), 503은 상태 코드만으로 쿼터 소진으로 읽는다(`:184-186`) — 아래 조치 2번 |
| D (SEC-01 자격증명 격리) | | 통과 | `ApiSettings`에 추가된 것은 `YOUTUBE_VIDEOS_TIMEOUT_SECONDS: float = 18.0` 하나뿐이고 자격증명이 아니다. `packages/core/tests/test_settings.py:66`의 허용 목록에 근거와 함께 등록됐다. `YOUTUBE_API_KEY`는 `WorkerSettings`에만 있다 |
| D (비밀 누출) | | 통과 | `sanitize_error`가 `TranscriptUnavailable`을 **사유 토큰만**으로 접는다(`queue.py:124-129`) — 공급자 예외 문자열이 `jobs.last_error`에 닿지 않는다. `YoutubeUnavailable` · `TranscriptUnavailable` 둘 다 응답 본문을 담을 필드를 두지 않았고, 워커 `_InternalGuard.run`이 모든 미분류 예외를 고정 detail의 502로 접는다. 응답 본문에 실리는 것은 기계 판독 토큰뿐이다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 이 change는 마이그레이션을 추가하지 않는다. 브랜치가 함께 들고 오는 `0020`이 원격에는 `0021`보다 먼저 적용돼 있다는 사실과 그 처치는 `docs/ops/migration-0021-record.md`에 이미 기록돼 있다 — 신규 위험이 아니다 |

### 호출자가 지목한 확인 항목

| 질문 | 결과 |
| --- | --- |
| 1. SEC-01 (provider 자격증명 유입) | 통과. 위 표 참조 |
| 2. 일괄 등록의 워크스페이스 경계 | **부분 위반** — 타 워크스페이스 요청은 소스를 0개 만든다(RLS가 INSERT를 막는다, 42501은 `WITH CHECK`가 heap insert보다 먼저 평가되므로 23505보다 항상 앞선다 → 남의 테넌트 중복 존재 여부도 새지 않는다). 그러나 "첫 INSERT에서 끊긴다"는 전제가 **INSERT가 한 번도 시도되지 않는 입력**에서 성립하지 않는다 — 조치 1번 |
| 3. 비멤버의 공용 쿼터 소비 | 통과. `_require_membership`이 검색에서는 캐시 조회보다 앞서고(`routers/youtube.py:240` vs `:242`), 영상 목록에도 업스트림 호출 앞에 걸려 있다(`:282`). 캐시 키에 `workspace_id`가 없는 것은 의도이며(공개 데이터), 멤버십이 먼저 판정되므로 캐시 히트가 경계를 넘지 않는다 |
| 4. 조용한 실패 (쿼터·소멸·설정 누락) | **부분 위반** — 라우트 미등록 404는 정확히 구분된다(FastAPI 기본 404 본문의 detail이 `Not Found`라 토큰 대조에서 떨어지고 502가 된다). 503만 토큰 대조가 없다 — 조치 2번 |
| 5. 멱등성 | 통과. 위 C-8 참조 |
| 6. 재시도 판정 | 통과. `NON_RETRYABLE_ERRORS`에 `TranscriptPermanentlyUnavailable`만 넣고 기반 클래스를 뺀 선택이 옳다 — 기반을 넣으면 IP 차단(`provider_unavailable`)까지 즉시 dead가 된다. `transcript.py` 안의 모든 raise가 `transcript_failure()`를 지나며, `fetch_transcript`의 `except TranscriptUnavailable: raise`가 타입을 보존한다. 기반 클래스를 직접 raise 하는 표면은 남아 있지 않다(`test_transcript.py`가 두 사유 집합의 합집합을 단언). 워커 단위 테스트 70건 green |
| 7. 비밀 누출 | 통과. 위 표 참조 |

## 조치가 필요한 항목

1. **INSERT를 한 번도 시도하지 않는 일괄 요청은 비멤버에게도 202를 돌려준다** (심각도: 보통)
   - 위치: `apps/api/src/api/routers/sources.py:511-512` (사전 거부) · `:569-574` (그 전제를 적은 docstring) · `:616`
   - 깨지는 것: `_register_one_video`는 `_VIDEO_ID_PATTERN`에 걸린 영상을 **DB를 만지기 전에** `failed/bad_video_id`로 돌려준다. 따라서 선택한 영상이 전부 형태 불량이면 루프 전체가 INSERT 없이 끝나고, 엔드포인트는 `202 {"results": [...]}`를 돌려준다. 이 경로의 격리 판정자는 오직 INSERT의 `WITH CHECK`이므로, **판정자가 한 번도 호출되지 않는 입력이 존재한다.** 결과는 비멤버가 남의 `workspace_id`에 대해 성공 계열 응답을 받는 것이다 — 데이터는 새지 않고 행도 만들어지지 않지만, delta spec의 "Registration targets another workspace → the system **denies the request**"와 D-12의 균일한 Forbidden 태도가 이 입력에서만 성립하지 않는다. docstring의 "비멤버의 요청은 **첫 INSERT에서** 42501이 된다"도 이 경우 사실이 아니다.
   - 부수 사실(위반은 아님): 첫 영상이 `bad_video_id`로 건너뛰어진 뒤 두 번째에서 42501이 나면 403이 나가고 앞선 `results`는 버려진다. 비멤버는 어차피 어떤 INSERT도 성공시킬 수 없으므로 "소스 0개"는 유지된다. 앞선 결과가 실제로 유실되는 유일한 경우는 배치 도중 멤버십이 박탈되는 경합인데, 그때도 경계는 넘지 않는다.
   - 조치: 루프가 끝난 뒤 **INSERT를 한 번도 시도하지 않았다면** `has_workspace_role(ws, 'editor')`를 한 번 물어 실패 시 `WorkspaceForbidden(table="raw_sources", affected=0)`을 올린다. TOCTOU 우려는 여기에 적용되지 않는다 — 이 경로는 아무것도 쓰지 않으므로 조회와 쓰기 사이의 창이 애초에 없다. (선조회를 앞에 두지 않은 원 설계 의도는 그대로 지켜진다.)

2. **워커의 503만 본문 토큰 대조 없이 쿼터 소진으로 읽는다** (심각도: 낮음)
   - 위치: `apps/api/src/api/routers/youtube.py:184-186`
   - 깨지는 것: 바로 세 줄 아래(`:187`)의 404는 `_error_detail(response) == "youtube_channel_not_found"`까지 대조해 "워커가 라우트를 등록하지 않았다"와 "채널이 사라졌다"를 가른다. 같은 방어가 503에는 없다. 현재 배포 형태(`http://worker.railway.internal:8081`, L7 프록시 없음)에서는 503의 발신자가 사실상 워커 가드뿐이라 지금 당장 오작동하지는 않는다. 그러나 이 값 앞에 인그레스·프록시·서비스 메시가 한 번이라도 끼는 순간, 워커가 죽어서 나온 503이 사용자에게 "오늘 사용할 수 있는 YouTube 조회 횟수를 모두 썼습니다. **내일** 다시 시도해 주세요."(`YoutubeVideoList.tsx:49-50`)로 표시된다 — 장애가 쿼터 소진으로 위장되고, 이 change가 요구사항 3에서 막으려던 것과 정확히 같은 종류의 뭉개짐이 방향만 반대로 발생한다.
   - 조치: `if response.status_code == 503 and _error_detail(response) == "youtube_quota_exceeded":`로 좁히고, 토큰이 다른 503은 `YoutubeUnavailable`로 떨어뜨린다. 404 분기와 대칭이 된다.

3. **워커의 transcript 분기가 `video_id` 형태를 재검증하지 않는다** (심각도: 낮음)
   - 위치: `apps/worker/src/worker/handlers/parse.py`의 transcript 분기 (`video_id`를 `isinstance(str) and truthy`로만 검사) ↔ `apps/api/src/api/routers/sources.py:84-86`의 주석
   - 깨지는 것: API 주석은 "영상 id는 정규화된 URL로 조립되어 `metadata`에 저장되고 **워커가 그 값을 그대로 쓴다**"를 근거로 `^[A-Za-z0-9_-]{11}$`를 못 박았다. 그런데 `0007` 섹션 8이 `authenticated`에게 `raw_sources` INSERT를 직접 부여하므로(`grant select, insert, delete … to authenticated`), editor는 PostgREST로 `source_type='transcript'` + 임의 `metadata.video_id` 행을 만들고 `enqueue_source_job`을 직접 부를 수 있다. 그러면 API의 패턴 검사는 우회되고 워커가 그 문자열을 자막 공급자에 그대로 넘긴다. 공급자는 호스트가 `www.youtube.com`으로 고정돼 있어 SSRF로 번지지는 않으며 자기 워크스페이스 안에서만 가능하므로 테넌트 경계는 넘지 않는다 — 그래서 낮음이다. 다만 "API에서 못 박았으니 워커는 믿어도 된다"는 전제가 실제로는 성립하지 않는다는 점이 문제다. `service_role`로 도는 코드는 DB에서 읽은 값을 사용자 입력으로 취급해야 한다.
   - 조치: transcript 분기에서 같은 패턴을 한 번 더 검사하고, 어긋나면 `ExtractionQualityError(reason="unsupported_source_type")`로 즉시 dead-letter 한다(재시도해도 결과가 같다).

## 관찰 (판정에 반영하지 않음)

1. **예산 상한에 처음 닿은 영상은 잡 없는 `raw_sources` 행으로 남는다.** `_insert_and_enqueue`는 행을 만든 **뒤** 인큐에서 거부되므로(기존 계약), 그 한 건은 `content=""` · 잡 0개로 남는다. 상한이 풀린 뒤 같은 영상을 다시 고르면 23505에 걸려 화면에는 "이미 수집한 영상입니다"가 뜨는데, 실제로는 아무것도 처리되지 않은 행이다. 텍스트·URL 경로가 402를 돌려줄 때와 동일한 기존 귀결이며 이번 change가 만든 것은 아니다. 다만 20편 일괄 선택에서는 사실상 매번 발생하므로 후속 change에서 "잡 없는 소스 재인큐" 표면을 다룰 가치가 있다. 상한 도달 후 나머지 영상은 시도조차 하지 않아 고아 행이 하나로 묶이는 설계(`:598-603`)는 옳다.
2. **검색 리스너의 토큰 버킷 고갈은 502(일반 장애)로 보인다.** `rate_capacity=60`, `refill=0.2/s`라 서비스 전체가 5초에 1회로 제한된다. 고갈 시 워커는 429를 주고 API는 `response.is_error` → `YoutubeUnavailable` → 502가 되어 "잠시 후 다시 시도"로 안내된다. 사용자가 취할 행동이 실제로 "잠시 후 재시도"라 치명적이지는 않지만, 공용 쿼터 경합이 업스트림 장애로 보이는 것은 사실이다.
3. **`apps/api/tests/conftest.py`의 `dead_letter_job` 픽스처가 `jobs`를 직접 PATCH 한다.** admin 키를 쓰는 이유와 "준비 전용"이라는 경계가 주석에 명시돼 있고 프로덕션 코드는 오염되지 않았다. 다만 이 픽스처가 만드는 상태는 `dead_letter_job` RPC가 만드는 상태와 정확히 같지 않다(시도 회계를 건드리지 않는다) — 이 픽스처 위에 attempts 의존 단언을 얹지 않도록 주의한다.
4. **비공개·삭제 영상만 있는 페이지는 "수집할 수 있는 영상이 없습니다"와 "영상 더 보기"를 동시에 보여준다.** `videos.list`가 비공개 영상을 걸러내는 설계(`worker/youtube.py:335-338`)의 귀결이다. 데이터 문제는 아니고 문구 조합만 어색하다.

## 판정 근거

테넌트 경계 자체는 뚫리지 않는다. 사용자 요청 경로는 전부 요청자 JWT를 쓰고, provider 키는 워커에만 있으며, 42501은 403으로 정확히 렌더되고, 타 워크스페이스를 지정한 일괄 등록은 실제로 소스를 0개 만든다(왕복 테스트로 확인됨). 마이그레이션·`anon` GRANT·벡터 검색·토크나이저·프롬프트 템플릿은 이 change에서 건드리지 않았다. 따라서 `blocked`은 아니다.

그러나 `pass`도 아니다. 이 엔드포인트는 격리 판정을 **오직 INSERT 하나에** 위임했는데, 그 INSERT에 도달하지 않는 입력(전부 형태 불량인 영상 목록)이 존재하고 그 경우 비멤버가 202를 받는다 — 판정자가 호출되지 않는 경로를 남긴 것은 코드 수정으로 닫아야 할 위반이다. 여기에 503 뭉개짐과 워커 측 재검증 누락 두 건이 더해진다. 셋 다 데이터가 경계를 넘지 않으며 국소적인 수정으로 해결되므로 `needs_fix`다.
