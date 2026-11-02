# Tenant Isolation Review — `ai-context-budget` (Round 1)

- **Change**: `ai-context-budget` (`openspec/changes/archive/2026-11-03-ai-context-budget`)
- **검토 범위**: `git diff main...HEAD` (`supabase/migrations/0028_control_budget_tab.sql`, `apps/api/src/api/routers/control.py`, `apps/api/src/api/services/ask.py`, `apps/worker/src/worker/handlers/compile.py`, `apps/worker/src/worker/handlers/conflict.py`, `packages/core/src/nexuswiki_core/context_budget.py` 외 관련 파일)
- **판정 등급**: `pass`
- **치명 항목 유무**: 없음

---

## 검사 항목별 판정 (A-1 ~ E-15)

### A. 테넌트 경계 및 권한 (RLS · 역할 · FK)

- **A-1 (사용자 경로의 `service_role`)**: **통과**
  - `apps/api/src/api/routers/control.py`의 신규 엔드포인트 `GET /workspaces/{workspace_id}/control/budget`는 `_user_db(request, credentials).rpc("control_budget_snapshot", ...)`를 통해 요청자 JWT(`UserDb`)만 사용한다.
  - `apps/api/src/api/services/ask.py`의 `_fetch_evidence_content`도 요청자 JWT가 실린 `user_db`와 `workspace_id=eq.{workspace_id}` 조건만 사용한다. 사용자 요청 경로 어디에도 `service_role` 클라이언트가 도입되지 않았다.
- **A-2 (신규 테이블 RLS 동시 활성화)**: **해당 없음**
  - `supabase/migrations/0028_control_budget_tab.sql`은 신규 테이블을 생성하지 않고 집계 RPC 함수 `public.control_budget_snapshot(uuid, timestamptz)`만 정의한다.
  - 참고로 해당 함수는 `security definer` + `set search_path = ''`로 선언되었으며, 진입 즉시 `public.has_workspace_role(p_workspace_id, 'viewer')`를 검사하고 모든 내부 CTE(`monthly`, `ask_turns`, `compile_savings`, `call_events`)와 서브쿼리에 `workspace_id = p_workspace_id` 필터 및 역할 분기(`v_can_view_ws` vs `t.user_id = auth.uid()`), `date_trunc('day', p_since, 'UTC')` 일 단위 내림을 적용해 교차 테넌트 유출과 시각 차분 역추적을 모두 차단한다.
- **A-3 (`anon`에 새로 부여된 GRANT나 정책)**: **통과**
  - `0028_control_budget_tab.sql:264-267`에서 `revoke all on function public.control_budget_snapshot(uuid, timestamptz) from public, anon, service_role;`로 기본 실행 권한을 회수한 뒤 `authenticated`에만 `grant execute`를 부여했다.
- **A-4 (`service_role` 코드(워커)의 명시적 `workspace_id` 필터)**: **통과**
  - `apps/worker/src/worker/handlers/compile.py`의 `_decide_route()`에서 호출하는 `db.latest_compile_fingerprint(workspace_id=workspace_id, raw_source_id=raw_source_id)` 및 `list_wiki_pages_for_source(workspace_id=workspace_id, raw_source_id=raw_source_id)` 모두 `workspace_id` 필터를 명시적으로 전달한다.
  - `apps/worker/src/worker/handlers/conflict.py`의 `run_conflict_check()`에서도 `list_wiki_pages_for_source`, `find_similar_wiki_pages`, `wiki_pages` 단건 조회(`"workspace_id": f"eq.{workspace_id}"`), `set_wiki_page_disputed` 모두 `workspace_id` 필터를 유지한다.
- **A-5 (새 자식 테이블의 복합 FK `(id, workspace_id)`)**: **해당 없음**
  - 신규 자식 테이블이 없다.

### B. 오류 매핑 (0행 · 42501 → 403)

- **B-6 (0행 → 403 매핑)**: **통과**
  - `apps/api/src/api/routers/control.py:500-501`에서 `control_budget_snapshot` RPC 결과가 빈 행(`if not rows:`)일 때 즉시 `raise WorkspaceForbidden(table="workspace_members", affected=0)`로 HTTP 403을 반환한다.
- **B-7 (SQLSTATE `42501` → 403 매핑)**: **통과**
  - `0028_control_budget_tab.sql:50-53, 62-65`에서 비멤버이거나 대상 워크스페이스가 없을 때 모두 동일하게 `using errcode = '42501'` 예외를 발생시켜 리소스 존재 여부를 노출하지 않으며, API 계층에서 SQLSTATE `42501`이 HTTP 403(`{"detail": "forbidden"}`)으로 매핑됨을 `apps/api/tests/test_tenant_isolation_full_path.py:615-646` 및 `apps/api/tests/test_control_router.py`에서 검증했다.

### C. 큐 · 워커 정합성

- **C-8 (핸들러 멱등성 및 upsert 키)**: **통과**
  - `compile.py`는 `(workspace_id, slug)` 업서트 키를 그대로 유지한다. 또한 `SKIP_UNCHANGED` 단락 판정 시 `previous == fingerprint`뿐 아니라 `has_existing_pages`(`list_wiki_pages_for_source` 결과 존재 여부)를 함께 확인하여, 기존 위키 페이지가 없는 상태에서 재실행 시 컴파일이 조용히 건너뛰어지는 결함을 방지했다.
  - `conflict.py`는 입력 본문 토큰 절단(`truncate_text_to_tokens`)과 `max_tokens` 상한만 추가하고 기존 `set_wiki_page_disputed` 멱등 처리 구조를 그대로 유지한다.
- **C-9 (`jobs` 직접 UPDATE 금지)**: **통과**
  - `compile.py:172-180`의 `SKIP_UNCHANGED` 단락 경로에서도 `jobs` 테이블을 직접 UPDATE하지 않고 `await db.complete_job_and_chain(job_id, next_type="link_sync", next_payload=...)` 큐 조작 함수를 사용한다.

### D. 검색 · 토크나이저 · 프롬프트 · 인용 정합성

- **D-10 (벡터 검색 `set local hnsw.iterative_scan = strict_order`)**: **해당 없음**
  - 이번 변경에서 벡터 검색 SQL 및 RPC는 수정되지 않았다.
- **D-11 (색인·질의 시점 토크나이저 일치 및 `tsv_tokenizer_version`)**: **해당 없음**
  - 토크나이저 로직 및 `tsv_tokenizer_version` 기록 방식에 변경이 없다. (`ask.py`에서 벡터 전용 위키 히트의 `slug`·`title` 메타데이터를 보강해 `decide_ask_route`에 넘기며, 동일한 `normalize()` 함수를 사용한다.)
- **D-12 (`search_tsv` 생성 컬럼 변경 금지)**: **해당 없음**
  - `search_tsv` 컬럼 정의 변경이 없다.
- **D-13 (프롬프트 템플릿 `str.format` 금지)**: **통과**
  - `ask.py`, `compile.py`, `conflict.py` 어디에도 `str.format`을 사용하지 않으며, 기존 단일 스캔 치환(`_render`, `render_template`)을 유지한다.
- **D-14 (LLM 컨텍스트 인용 앵커 포함)**: **통과**
  - `packages/core/src/nexuswiki_core/context_budget.py`의 `allocate_ask_context_budget()`은 검색 결과에 `wiki`와 `source`가 모두 존재할 때 최상위 `wiki` 1개와 최상위 `source` 1개를 필수 쿼터로 먼저 배정하여, 상위 거대 문서가 예산을 초과하더라도 이중 인용 근거(`dual_evidence_preserved = True`)가 조용히 탈락하지 않도록 보장한다.
  - `apps/api/src/api/services/ask.py:792-805`에서 예산 할당 후 선택된 `included_evidence`에 대해서만 `build_issuance_map(included_evidence)`와 `_context_blocks(included_evidence, issuance, budget.content_by_id)`를 호출하므로, 프롬프트의 `[[wiki:wN]]` / `[[src:sN]] (raw_source_id chunk_index)` 인용 앵커와 발급 맵이 1:1로 일치한다.

### E. 마이그레이션 순서

- **E-15 (새 마이그레이션 번호가 기존 최대 번호보다 큰가)**: **통과**
  - 기존 최대 번호 `0027_ask_cost_accounting.sql` 다음 번호인 `0028_control_budget_tab.sql`을 사용했다.

---

## 최종 판정

- **등급**: `pass`
- **결론**: 모든 테넌트 격리 규칙, 역할별 집계 가시성 분리(`viewer` vs `editor` 이상), `42501`/0행 → 403 매핑, 워커 `workspace_id` 필터, 핸들러 멱등성 및 이중 인용 앵커 보존 불변식이 위반 없이 준수되었다.
