# 마이그레이션 0008 적용 기록

`docs/ops/migration-0007-record.md`를 이어 쓴 문서다. `0008`은 그 기록이 "`0007`의 내용을 바꾸려면
`0008` 보정 마이그레이션이 필요하다"고 남긴 다음 번호이며, 실제로 `0002`와 `0007`이 1536차로 고정해 둔
임베딩 차원을 1024로 옮기는 보정이다.

## 적용 일시

- 로컬 `db reset`: 2026-08-08 (UTC 2026-08-08T01:5xZ). 마이그레이션 저술 직후 한 번, 주석 정정 후 push 직전에 한 번, 총 두 번.
- 클라우드 `db push`: 2026-08-08 (UTC 2026-08-08T02:0xZ)
- 대상 커밋: `c0eed04` (마이그레이션 저술) · `9361332` (계약 러너 + CI 잡). 적용 시점 HEAD `9361332`
- 대상 프로젝트: Supabase `dajhhwbkfdaqnuenulsb` / 리전 `ap-southeast-1` / Postgres 17.6 (플랫폼 버전 17.6.1.155)
- 도구: Supabase CLI 2.111.0. ⚠️ `.claude/CLAUDE.md`가 적어둔 2.33.2가 아니다 — 어느 시점에 올라갔고
  이 적용은 2.111.0으로 수행됐다. `config.toml`은 `[inbucket]` 섹션 deprecated 경고를 내지만 적용에는 영향이 없었다.

## 무엇을 바꿨나

| 객체 | 이전 | 이후 |
|---|---|---|
| `public.source_chunks.embedding` | `vector(1536)` | `vector(1024)` |
| `public.wiki_embeddings.embedding` | `vector(1536)` | `vector(1024)` |
| `source_chunks_embedding_idx` | hnsw / vector_cosine_ops | drop 후 같은 이름·같은 opclass로 재생성 |
| `wiki_embeddings_embedding_idx` | hnsw / vector_cosine_ops | drop 후 같은 이름·같은 opclass로 재생성 |
| `public.search_chunks` | 선언부 `p_query extensions.vector(1536)` | drop 후 선언부 `extensions.vector(1024)`로 재생성 + ACL 복원 |

전부 **기존 객체 변경**이다. `dead_letter_job()`과 `usage_events`는 새 객체이므로 `0009` 이후로 갔다
(`03-CONTEXT.md > D-01`).

## 로컬

### 방법

- `supabase db reset`을 두 번 돌렸다. 두 번째는 아래 §관측이 드러낸 사실을 반영해 `0008`의 주석을 고친
  뒤이며, 그 의미는 "빈 DB에서 `0001`부터 순서대로 다시 세워도 최종 파일 내용으로 `0008`이 적용되는가"다.
- 계약 러너 두 개를 reset된 스키마 위에서 실행했다 —
  `bash scripts/verify_search_contract.sh` (신규) · `bash scripts/verify_queue_functions.sh` (기존 회귀).
- 스키마·권한은 `pg_catalog`를 직접 조회해 확인했다 (`docker exec -i supabase_db_NexusWiki psql …`).

### 결과

- `supabase db reset`이 `0001` → … → `0008` 순서로 오류 없이 적용됐다. pass.
- `verify_search_contract.sh` 종료 코드 `0`, 출력 `search_contract: ok`. 단언 9종 전부 통과. 테스트가
  `rollback`으로 끝나므로 잔여 행 `0`. pass.
- `verify_queue_functions.sh` 종료 코드 `0`, 출력 `queue_functions: ok` — 기존 큐 계약 회귀 없음. pass.
- `bash scripts/ci_check_search_contract.sh` 종료 코드 `0` (토큰 9종). 대상 0개(빈 디렉터리)에서는 `2`,
  토큰 하나를 지운 사본에서는 `1` — 게이트가 red가 되는 것까지 확인했다. pass.
- `uv run pytest -rs` 147 passed. `uv run pre-commit run --all-files` 통과. pass.

### 로컬 관측값

| 확인 항목 | 실제 반환값 | 판정 |
|---|---|---|
| `source_chunks.embedding` | `vector(1024)` | pass |
| `wiki_embeddings.embedding` | `vector(1024)` | pass |
| `public.search_chunks` 개수 | `1` | pass |
| `pg_get_function_arguments` | `p_workspace_id uuid, p_query vector, p_k integer DEFAULT 20` | 아래 §한계 1 참조 |
| `prosecdef` | `false` | pass |
| `provolatile` | `s` | pass |
| `proconfig` | `search_path=public \| hnsw.iterative_scan=strict_order \| hnsw.ef_search=200 \| hnsw.max_scan_tuples=40000` | pass |
| `has_function_privilege('authenticated', …, 'EXECUTE')` | `true` | pass |
| `has_function_privilege('anon', …, 'EXECUTE')` | `false` | pass |
| `has_function_privilege('service_role', …, 'EXECUTE')` | `false` | pass |
| `source_chunks_embedding_idx` | `hnsw / vector_cosine_ops` | pass |
| `wiki_embeddings_embedding_idx` | `hnsw / vector_cosine_ops` | pass |
| 함수 `proacl` | `postgres=X/postgres \| authenticated=X/postgres` | pass |

## 클라우드

### 방법

- push **직전에** `supabase migration list --linked`로 원격 원장이 `0001`~`0007`이고 `0008`의 Remote 열이
  비어 있음을 확인했다.
- `supabase db push --linked`로 적용한 뒤 같은 명령으로 다시 대조하고, 원격 스키마를
  `supabase db query --linked -f …`로 직접 조회했다.
- ⚠️ `SUPABASE_ACCESS_TOKEN` 환경변수는 **설정되어 있지 않다**. CLI의 저장된 세션으로 비대화형 동작이
  가능했고, `0007` 적용 때와 같은 조건이다.

### 결과

`supabase db push --linked` 출력:
`{"upToDate":false,"dryRun":false,"migrations":["0008_embedding_dimension.sql"],"seeds":[],"roles":[],"message":"Finished supabase db push."}`.
적용된 마이그레이션은 `0008` 하나뿐이며 부분 적용의 흔적은 없다 — 파일 전체가 단일 트랜잭션이므로
부분 적용이 애초에 불가능하다.

#### `migration list` 로컬/원격 대조표

| Local | Remote | 일치 |
|---|---|---|
| 0001 | 0001 | ✅ |
| 0002 | 0002 | ✅ |
| 0003 | 0003 | ✅ |
| 0004 | 0004 | ✅ |
| 0005 | 0005 | ✅ |
| 0006 | 0006 | ✅ |
| 0007 | 0007 | ✅ |
| 0008 | 0008 | ✅ |

push 직전 표에서는 `0008` 행의 Remote 열만 비어 있었고, push 후 채워졌다.

#### 원격 스키마 직접 조회

| 확인 항목 | 실제 반환값 | 로컬과 일치 | 판정 |
|---|---|---|---|
| `source_chunks.embedding` | `vector(1024)` | ✅ | pass |
| `wiki_embeddings.embedding` | `vector(1024)` | ✅ | pass |
| `public.search_chunks` 개수 | `1` | ✅ | pass |
| `pg_get_function_arguments` | `p_workspace_id uuid, p_query vector, p_k integer DEFAULT 20` | ✅ | §한계 1 |
| `prosecdef` | `false` | ✅ | pass |
| `provolatile` | `s` | ✅ | pass |
| `proconfig` | `search_path=public \| hnsw.iterative_scan=strict_order \| hnsw.ef_search=200 \| hnsw.max_scan_tuples=40000` | ✅ | pass |
| `has_function_privilege('authenticated', …, 'EXECUTE')` | `true` | ✅ | pass |
| `has_function_privilege('anon', …, 'EXECUTE')` | `false` | ✅ | pass |
| `has_function_privilege('service_role', …, 'EXECUTE')` | **`true`** | ❌ | **fail — §한계 2** |
| `source_chunks_embedding_idx` | `hnsw / vector_cosine_ops` | ✅ | pass |
| `wiki_embeddings_embedding_idx` | `hnsw / vector_cosine_ops` | ✅ | pass |
| `source_chunks.embedding` 비-null 행 수 | `0` | ✅ | pass |
| `wiki_embeddings.embedding` 비-null 행 수 | `0` | ✅ | pass |
| 함수 `proacl` | `postgres=X/postgres \| authenticated=X/postgres \| service_role=X/postgres` | ❌ | §한계 2 |

## 한계와 되돌리기

### 1. 함수 선언부의 차원은 문서일 뿐 계약이 아니다

`0008`은 `p_query extensions.vector(1024)`라고 선언하지만 로컬·클라우드 양쪽에서
`pg_get_function_arguments`는 `p_query vector`를 돌려준다. Postgres는 함수 **인자**의 typmod를 저장하지
않고 길이 지정자를 강제하지도 않기 때문이다. `0007:386`이 revoke 대상을 `extensions.vector`로만 수식한
것도 같은 이유이며, 그것이 이 함수의 실제 시그니처다.

따라오는 두 가지:

- `03-CONTEXT.md > D-01(4)`이 적은 "시그니처에 1536이 박혀 있어 `create or replace`로는 바뀌지 않는다"는
  **사실이 아니다**. 오버로드는 애초에 생기지 않으며 `create or replace`만으로도 충분했다. `0008`이 그럼에도
  drop 후 create를 한 것은 D-01(4)이 지시한 형태를 지키면서 "이 파일 이후 `search_chunks`는 정확히 하나"를
  무조건 참으로 만들기 위해서다. 대가는 ACL이었고 섹션 7이 같은 트랜잭션에서 복원했다.
- 차원을 실제로 강제하는 것은 **컬럼 타입**뿐이고 그 강제는 호출 시점에만 나타난다. 그래서
  `supabase/tests/0008_search_contract.sql`의 계약 5는 카탈로그가 아니라 행동을 단언한다 — 1024차 질의는
  5행을 돌려주고 1536차 질의는 거부된다.

### 2. ⚠️ 클라우드에서 `service_role`이 `search_chunks` EXECUTE를 갖는다 — `0009`가 정정해야 한다

로컬은 `false`, 클라우드는 `true`다. 원인은 두 환경의 `pg_default_acl`이 다르다는 것이다.

| 환경 | `pg_default_acl` (schema `public`, objtype `f`) |
|---|---|
| 로컬 | `postgres=X/postgres` · 그리고 `supabase_admin` 소유의 `anon,authenticated,service_role` 항목 |
| 클라우드 | **`postgres` 소유 항목이 `anon,authenticated,service_role`에 EXECUTE를 준다** · `supabase_admin` 소유 항목도 동일 |

클라우드에서는 `postgres`가 만든 `public` 함수가 생성 즉시 세 롤에 EXECUTE를 물려받는다. `0008`의
`revoke all … from public, anon`은 그중 `anon`만 걷어냈고 `service_role`은 그대로 남았다. 로컬에는 그
기본 부여가 없어 revoke가 필요 없었고, 그래서 **로컬 계약 테스트는 green인데 클라우드는 위반 상태**다.

- 이것은 `0008`이 새로 만든 구멍이 아니다. `0007`이 같은 방식으로 `search_chunks`를 만들었으므로 그때부터
  존재했고 `0008`이 그대로 재현했다. `0007` 적용 기록은 함수 EXECUTE를 롤별로 조회하지 않아 놓쳤다.
- 심각도는 "열린 문"이 아니라 **다층 방어의 한 겹 상실**이다. `service_role` 키를 가진 주체는 이미
  BYPASSRLS로 테이블을 직접 읽을 수 있으므로 이 EXECUTE가 새 권한을 더해주지는 않는다. `0007:382-385`가
  막으려던 것은 애플리케이션이 사용자 검색을 `service_role` 경로로 흘려보내는 일이며, 그 위험이 지금 열려 있다.
  아직 `search_chunks`를 부르는 코드가 없으므로(검색 경로는 Phase 4) 실제 노출은 없다.
- **정정 위치는 `0009`다.** `0008`은 이미 원격에 올라갔으므로 소급 편집할 수 없다. 필요한 것은 한 줄이다:
  ```sql
  revoke execute on function public.search_chunks(uuid, extensions.vector, int) from service_role;
  ```
- ⚠️ **앞으로 `public`에 함수를 만드는 모든 마이그레이션에 같은 함정이 있다.** `0007` 섹션 8이 **테이블**에
  대해 적어둔 "새 객체는 `pg_default_acl`에서 기본 권한을 물려받으므로 revoke/grant 쌍을 반드시 반복하라"가
  **함수에도, 그리고 클라우드에서만 더 넓게** 적용된다. `revoke all … from public, anon`처럼 부분적으로
  열거하지 말고 `revoke all … from public, anon, authenticated, service_role` 후 필요한 롤에만 grant하는
  형태가 안전하다.

### 3. 이 적용은 one-way다

- 원격 원장에 `0008`이 올라간 이상 `0008`보다 낮은 번호의 마이그레이션은 다시는 추가할 수 없다.
  `0007` 기록의 같은 항목과 같은 제약이다.
- **되돌리려면 그 시점에 존재하는 모든 임베딩을 재생성해야 한다.** 지금은 두 컬럼의 비-null 행이 로컬·클라우드
  양쪽 `0`이라 되돌리기 비용도 `0`이었고, `alter column … type`이 `using` 캐스트를 한 번도 평가하지 않고 끝났다.
  **이 창은 Phase 3가 첫 임베딩을 만드는 순간 닫힌다.** 그 뒤의 차원 변경은 전량 재임베딩이며 종량 과금이라
  곧바로 돈이다. `03-CONTEXT.md > D-02`가 이 플랜을 Wave 1 단독으로 둔 이유가 이것이다.
- `0002_search_schema.sql:76`의 `text-embedding-3-small(1536차원).` 주석은 **거짓인 채로 영원히 남는다.**
  `0002`는 로컬·클라우드 양쪽에 적용되어 소급 수정이 불가하기 때문이다. 대체 근거는
  `checklists.json > decisions.embedding_model`이며 `0008` 헤더와 두 컬럼 `comment on column`이 그것을 가리킨다
  (`03-CONTEXT.md > D-06`).

### 4. CI 게이트는 소스 수준이고 psql 계약 러너는 로컬·수동이다 (D-08 이탈)

`03-CONTEXT.md > D-08`은 계약 검증을 "GitHub Actions PR 게이트에 추가"하라고 요구했고, 그 항목은
`### Claude's Discretion` 블록 안에 있다. 형태를 바꿨으므로 이유를 남긴다.

- 러너에 Supabase 스택을 세우지 않는다는 것은 `.github/workflows/ci.yml` 155-169행의 명시적 결정이다.
  세우면 이 잡이 검증하는 대상이 마이그레이션이 아니라 "CLI가 러너에서 뜨는가"가 된다.
- 그래서 역할을 둘로 나눴다. `scripts/ci_check_search_contract.sh`(CI 5번째 잡 `search-contract`)는
  `search_chunks`를 마지막으로 정의한 마이그레이션에서 계약 토큰 9종이 살아 있는지 **소스**로 본다.
  `scripts/verify_search_contract.sh`는 실제 스키마를 보지만 로컬·수동이다.
- ⚠️ **남는 사각:** CI는 "계약이 파일에 적혀 있는가"만 보고, psql 러너는 **로컬 DB만** 본다. 그래서
  §한계 2의 클라우드/로컬 ACL 차이 같은 것은 **어느 자동 게이트도 잡지 못한다**. 지금 그것을 잡는 유일한
  방법은 push 후 원격을 직접 조회하는 이 문서의 절차이며, 그 절차는 사람이 실행한다.

### 5. 아직 확인되지 않은 것

- 원격에서 실제 요청자 JWT로 `search_chunks`를 왕복시켜 본 적은 없다. 확인한 것은 스키마 동일성과 권한뿐이며,
  실제 왕복은 검색 경로가 서는 Phase 4에서 처음 검증된다. `0007` 기록의 같은 항목이 그대로 이월된다.
- HNSW 인덱스가 **운영 규모에서** 선택되는지는 확인되지 않았다. 계약 9의 `EXPLAIN` 단언은
  `enable_seqscan`/`enable_sort`를 끈 상태에서 "인덱스가 이 컬럼·이 연산자에 쓰일 수 있는가"만 묻는다 —
  30행 픽스처에서는 `workspace_id` btree + Sort가 언제나 더 싸기 때문이다. 실제 계획 판정은 Phase 4(RTV-04)다.
