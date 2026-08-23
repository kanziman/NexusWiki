# Design — ask-thread-history

## Context

동기는 `proposal.md`의 "Why"를 본다. 요구사항은 `specs/ask-thread-history/spec.md`가 정본이다. 여기서는 접근을 고정하는 현재 상태만 적는다.

- Ask UI는 `AskConversation.tsx`의 `useState<Turn[]>`만 사용한다. 새로고침·언마운트 시 턴과 인용 해소 상태가 사라진다.
- `POST /workspaces/{workspace_id}/ask`의 `AskRequest`는 `query` / `requested_k` / `template_id`만 받고 `extra="forbid"`다. `thread_id`는 422다.
- SSE 순서는 `meta` → `delta*` → `citations` → `done`이다. 서버는 모든 분기에서 `done` 페이로드를 `{}`로만 보낸다. 복원에 필요한 값은 `query`와 `citations`의 `text` + `resolved[]`에 있다.
- 사용자 Ask 경로는 이미 `UserDb`(요청자 JWT, `user_client`)다. `service_role`을 끼워 넣지 않는다.
- 작성자 소유 + 워크스페이스 멤버십 패턴의 가장 가까운 아날로그는 `0017_wiki_bookmarks.sql`이다. 다만 스펙은 멤버십을 잃은 작성자의 SELECT도 거부하므로, 즐겨찾기의 SELECT(`user_id`만)보다 한 겹 더 엄격하다.
- `AskLayout`은 대화 420 + 스플리터 6 + 인스펙터 360 = 786px 최소 예산을 하드코딩한다. `.app` 그리드에 열을 늘리는 선례는 디자인 시스템 섹션 15/16이 이미 기각했다.
- 클라우드에 적용된 최신 마이그레이션은 `0017`이다. 다음 번호는 `0018`만 허용된다.

## Goals / Non-Goals

범위는 `proposal.md`의 "What Changes"와 델타 스펙이 정의한다. 설계 수준의 경계만 덧붙인다.

**Goals:**
- 완료된 Ask 턴을 작성자 소유 행으로 서버에 남기고, 복원 시 발급된 위키·원문 마커를 클릭 가능한 상태로 재수화한다.
- 기존 SSE 순서와 단건 grounded Ask를 유지한 채 `/ask`에 스레드 식별자와 멱등 키만 더한다.
- Ask 레이아웃 예산을 깨지 않고 대화 목록을 얹는다.

**Non-Goals:**
- 이전 턴을 LLM 프롬프트에 재주입하는 멀티턴 grounded Ask.
- 워크스페이스 공유·공개 Ask 스레드, 실시간 presence, 다중 탭 OT.
- `dropped` 클라이언트 로컬 상태의 영속화.
- SSE `done`에 풀 페이로드를 실어 나르거나 이벤트 순서를 바꾸는 일.
- retrieval debug 원시 hit 스냅샷, 답변 in-place 편집, `service_role` 백필.
- 위키/소스 삭제 후 dangling `id`의 제목 스냅샷 — 클릭 실패는 현 인용 핸들러와 동일하게 두고 후속으로 미룬다.
- `missing_channels`를 서버 `meta`에 새로 실어 보내는 검색 파이프라인 변경.

## Decisions

### 1. 작성자 소유 서버 영속 (Gate 2 선택 a)

**채택:** `ask_threads` + `ask_messages`를 Postgres에 두고, 가시성은 작성자 ∩ 현재 워크스페이스 멤버십이다.

**대안과 기각 사유**
- *워크스페이스 공유 스레드 (b)*: 개인 질문을 팀 자산으로 바꾸는 제품 결정이 스펙에 없다. 교차 멤버 가시성 행렬만 늘고 이중 Citation 복원 이득은 없다.
- *브라우저만 영속 (c)*: 새로고침·다른 기기·시크릿에서 `text`+`resolved[]`를 보장하지 못해 Core Value가 무너진다.

### 2. citations 조립 후, `done` 직전, 같은 요청의 `user_client`로 인라인 저장

**채택:** `AskService`가 최종 `citations`를 만든 뒤 질문+답변 행을 한 트랜잭션으로 insert하고, 그 커밋이 성공한 뒤에만 `done`을 yield한다. `done`은 완료+저장 보장이다. 클라이언트는 빈 `done`을 저장의 소스 오브 트루스로 쓰지 않는다.

**대안과 기각 사유**
- *`done` 송신 후 클라이언트가 POST*: `done`이 `{}`라 필드 유실·부분 저장·`dropped` 분기가 늘어난다.
- *`done` 이후 워커 잡*: 사용자 경로에 `service_role`이 끼거나, `done`을 본 클라이언트가 아직 없는 행을 GET하는 레이스가 생긴다. 기존 Ask는 잡이 아니라 요청-응답 SSE다.

저장 실패 시 `done`을 보내지 않고 재시도 가능한 오류로 매핑한다. 스트림 도중 소켓이 끊겨도 서버는 조립이 끝났으면 저장을 마친다. 클라이언트의 `dropped` 카드는 로컬에만 남기고, 이후 GET은 서버 최종 상태(`resolved` / `error` / 없음)를 따른다.

### 3. 논리 턴은 한 행, 멱등 키는 `(thread_id, client_turn_id)`

**채택:** `ask_messages`는 사용자 질문과 어시스턴트 최종 상태를 한 행에 담는다. 컬럼은 최소한 `thread_id`, `client_turn_id`, `question`, `answer_text`, `citations jsonb`, `status`(`resolved` / `no-evidence` / `error`), `created_at`이다. UNIQUE `(thread_id, client_turn_id)`. 충돌 시 `on conflict do nothing` 후 기존 행을 성공으로 간주하고 `done`을 보낸다.

클라이언트가 매 제출마다 UUID `client_turn_id`를 만들고 `/ask` body에 넣는다. 명시적 재시도 버튼은 **새** `client_turn_id`를 쓴다.

**대안과 기각 사유**
- *user/assistant 두 행*: 멱등 키가 `(thread_id, client_turn_id, role)`로 늘고, 한쪽만 커밋된 부분 턴을 복원 경로가 처리해야 한다. 스펙의 “한 논리 턴”과 어긋난다.
- *`on conflict do update`*: 같은 키로 재전송된 완료가 이미 저장된 인용을 덮어쓸 수 있다. 재생성은 새 키로 충분하다.

`citations jsonb`는 라이브 `citations` 이벤트와 같은 최소 형태다: `{ "text": string, "resolved": [{ "alias", "kind": "wiki"|"source", "id" }] }`. `no-evidence`/`error`는 `resolved`가 빈 배열이고 카드 복원에 `status`를 쓴다.

### 4. `/ask`의 `thread_id`는 선택, 없으면 첫 영속 시 스레드를 만든다

**채택:** `AskRequest`에 `thread_id: uuid | none`, `client_turn_id: uuid`를 추가한다(`extra=forbid` 유지). `thread_id`가 없으면 persist 트랜잭션 안에서 `ask_threads`를 만들고 제목을 첫 질문에서 자른다. 있으면 작성자 소유 행이어야 하고, 아니면 RLS 0행 → API 403.

스레드 CRUD는 별도 라우트다.

- `GET /workspaces/{workspace_id}/ask/threads` — 본인 것만, `updated_at` desc
- `GET /workspaces/{workspace_id}/ask/threads/{thread_id}` — 스레드 + 메시지
- `PATCH .../ask/threads/{thread_id}` — 비어 있지 않은 `title`
- `DELETE .../ask/threads/{thread_id}` — 메시지 cascade

명시적 `POST /threads`는 필수 전제가 아니다. 빈 화면의 `[새 대화]`는 로컬 상태를 비우고, 첫 제출이 스레드를 만든다.

**대안과 기각 사유**
- *항상 먼저 POST /threads*: 빈 스레드 행이 쌓이고, 제출 실패 시 제목 없는 잔행이 목록에 남는다.
- *thread_id 필수*: 홈 `AskHero`의 `/ask?q=` 진입이 스레드 생성 API를 먼저 호출해야 해서 기존 진입이 깨진다.

딥링크는 `/w/{workspaceId}/ask?thread={id}`로 둔다. 삭제됐거나 403이면 대화 영역에 notice 카드 + 새 대화.

### 5. RLS는 0017을 미러하되 SELECT에도 멤버십을 건다

**채택:** 마이그레이션 `0018_ask_history.sql`.

- `ask_threads(id, workspace_id, user_id, title, created_at, updated_at)`
- `ask_messages(..., thread_id references ask_threads on delete cascade)`
- 복합 FK로 `workspace_id`가 스레드와 어긋나지 않게 한다 (0017 `user_wiki_bookmarks_tenant_fkey`와 같은 이유).
- `enable row level security`. `anon` 정책 없음.
- SELECT/UPDATE/DELETE `using (user_id = (select auth.uid()) and public.is_workspace_member(workspace_id))`
- INSERT `with check`도 동일.
- API 쓰기가 0행이면 HTTP 403 (`errors.py`의 기존 매핑).

**대안:** 0017처럼 SELECT는 `user_id`만 → 기각. 스펙 시나리오 “멤버십을 잃은 작성자”가 작성자 일치만으로 읽히는 것을 금지한다.

### 6. 복원은 `splitTextWithAnchors(text, resolved)`만 탄다

**채택:** GET한 완료 턴은 `status`를 즉시 최종값으로 두고, `resolved`가 있는 답변만 `splitTextWithAnchors(stored.text, stored.resolved)`로 나눈다. 라이브 스트림의 해소 맵 없는 호출은 복원 경로에서 금지한다. 마커 클릭은 기존 `handleMarkerClick`을 재사용한다.

스트리밍 중 다른 스레드로 옮기면 같은 탭의 `fetch`는 abort하지 않는다. 같은 세션에서 돌아오면 (1) 아직 살아있는 스트림이 있으면 그걸 보여주고 (2) 없으면 GET으로 서버 최종 상태를 읽는다. 서버가 아직 커밋 전이면 짧은 간격으로 같은 GET을 재시도한다. SSE를 이어 붙이거나 재구독하지 않는다.

**대안:** SSE resume / Last-Event-Id → 기각. 현재 파서는 연결 단위이고, `done={}`라 resume 커서가 없다.

### 7. 스레드 레일은 대화열 오버레이 서랍이다

**채택:** `ThreadDrawer`를 `.conversation` 위에 얹는다. 1599px 이하는 기존 `.sidebar.mobile-open` + `.mobile-scrim` 패턴(스크림 포함). 1600px 이상은 CSS만으로 280px push(스크림 없음). `AskLayout` 그리드 계산·리사이즈는 건드리지 않는다. 트리거는 `.conversation-head`의 `icon-btn`. 목록은 `role="listbox"` / `role="option"`. 삭제 확인은 Radix Dialog + `.button.danger`. 상대 시간은 `formatRelativeTime`.

기존 Ask 카피 토큰(`EMPTY_HEADING` 등)은 한 글자도 바꾸지 않는다.

**대안과 기각 사유**
- *`.ask-layout` 또는 `.app`에 열 추가*: 786px 예산과 컴팩트 데스크톱 접힘 순서를 다시 짜야 하고, 섹션 15/16이 같은 이유로 열 추가를 버렸다.
- *`WorkspaceSidebar` LNB에 대화 목록*: 전역 내비와 Ask 세션 상태가 섞이고, 위키/소스 라우트에도 빈 열이 생긴다.

### 8. 사용자 경로는 `user_client`만 쓴다

스레드 CRUD와 persist insert 모두 요청자 JWT `UserDb`다. 워커 잡을 만들지 않으므로 `service_role`+`workspace_id` 필터 경로가 생기지 않게 한다.

## Risks / Trade-offs

- **[Risk] persist가 LLM 완료와 같은 요청에 묶여 저장 지연이 `done`을 늦춘다** → 한 행 insert라 지연은 작다. 실패 시 `done`을 보내지 않아 클라이언트가 “저장 안 된 완료”를 신뢰하지 않는다.
- **[Risk] 복원 시 `resolved` 없이 text만 저장하면 placeholder가 고착된다** → jsonb 계약을 `text`+`resolved[]`로 고정하고, 복원 테스트에서 해소된 마커를 단언한다.
- **[Risk] 위키/소스 삭제 후 dangling `id`** → 현 클릭 핸들러와 동일하게 실패를 삼킨다. 제목 스냅샷은 Non-Goal.
- **[Risk] 멤버십을 잃은 뒤에도 0017식 SELECT가 통과하면 스펙 위반** → SELECT `using`에 `is_workspace_member`를 반드시 넣는다.
- **[Risk] 마이그레이션 번호를 0017 앞에 끼우면 클라우드 순서가 어긋난다** → `0018_ask_history.sql`만 추가한다.
- **[Risk] 서랍이 인용 인스펙터와 z-index로 싸운다** → 스레드 서랍을 주 내비(30)보다 낮게(20) 두고, 폭을 280px로 제한해 답변 카드 전체를 가리지 않는다.

## Migration Plan

1. `supabase/migrations/0018_ask_history.sql` — 테이블, unique, RLS, grant. SQL 전부 소문자.
2. API 스키마·라우트·AskService persist를 같은 슬라이스에서 켠다. 빈 목록은 정상이다(백필 없음).
3. 대시보드가 `thread_id`/`client_turn_id`를 보내고 서랍·복원을 붙인다.
4. 롤백: 라우트와 UI를 제거하고 마이그레이션을 되돌리면 된다. 기존 Ask SSE는 `thread_id` 없이 동작하던 계약과 호환되게, 필드가 없는 구 클라이언트는 422가 아니라 서버가 스레드를 새로 만들도록 `thread_id`만 optional로 둔다. `client_turn_id`는 신규 필수 — 구 클라이언트가 없으면 허용한다(대시보드가 유일 클라이언트).

## Open Questions

없음. 소유권·영속 시점·멱등 키·서랍 배치는 Gate 2에서 확정했다. 제목 truncate 길이·GET 재시도 간격은 구현 기본값으로 두고 스펙을 바꾸지 않는다.
