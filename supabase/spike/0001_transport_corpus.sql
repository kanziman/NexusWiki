-- =============================================================================
-- NexusWiki 스파이크 0001: DB 트랜스포트 판정용 적대적 코퍼스
--
-- 관련 태스크: P2-BE-01 (소비자는 scripts/spike_db_transport.py)
-- 설계 근거:  02-CONTEXT.md > D-02 (합성 데이터 · 적대적 분포 · 고정 시드)
--             02-CONTEXT.md > D-01 (판정은 EXPLAIN 계획과 실제 반환 행 수로 한다)
--
-- ⚠️ 이 파일은 마이그레이션이 아니다. supabase/migrations/ 아래에 두지 않는 이유는
--    로컬 스파이크 전용이며 클라우드에 적재하면 안 되기 때문이다. `supabase db reset`이
--    이 코퍼스를 지운다.
--
-- 코퍼스 구조
--
--   spike_owner ──owns──> 타깃 워크스페이스 1개 ── raw_source 1 ── source_chunks :target_rows
--   spike_noise ──owns──> 노이즈 워크스페이스 N개 ─ raw_source 1씩 ─ 나머지 행 분산
--
-- 타깃 비율이 낮을수록(SPEC R6은 1.5%) HNSW 사후 필터링이 반드시 물리므로 RPC와
-- asyncpg가 변별된다. 노이즈를 *다른 사용자*가 소유하게 만든 이유는 실제 운영에서
-- 대부분의 행이 요청자가 멤버가 아닌 워크스페이스에 속하기 때문이며, 그래야 RLS와
-- 명시 필터가 함께 좁히는 프로덕션 경로를 그대로 재현한다.
--
-- 실행
--   export SPIKE_USER_PASSWORD='...'
--   cat supabase/spike/0001_transport_corpus.sql \
--     | docker exec -i -e SPIKE_USER_PASSWORD supabase_db_NexusWiki \
--         psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
--              -v total_rows=50000 -v target_rows=750 -v noise_workspaces=5
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 0. 파라미터
--
-- 행 수를 psql 변수로 받는 이유는 얇은 관통(2,200행)과 본 판정(50,000행)이 같은
-- 스크립트를 그대로 쓰게 하기 위해서다. 두 코퍼스가 다른 파일이면 얇은 경로에서
-- 통과한 것이 본 판정에서 통과한다는 보장이 사라진다.
-- -----------------------------------------------------------------------------
\if :{?total_rows}
\else
  \set total_rows 50000
\endif

\if :{?target_rows}
\else
  \set target_rows 750
\endif

\if :{?noise_workspaces}
\else
  \set noise_workspaces 1
\endif

\if :{?seed}
\else
  \set seed 0.4242
\endif

\if :{?spike_email}
\else
  \set spike_email 'spike-owner@nexuswiki.local'
\endif

\if :{?noise_email}
\else
  \set noise_email 'spike-noise@nexuswiki.local'
\endif

-- ⚠️ 비밀번호는 파일에 기본값을 두지 않는다. 커밋된 파일에 자격증명이 들어가면
--    영구히 남는다(T-02-01). psql 프로세스의 환경변수에서만 읽는다.
\if :{?spike_password}
\else
  \getenv spike_password SPIKE_USER_PASSWORD
\endif

\if :{?spike_password}
\else
  \set spike_password ''
\endif

-- ⚠️ psql은 달러 인용 블록 안에서 :변수를 치환하지 않는다. DO 블록이 파라미터를
--    보려면 세션 GUC를 경유해야 하며, 치환된 것처럼 쓰면 구문 오류로 즉시 드러난다.
select
  set_config('spike.total_rows',       :'total_rows',       false),
  set_config('spike.target_rows',      :'target_rows',      false),
  set_config('spike.noise_workspaces', :'noise_workspaces', false),
  set_config('spike.seed',             :'seed',             false),
  set_config('spike.password_length',  length(:'spike_password')::text, false);

do $guard$
begin
  if current_setting('spike.password_length')::int < 8 then
    raise exception
      'SPIKE_USER_PASSWORD 환경변수(8자 이상)가 필요하다. docker exec 에 -e SPIKE_USER_PASSWORD 를 붙였는지 확인할 것.';
  end if;
end
$guard$;

-- ⚠️ 병렬 워커가 붙으면 random() 호출 순서가 실행마다 달라져 setseed 재현성이 깨진다.
--    3회 반복이 같은 코퍼스를 본다는 전제가 여기서 무너지면 판정 일치는 우연이 된다.
set max_parallel_workers_per_gather = 0;

select setseed(:seed);


-- -----------------------------------------------------------------------------
-- 1. 정리 (재실행 가능성)
--
-- workspaces.owner_id 는 on delete restrict 이므로 워크스페이스를 먼저 지운다.
-- source_chunks / raw_sources / workspace_members 는 cascade 로 함께 사라진다.
-- -----------------------------------------------------------------------------
delete from public.workspaces
 where id::text like 'b0000000-0000-4000-8000-%';

delete from auth.users
 where id in (
   'a0000000-0000-4000-8000-000000000001'::uuid,
   'a0000000-0000-4000-8000-000000000002'::uuid
 );


-- -----------------------------------------------------------------------------
-- 2. 스파이크 사용자 2명
--
-- GoTrue password grant 가 그대로 붙을 수 있는 형태로 직접 심는다. 러너가 요청자
-- JWT를 받아야 하고(D-01), 그 JWT 없이는 SECURITY INVOKER 경로를 관측할 수 없다.
--
-- ⚠️ confirmation_token 등 토큰 컬럼을 NULL로 두면 GoTrue가
--    "converting NULL to string is unsupported" 로 500을 던진다. 빈 문자열이어야 한다.
--    또한 auth.identities 행이 없으면 email provider 로그인이 성립하지 않는다.
-- -----------------------------------------------------------------------------
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
  confirmation_token, recovery_token, email_change_token_new, email_change,
  email_change_token_current, phone_change, phone_change_token, reauthentication_token
)
select
  '00000000-0000-0000-0000-000000000000'::uuid,
  u.id,
  'authenticated',
  'authenticated',
  u.email,
  extensions.crypt(:'spike_password', extensions.gen_salt('bf')),
  now(),
  '{"provider":"email","providers":["email"]}'::jsonb,
  '{}'::jsonb,
  now(),
  now(),
  '', '', '', '', '', '', '', ''
from (values
  ('a0000000-0000-4000-8000-000000000001'::uuid, :'spike_email'),
  ('a0000000-0000-4000-8000-000000000002'::uuid, :'noise_email')
) as u(id, email);

insert into auth.identities (
  provider_id, user_id, identity_data, provider, created_at, updated_at, last_sign_in_at
)
select
  u.id::text,
  u.id,
  jsonb_build_object(
    'sub', u.id::text,
    'email', u.email,
    'email_verified', true,
    'phone_verified', false
  ),
  'email',
  now(), now(), now()
from auth.users u
where u.id in (
  'a0000000-0000-4000-8000-000000000001'::uuid,
  'a0000000-0000-4000-8000-000000000002'::uuid
);


-- -----------------------------------------------------------------------------
-- 3. 워크스페이스와 원문 소스
--
-- workspaces_add_owner_member 트리거가 소유자를 멤버로 자동 등록하므로
-- workspace_members 를 직접 만들지 않는다(0001의 계약을 그대로 소비).
-- -----------------------------------------------------------------------------
insert into public.workspaces (id, name, slug, kind, owner_id)
values (
  'b0000000-0000-4000-8000-000000000001'::uuid,
  'spike-target',
  'spike-target',
  'team',
  'a0000000-0000-4000-8000-000000000001'::uuid
);

insert into public.workspaces (id, name, slug, kind, owner_id)
select
  ('b0000000-0000-4000-8000-' || lpad((100 + j)::text, 12, '0'))::uuid,
  'spike-noise-' || j,
  'spike-noise-' || j,
  'team',
  'a0000000-0000-4000-8000-000000000002'::uuid
from generate_series(1, :noise_workspaces) as j;

-- 복합 FK (raw_sources.id, workspace_id) 규약을 지키기 위해 워크스페이스마다
-- 부모 행을 정확히 하나씩 만든다 (0002의 source_chunks_raw_source_fkey).
insert into public.raw_sources (
  id, workspace_id, title, source_type, content, content_hash
)
select
  ('c0000000-0000-4000-8000-' || substr(w.id::text, 25))::uuid,
  w.id,
  'spike corpus ' || w.name,
  'text',
  'spike synthetic corpus for ' || w.name,
  encode(extensions.digest(w.id::text, 'sha256'), 'hex')
from public.workspaces w
where w.id::text like 'b0000000-0000-4000-8000-%';


-- -----------------------------------------------------------------------------
-- 4. source_chunks 적재
--
-- 워크스페이스별 행 수 배분: 타깃은 :target_rows, 나머지 (:total_rows - :target_rows)
-- 를 노이즈 워크스페이스에 균등 분배하고 잔여분은 마지막 노이즈가 흡수한다.
--
-- ⚠️ 임베딩 생성 서브쿼리는 반드시 바깥 행을 참조해야 한다. 참조가 없으면 플래너가
--    InitPlan 으로 끌어올려 한 번만 평가하고, 5만 행이 전부 동일한 벡터를 갖게 된다.
--    그 코퍼스에서는 HNSW가 무엇을 하든 판정이 통과해 스파이크가 아무것도 변별하지
--    못한다. `0 * e.i` 가 그 참조를 강제한다.
-- -----------------------------------------------------------------------------
with target_plan as (
  select
    'b0000000-0000-4000-8000-000000000001'::uuid as workspace_id,
    (:target_rows)::int                          as n_rows,
    0                                            as ordinal
),
noise_plan as (
  select
    ('b0000000-0000-4000-8000-' || lpad((100 + j)::text, 12, '0'))::uuid as workspace_id,
    (((:total_rows) - (:target_rows)) / (:noise_workspaces))::int
      + case
          when j = :noise_workspaces
          then (((:total_rows) - (:target_rows)) % (:noise_workspaces))::int
          else 0
        end                                                             as n_rows,
    j                                                                    as ordinal
  from generate_series(1, :noise_workspaces) as j
),
plan as (
  select * from target_plan
  union all
  select * from noise_plan
),
expanded as (
  select
    p.workspace_id,
    ('c0000000-0000-4000-8000-' || substr(p.workspace_id::text, 25))::uuid as raw_source_id,
    gs.i
  from plan p,
       lateral generate_series(0, p.n_rows - 1) as gs(i)
)
insert into public.source_chunks (
  raw_source_id, workspace_id, chunk_index, content, char_start, char_end, embedding
)
select
  e.raw_source_id,
  e.workspace_id,
  e.i,
  'spike chunk ' || e.workspace_id::text || ' #' || e.i,
  e.i * 100,
  e.i * 100 + 80,
  v.vec
from expanded e,
     lateral (
       select array_agg(s.x)::extensions.vector as vec
       from (
         select random() + 0 * e.i as x
         from generate_series(1, 1536)
       ) s
     ) v;


-- -----------------------------------------------------------------------------
-- 5. 적재 후 점검
--
-- ⚠️ 대량 insert 뒤 통계가 낡으면 플래너가 HNSW 대신 seq scan 을 고른다. 그러면
--    EXPLAIN 판정이 트랜스포트가 아니라 통계 상태를 측정하게 된다.
-- -----------------------------------------------------------------------------
analyze public.source_chunks;

do $check$
declare
  v_total    bigint;
  v_target   bigint;
  v_index    boolean;
  v_expected bigint := current_setting('spike.total_rows')::bigint;
  v_wanted   bigint := current_setting('spike.target_rows')::bigint;
begin
  select count(*) into v_total from public.source_chunks;

  select count(*) into v_target
  from public.source_chunks
  where workspace_id = 'b0000000-0000-4000-8000-000000000001'::uuid;

  select exists (
    select 1 from pg_class where relname = 'source_chunks_embedding_idx'
  ) into v_index;

  if v_total <> v_expected then
    raise exception '코퍼스 총 행 수 불일치: 기대 % 실제 %', v_expected, v_total;
  end if;

  if v_target <> v_wanted then
    raise exception '타깃 워크스페이스 행 수 불일치: 기대 % 실제 %', v_wanted, v_target;
  end if;

  if not v_index then
    raise exception 'source_chunks_embedding_idx (HNSW) 가 없다 — 0002 마이그레이션 적용 여부를 확인할 것.';
  end if;

  raise notice
    '스파이크 코퍼스 준비 완료: 총 % 행, 타깃 % 행 (% %%), 노이즈 워크스페이스 %개, seed %',
    v_total,
    v_target,
    round(v_target::numeric * 100 / v_total, 4),
    current_setting('spike.noise_workspaces'),
    current_setting('spike.seed');
end
$check$;
