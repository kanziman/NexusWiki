## Context

`proposal.md`에서 정의한 Controlled AI Step 2(`ai-context-budget`)는 네 개의 레이어(`packages/core`, `apps/api`, `apps/worker`, `apps/dashboard` + `supabase/migrations`)에 걸친 변경이다.

현재 코드베이스의 기술적 제약은 다음과 같다:
- `packages/core`는 I/O 없는 순수 함수 패키지이므로 RRF 병합, 토큰 예산 할당, 라우팅 판정은 모두 `packages/core`에 두고, DB 조회와 OpenRouter 호출은 `apps/api`와 `apps/worker`에서 수행해야 한다.
- 사용자 요청 경로(`apps/api/src/api/routers/control.py`)에서는 `service_role` 키를 절대 사용할 수 없으며, 요청자 JWT를 전달받은 PostgREST RPC를 통해서만 집계 데이터를 읽어야 한다.
- `usage_events`, `ask_messages.control_report`, Control Room 응답, 공개 쇼케이스 증거 JSON에는 프롬프트·질문·답변·원문 텍스트나 사용자 식별자·내부 작업 에러 문자열이 포함되어서는 안 된다.
- 공개 쇼케이스 합성 증거 검증(`apps/worker/tests/test_controlled_ai_evidence.py`)은 `79b68fe` 커밋 worktree와 현재 `HEAD` 모두에서 실행되므로, 시나리오 드라이버는 `79b68fe` 시점에 존재하던 모듈 시그니처와 호환되어야 한다.

## Goals / Non-Goals

**Goals:**
- Ask 근거 블록 조립 시 총 토큰 상한(`ASK_MAX_CONTEXT_TOKENS`)을 강제하면서 위키 근거(`[[wiki:...]]`)와 원문 청크 근거(`[[src:...]]`)가 모두 검색된 경우 각 종류 최소 1개 블록의 인용 가능성을 보장한다.
- RRF 다중 채널 병합(`fuse_ranked_hits`) 및 Ask 근거 본문 조회(`_fetch_evidence_content`)에서 채널별 메타데이터(`slug`, `title`)가 유실되지 않도록 보장한다.
- 구조화 출력 호출(`compile`, `conflict_check`)에 `max_tokens` 출력 상한과 입력 길이 상한을 적용하고 `usage_events.metadata`에 기록한다.
- `compile` 핸들러에서 동일 `raw_source_id`의 직전 성공 `fingerprint`가 일치하고 해당 원문의 위키 페이지가 이미 존재할 때 `SKIP_UNCHANGED`로 LLM 호출을 실제로 건너뛰고 `link_sync`로 체이닝한다.
- Control Room의 `[예산]` 탭(`Step 2`)을 활성화하고 요청자 JWT 기반 집계 RPC(`public.control_budget_snapshot`) 및 API(`GET /workspaces/{workspace_id}/control/budget`)를 연결한다.
- `/showcase/controlled-ai`에 Step 2 전/후 합성 증거 시나리오 3종을 추가하고 `upcoming` 목록을 Step 3·Step 4로 갱신한다.

**Non-Goals:**
- 워크스페이스별 동적 월 예산 상한 편집 UI 또는 팀원별 쿼터 배분(월 상한은 기존 `MONTHLY_WORKSPACE_CREDIT_CAP_MICROS` 설정과 `usage_events` 원장 정산을 그대로 사용).
- Step 3(근거 품질·환각·인용 감사) 및 Step 4(프롬프트 인젝션·민감정보 리스크 방어) 기능 구현.
- `usage_events`를 실제 공급자 호출이 없던 `SKIP_UNCHANGED` 경로에 가짜 행으로 삽입하는 행위(호출 횟수·원장 왜곡 방지).

## Decisions

### D1. RRF 메타데이터 병합 및 Ask 컨텍스트 토큰 예산 할당기 (`packages/core` + `apps/api`)

- **결정**:
  1. `packages/core/src/nexuswiki_core/rrf.py`의 `fuse_ranked_hits`에서 동일 `(kind, id)` 히트가 여러 검색 채널에서 발견될 때 기존에는 첫 채널의 `metadata`만 남겼으나, `{**hit.metadata, **previous.metadata}` 형태로 병합해 선행 채널의 키 우선순위를 유지하면서 후행 채널(`wiki_lexical` 등)에만 존재하는 `slug`·`title`을 보존한다. 또한 `apps/api/src/api/services/ask.py`의 `_fetch_evidence_content`에서도 `wiki_pages` 조회 시 `id,slug,title,content`를 함께 읽어, 벡터 채널 단독 히트인 경우에도 `EvidenceHit.metadata`에 `slug`·`title`을 보강한 뒤 `decide_ask_route`와 컨텍스트 조립을 수행한다.
  2. `packages/core/src/nexuswiki_core/context_budget.py`(및 `packages/core` 공개 export)에 순수 함수 `allocate_ask_context_budget(hits, contents, *, max_context_tokens)`를 둔다.
     - 각 근거 블록의 헤더(`[i] [[wiki:slug]] (title)` 또는 `[i] [[src:id]] (title)`)와 본문 토큰 수를 `estimate_token_count`로 계산한다.
     - 검색 결과에 `wiki`와 `source`가 모두 존재하면, 1순위로 최상위 `wiki` 히트와 최상위 `source` 히트를 선택 후보에 먼저 배정하고(단일 블록이 남은 예산을 초과하면 본문을 토큰 예산에 맞게 절단하되 최소 1개 인용 블록은 유지), 이후 남은 RRF 순위 순서대로 잔여 토큰 예산 안에서 블록을 추가하거나 마지막 수용 블록의 본문을 절단한다.
     - 반환값 `AskContextBudgetResult`는 조립된 블록 문자열 목록, 채택된 `EvidenceHit` 목록, 그리고 `control_report["budget"]`에 기록할 숫자·불리언 요약(`max_context_tokens`, `estimated_context_tokens`, `candidate_blocks`, `included_blocks`, `dropped_blocks`, `truncated_blocks`, `wiki_blocks`, `source_blocks`, `dual_evidence_preserved`, `truncated`)을 담는다.
- **대안 검토**:
  - 단순 문자열 슬라이싱으로 전체 프롬프트를 자르는 방식: 뒤에 배치된 `[[src:...]]` 블록이나 `[[wiki:...]]` 헤더가 통째로 잘려 이중 근거 인용 요건(`grounded-answering`)이 깨진다.

### D2. 구조화 출력 `max_tokens` 및 입력 절단 (`apps/worker`)

- **결정**:
  - `WorkerSettings`에 `COMPILE_MAX_OUTPUT_TOKENS: int = 4096`, `COMPILE_MAX_EXISTING_SLUGS: int = 200`, `CONFLICT_MAX_INPUT_TOKENS: int = 4000`, `CONFLICT_MAX_OUTPUT_TOKENS: int = 512`를 추가한다.
  - `worker.llm.complete_structured`와 `worker.llm_gateway.LlmGateway.complete_structured`에 선택 인자 `max_tokens: int | None = None`을 추가하고, 값이 주어지면 OpenRouter 요청 본문(`_chat_body`)에 `"max_tokens": max_tokens`를 포함하며 `usage_events.metadata["max_tokens"]`에 기록한다.
  - `run_compile`은 `existing_slugs[:settings.COMPILE_MAX_EXISTING_SLUGS]`로 슬러그 목록을 제한하고 `max_tokens=settings.COMPILE_MAX_OUTPUT_TOKENS`를 전달한다.
  - `run_conflict_check`는 기존 페이지 본문과 신규 페이지 본문이 각각 `CONFLICT_MAX_INPUT_TOKENS // 2`를 넘으면 토큰 예산에 맞게 절단하고 `extra_metadata={"truncated_input": truncated_input, "max_input_tokens": settings.CONFLICT_MAX_INPUT_TOKENS}` 및 `max_tokens=settings.CONFLICT_MAX_OUTPUT_TOKENS`를 전달한다.
- **대안 검토**:
  - OpenRouter 기본 출력 한도에 의존하는 방식: 모델 기본 상한이 수만 토큰인 경우 비정상 JSON 반복 생성 시 단일 잡이 과도한 출력 비용을 소모한다.

### D3. Compile `SKIP_UNCHANGED` 단락 실행 및 원장 정합성 (`packages/core` + `apps/worker`)

- **결정**:
  - `decide_compile_route`에 `has_existing_pages: bool = True` 인자를 추가한다(기본값 `True`로 하위 호환 유지). `previous_fingerprint == fingerprint`이더라도 `has_existing_pages=False`이면 `SKIP_UNCHANGED`로 단락하지 않고 `TRUNCATED` 또는 `STANDARD`를 반환한다.
  - `run_compile`에서 `previous_fingerprint == fingerprint`일 때 `await db.list_wiki_pages_for_source(workspace_id=workspace_id, raw_source_id=raw_source_id)`로 기존 위키 페이지 존재 여부를 확인한다(테스트 더블에 해당 메서드가 없는 경우 안전하게 빈 목록으로 처리하지 않고, 기존 페이지가 확인된 경우에만 단락하거나 메서드가 정의된 경우 그 결과를 따른다).
  - `route.decision == "SKIP_UNCHANGED"`이면 `LlmGateway.complete_structured`를 호출하지 않고, 즉시 `await db.complete_job_and_chain(job_id, next_type="link_sync", next_payload={"target_id": raw_source_id, "raw_source_id": raw_source_id, "compile_route": "SKIP_UNCHANGED"})`를 호출해 종료한다.
  - 실제 공급자 호출이 없었으므로 `usage_events`에는 행을 추가하지 않는다(`recorded_usage_rows = 0`). 대신 체이닝된 `link_sync` 잡의 `payload ->> 'compile_route' = 'SKIP_UNCHANGED'`를 통해 Control Room 예산 집계 RPC가 LLM 생략 횟수(`compile_skipped_count`)를 정확히 집계한다. 또한 직전 성공 컴파일의 `usage_events` 행이 그대로 최신으로 유지되므로 이후 재실행에서도 `latest_compile_fingerprint`가 동일 지문을 계속 반환한다.
- **대안 검토**:
  - `usage_events`에 `cost_micros = 0` 행을 추가하는 방식: `usage-guardrails`의 "공급자 호출당 1행 기록" 불변식을 위반하고 Control Room `[추적]` 탭의 공급자 호출 수(`call_count`)를 부풀린다.

### D4. Control Room `[예산]` 탭 집계 RPC 및 API/UI (`supabase/migrations` + `apps/api` + `apps/dashboard`)

- **결정**:
  - 새 마이그레이션 `supabase/migrations/0028_control_budget_tab.sql`에 `public.control_budget_snapshot(p_workspace_id uuid, p_since timestamptz)`(`language plpgsql stable security definer set search_path = ''`)를 추가한다.
  - 권한 검증:
    - `public`, `anon` 실행 권한을 박탈하고 `authenticated`에만 부여한다.
    - 함수 첫머리에서 `if not public.has_workspace_role(p_workspace_id, 'viewer') then raise exception 'insufficient_privilege' using errcode = '42501'; end if;`를 실행해 비소속 사용자의 호출을 즉시 HTTP 403으로 귀결시킨다.
    - `v_can_view_workspace := public.has_workspace_role(p_workspace_id, 'editor');`로 역할을 판별한다.
  - 반환 구조(`jsonb`):
    - 공통(`viewer` 이상):
      - `can_view_workspace`: `boolean`
      - `window_days`: 호출자가 지정한 기간(기본 30일)과 별개로 월간 크레딧 원장(`this_month`) 및 기간별 호출 집계를 함께 반환.
      - `monthly_usage`: 당월(`date_trunc('month', now() at time zone 'utc')`) 기준 `reported_cost_micros`, `pending_cost_micros`, `estimated_cost_micros`, `budget_cost_micros`, `call_count`, `total_tokens`, `unresolved_count`, `manual_review_count`, `over_reserve_count`.
      - `saving_counts`:
        - `editor`/`owner`: 워크스페이스 전체 당월(또는 조회 기간) `ask_no_evidence_count`(`control_report ->> 'route' = 'NO_EVIDENCE'`), `ask_context_truncated_count`(`coalesce((control_report -> 'budget' ->> 'truncated')::boolean, false) = true`), `compile_truncated_count`(`usage_events`에서 `call_path = 'compile'` 및 `metadata ->> 'route' = 'TRUNCATED'`), `compile_skipped_count`(`jobs`에서 `type = 'link_sync'` 및 `payload ->> 'compile_route' = 'SKIP_UNCHANGED'`).
        - `viewer`: 본인(`ask_threads.created_by = auth.uid()`)의 `ask_no_evidence_count` 및 `ask_context_truncated_count`만 포함하고, 워크스페이스 전체 컴파일 카운트는 `0`으로 마스킹한다.
      - `by_call_path`:
        - `editor`/`owner`: `usage_events`를 `call_path`별로 그룹화한 배열(`call_path`, `call_count`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `reported_cost_micros`, `pending_cost_micros`, `budget_cost_micros`).
        - `viewer`: 빈 배열 `[]`.
  - API 엔드포인트 `GET /workspaces/{workspace_id}/control/budget`:
    - `apps/api/src/api/routers/control.py`에서 요청자 JWT로 `rpc/control_budget_snapshot`을 호출하고, 서버 설정(`MONTHLY_WORKSPACE_CREDIT_CAP_MICROS`, `ASK_MAX_CONTEXT_TOKENS`, `COMPILE_MAX_INPUT_TOKENS`, `COMPILE_MAX_OUTPUT_TOKENS`, `CONFLICT_MAX_INPUT_TOKENS`, `CONFLICT_MAX_OUTPUT_TOKENS`)을 결합해 `cap_micros`, `remaining_micros`, `utilization_pct`, `policy`를 포함한 응답을 반환한다.
  - 대시보드 `apps/dashboard/components/ControlRoom.tsx`:
    - `"budget"` 탭을 활성 탭으로 전환하고 `"quality"`(`Step 3`)와 `"risk"`(`Step 4`)만 `FUTURE_TABS`에 남긴다.
    - `[예산]` 탭 선택 시 `/workspaces/${workspaceId}/control/budget`를 호출하여 (1) 당월 예산 상한·공급자 보고 비용·미확정 점유·잔여 한도·미정산/수동검토 건수 카드, (2) 활성 토큰 예산 정책 카드, (3) 사전 차단·절단으로 절감된 실행 카운트 카드, (4) `editor`/`owner` 전용 호출 경로별 토큰·비용 표(`viewer`에게는 개인 범위 안내 배너 표시)를 렌더링한다.

### D5. 공개 쇼케이스 Step 2 합성 증거 (`apps/worker/tests/test_controlled_ai_evidence.py` + `apps/dashboard`)

- **결정**:
  - `test_controlled_ai_evidence.py`에 Step 2 시나리오 3종을 추가하고, 기존 `79b68fe` worktree 실행기와 호환되도록 `79b68fe`에도 존재하는 진입점(`run_compile`, `run_conflict_check`, `AskService.stream_answer`)만 호출한다:
    1. `compile_unchanged_skip`: 동일 `raw_source`(동일 `content_hash`)에 대해 이미 컴파일된 위키 페이지와 직전 지문이 존재할 때 재컴파일 실행. `before`(`79b68fe`)는 `llm_calls=1`, `recorded_usage_rows=1`인 반면 `after`는 `SKIP_UNCHANGED`로 단락되어 `llm_calls=0`, `recorded_usage_rows=0`, `chained_next_type="link_sync"`가 된다.
    2. `ask_context_budget_quota`: 긴 본문을 가진 상위 위키 히트 여러 개와 후순위 원문 청크 히트가 함께 검색된 상태에서 Ask 호출. `before`(`79b68fe`)는 모든 히트 본문을 무제한 결합해 컨텍스트 토큰이 예산을 초과하는 반면, `after`는 `ASK_MAX_CONTEXT_TOKENS` 이하로 컨텍스트를 제한하면서도 `[[wiki:...]]`와 `[[src:...]]` 인용 블록을 모두 보존하고 `control_report.budget.truncated=True`, `dual_evidence_preserved=True`를 기록한다.
    3. `structured_output_max_tokens`: 긴 위키 페이지 쌍에 대한 `run_conflict_check` 호출. `before`(`79b68fe`)는 OpenRouter 요청에 `max_tokens`를 전달하지 않고 원문 전체를 전송하는 반면, `after`는 입력을 `CONFLICT_MAX_INPUT_TOKENS` 예산 내로 절단하고 요청 본문과 `usage_events.metadata`에 `max_tokens=512`를 기록한다.
  - `apps/dashboard/content/controlled-ai/step1.json`에 위 3개 시나리오의 실측 `before`/`after` 결과를 반영하고 `upcoming` 배열은 Step 3·Step 4만 남긴다.

## Risks / Trade-offs

- **[Risk] `ApiSettings` 필드 추가 시 `packages/core/tests/test_settings.py`의 allowlist 테스트 실패** → `ApiSettings`에 비비밀 운영 한도 필드(`ASK_MAX_CONTEXT_TOKENS` 등)를 추가할 때 `packages/core/tests/test_settings.py`의 허용 필드 집합도 함께 갱신하여 비밀 키 유출 방지 테스트의 의도를 유지한다.
- **[Risk] `test_controlled_ai_evidence.py`의 커밋 해시 정합성 검증(`test_committed_code_cannot_ship_with_uncommitted_evidence`)** → 코드 변경을 커밋한 뒤 `step1.json`의 `after.commit`이 실제 코드 커밋을 가리키도록 갱신하여 증거 JSON과 커밋 상태가 어긋나지 않게 한다.
- **[Risk] 로컬 및 원격 Supabase 마이그레이션 드리프트** → `0028_control_budget_tab.sql` 작성 후 로컬 컨테이너에 즉시 적용하고 `supabase/tests/0028_control_budget_tab.sql`로 RLS·역할 분기 테스트를 통과시킨다.

## Migration Plan

1. `supabase/migrations/0028_control_budget_tab.sql`을 추가하여 `public.control_budget_snapshot` 함수를 생성하고 `authenticated` 실행 권한만 부여한다.
2. 기존 테이블 스키마 변경이나 파괴적 DDL이 없으므로 무중단 적용이 가능하며, 롤백 시 `drop function if exists public.control_budget_snapshot(uuid, timestamptz);`로 즉시 되돌릴 수 있다.
