## 03-01에서 발견 (범위 밖)

- **⚠️ 클라우드에서 `service_role`이 `public.search_chunks` EXECUTE를 갖는다.** 로컬은 `false`, 클라우드는 `true`. 원인은 클라우드의 `pg_default_acl`(schema `public`, objtype `f`, owner `postgres`)이 `anon,authenticated,service_role`에 EXECUTE를 주는데 로컬에는 그 항목이 없다는 것. `0008`의 `revoke all … from public, anon`이 `anon`만 걷어냈다. `0007`이 만든 상태를 `0008`이 재현한 것이며 `0008`은 이미 push되어 소급 수정 불가.

  **정정:** `0009`에 `revoke execute on function public.search_chunks(uuid, extensions.vector, int) from service_role;` 한 줄. 실측과 근거는 `docs/ops/migration-0008-record.md` § 한계와 되돌리기 2.

  **⚠️ 일반화된 함정 — `0009` 이후 모든 마이그레이션에 적용된다.** `0007` §8이 **테이블**에 대해 적어둔 "새 객체는 `pg_default_acl`에서 기본 권한을 물려받으므로 revoke/grant 쌍을 반드시 반복하라"가 **함수에도, 그리고 클라우드에서만 더 넓게** 걸린다. `revoke all … from public, anon`처럼 부분 열거하지 말고 `revoke all … from public, anon, authenticated, service_role` 후 필요한 롤에만 grant할 것. `dead_letter_job()`(D-03)이 이 규칙을 처음 적용받는다.

- **`03-CONTEXT.md > D-01(4)`의 전제가 사실이 아니다.** "시그니처에 `p_query extensions.vector(1536)`이 박혀 있어 `create or replace`로는 바뀌지 않는다"는 틀렸다 — Postgres는 함수 인자의 typmod를 저장하지 않으므로 실제 시그니처는 `(uuid, vector, int)`이고 오버로드는 생기지 않는다. `0008`은 그럼에도 D-01(4)의 형태를 지켜 drop 후 create를 했고 ACL을 복원했다. 후속 플랜이 "함수 인자 타입으로 차원을 강제할 수 있다"고 가정하지 말 것 — 강제하는 것은 컬럼 타입뿐이다.

- **`.claude/CLAUDE.md`의 Supabase CLI 버전 기록이 낡았다.** 문서는 2.33.2(업그레이드 유예)라고 적었으나 실제 설치본은 2.111.0이고 `0008` 적용도 그것으로 수행됐다. `config.toml`은 `[inbucket]` deprecated 경고를 낸다(적용에는 영향 없음). 문서 정정 또는 `[local_smtp]` 이관은 이 플랜의 범위 밖.
