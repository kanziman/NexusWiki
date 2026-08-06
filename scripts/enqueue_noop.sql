-- =============================================================================
-- noop 잡 1건 인큐 — 큐 계약 검증 전용
--
-- 관련 태스크: P2-JOB-01
-- 설계 근거:  02-CONTEXT.md > D-17 (Phase 2가 실측할 수 있는 것은 noop 잡의
--             큐 오버헤드뿐이다), 02-SPEC.md R10
--
-- ⚠️ 이 파일을 supabase/migrations/ 에 두면 안 됩니다. 그 디렉터리의 파일은
--    `supabase db reset`과 `supabase db push`가 번호 순서대로 **모든 환경에**
--    적용하므로, 검증용 잡 한 건이 클라우드 프로덕션 큐에 그대로 인큐되어
--    배포된 워커가 그것을 집어갑니다. 마이그레이션 번호는 스키마의 순서이지
--    데이터 주입의 순서가 아닙니다.
--
-- ⚠️ 생산자 API(P2-ING-01)는 Phase 3의 일입니다. Phase 2에는 잡을 만드는
--    코드 경로가 없으므로 인큐는 이 스크립트가 유일한 수단입니다.
--
-- ⚠️ payload의 target_id는 선택 사항이 아닙니다. 0007의 jobs_dedup_idx가
--    (workspace_id, type, payload ->> 'target_id') 위의 부분 유니크 인덱스라,
--    이 키가 없으면 NULL끼리 서로 다른 값으로 취급되어 중복 인큐가 조용히
--    통과합니다. 여기서는 실행마다 새 uuid를 넣어 반복 실행이 23505로 막히지
--    않게 합니다.
--
-- 사용법 (로컬. 이 저장소에는 로컬 psql이 없습니다):
--
--   docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres \
--     -v workspace_id="'00000000-0000-0000-0000-000000000000'" \
--     -f - < scripts/enqueue_noop.sql
--
-- 정리:
--   delete from public.jobs where type = 'noop' and workspace_id = '<uuid>';
-- =============================================================================

insert into public.jobs (workspace_id, type, payload, max_attempts)
values (
  :workspace_id::uuid,
  'noop',
  jsonb_build_object('target_id', gen_random_uuid()::text),
  1
)
returning id, workspace_id, type, status, attempts, max_attempts, run_after;
