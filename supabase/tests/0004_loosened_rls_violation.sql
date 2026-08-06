-- =============================================================================
-- NexusWiki 0004 위반 픽스처: workspaces 쓰기 정책을 교차 테넌트가 뚫리도록 느슨하게
--
-- 관련 태스크: P2-BE-01 (SEC-06 fail-first 증명)
-- 설계 근거:  02-CONTEXT.md > D-12, D-14
--
-- 목적
--   `apps/api/tests/test_workspaces_isolation.py`가 통과한다는 사실은 두 가지를 뜻할
--   수 있습니다 — 정책이 실제로 동작한다는 뜻이거나, 테스트가 아무것도 검사하지 않는
--   공허한 형태라는 뜻이거나. 둘을 구분하는 유일한 방법은 정책을 깨고 그 테스트가
--   실제로 red가 되는 것을 관측하는 것입니다. 보안 척추 전체가 이 테스트 하나로
--   증명되므로, 공허한 통과가 이 페이즈에서 가장 비싼 실패입니다.
--
-- ⚠️ 이 스크립트는 **검증 전용**이며 절대로 `supabase/migrations/`에 두지 않습니다.
--    마이그레이션 디렉터리에 있으면 `supabase db reset`과 `supabase db push`가 이것을
--    순서대로 적용해 격리가 로컬에서도 클라우드에서도 영구히 풀립니다. 그 상태는
--    아무 오류도 내지 않으므로 조용합니다 — 실행 결과가 정상과 구별되지 않습니다.
--
-- 실행 방법 (섹션을 따로 적용합니다)
--   느슨하게:  sed -n '/-- 1\./,/-- 2\./p' supabase/tests/0004_loosened_rls_violation.sql \
--                | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
--   되돌리기:  sed -n '/-- 2\./,$p' supabase/tests/0004_loosened_rls_violation.sql \
--                | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
--
-- 관측 기록: docs/ops/tenant-isolation-proof.md
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. 느슨하게 — workspaces의 SELECT·UPDATE·DELETE에서 멤버십/소유자 조건을 걷어냅니다.
--
-- ⚠️ SELECT 정책을 함께 풀어야 하는 이유가 이 페이즈의 실측 결과입니다. Postgres에서
--    `update ... where id = $1`은 대상 행을 **먼저 읽어야** 찾으므로 SELECT 정책이
--    그 행을 가린 상태에서는 UPDATE 술어를 아무리 풀어도 0행이 돌아옵니다. 즉 교차
--    테넌트 쓰기를 막는 술어가 두 겹이며, 한 겹만 풀면 격리는 여전히 유지되어
--    fail-first가 red를 만들지 못합니다(그 상태를 실제로 관측했습니다 —
--    docs/ops/tenant-isolation-proof.md §결과).
--
-- `to authenticated`는 그대로 둡니다. 이것까지 풀면 인증 없는 요청도 통과해 "격리가
-- 깨졌다"가 아니라 "인증이 깨졌다"를 관측하게 되고, 무엇이 red를 만들었는지 구별할 수
-- 없게 됩니다. 바꾸는 것은 테넌트 술어뿐입니다.
-- -----------------------------------------------------------------------------
drop policy workspaces_select_member on public.workspaces;

create policy workspaces_select_member on public.workspaces
  for select to authenticated
  using (true);

drop policy workspaces_update_owner on public.workspaces;

create policy workspaces_update_owner on public.workspaces
  for update to authenticated
  using (true)
  with check (true);

drop policy workspaces_delete_owner on public.workspaces;

create policy workspaces_delete_owner on public.workspaces
  for delete to authenticated
  using (true);


-- -----------------------------------------------------------------------------
-- 2. 되돌리기 — 0004_rls_policies.sql:163-178의 정의를 그대로 복원합니다.
--
-- ⚠️ 복원 여부는 "이 섹션을 실행했다"가 아니라 pg_policies의 qual/with_check 문자열을
--    느슨하게 만들기 전과 대조해 확인합니다. 실행했다는 사실만으로는 복원을 증명하지
--    못합니다.
--
-- SELECT 정책의 `owner_id` 조건은 0004의 주석대로 워크스페이스 생성의 RETURNING을
-- 통과시키기 위한 것입니다 — 소유자를 멤버로 넣는 트리거가 AFTER라 INSERT 시점에는
-- 아직 멤버십 행이 없습니다. 빠뜨리면 워크스페이스 생성 자체가 실패합니다.
-- -----------------------------------------------------------------------------
drop policy workspaces_select_member on public.workspaces;

create policy workspaces_select_member on public.workspaces
  for select to authenticated
  using (public.is_workspace_member(id) or owner_id = (select auth.uid()));

drop policy workspaces_update_owner on public.workspaces;

create policy workspaces_update_owner on public.workspaces
  for update to authenticated
  using (public.has_workspace_role(id, 'owner'))
  with check (public.has_workspace_role(id, 'owner'));

drop policy workspaces_delete_owner on public.workspaces;

create policy workspaces_delete_owner on public.workspaces
  for delete to authenticated
  using (public.has_workspace_role(id, 'owner'));
