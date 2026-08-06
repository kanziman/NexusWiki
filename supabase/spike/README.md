# DB 트랜스포트 스파이크 하네스

`DOM-01`의 판정 근거를 만드는 재현용 하네스다. 결과는 `docs/ops/db-transport-spike.md`에,
결정 자체는 `checklists.json > decisions.db_transport`에 남는다.

관련 태스크: `P2-BE-01`
설계 근거: `02-CONTEXT.md > D-01`, `D-02`, `D-03`, `D-05`

## 이 디렉터리가 마이그레이션이 아닌 이유

여기 있는 SQL은 **로컬 전용**이며 클라우드에 적재하지 않는다. 50,000행 × 1536차 벡터는
무료 티어 용량을 위협하고, 판정이 끝나면 필요 없다. `supabase db reset`이 전부 지운다.
번호(`0001`, `0002`)는 이 디렉터리 안에서의 실행 순서일 뿐 `supabase/migrations/`의
번호 계열과 무관하다.

## 사전 조건

- 로컬 Supabase 스택이 떠 있다 (`supabase status`가 DB `127.0.0.1:54422`를 보고).
- 로컬 `psql`이 없으므로 모든 SQL은 `docker exec -i supabase_db_NexusWiki psql`로 넣는다.
- 스파이크 사용자 비밀번호는 파일이 아니라 환경변수로 넘긴다. 커밋된 파일에 자격증명이
  들어가면 영구히 남는다 (`T-02-01`).

```bash
export SPIKE_USER_PASSWORD='<로컬 전용 임의 문자열, 8자 이상>'
```

## 실행 순서

### 1. 코퍼스 적재

`docker exec`에 `-e SPIKE_USER_PASSWORD`를 붙여야 psql이 `\getenv`로 값을 읽을 수 있다.
붙이지 않으면 스크립트가 즉시 실패한다(조용히 빈 비밀번호로 넘어가지 않는다).

얇은 관통용 (총 2,200행 / 타깃 200행):

```bash
cat supabase/spike/0001_transport_corpus.sql \
  | docker exec -i -e SPIKE_USER_PASSWORD supabase_db_NexusWiki \
      psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
           -v total_rows=2200 -v target_rows=200
```

본 판정용 (총 50,000행 / 타깃 750행 = 1.5%):

```bash
cat supabase/spike/0001_transport_corpus.sql \
  | docker exec -i -e SPIKE_USER_PASSWORD supabase_db_NexusWiki \
      psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
           -v total_rows=50000 -v target_rows=750 -v noise_workspaces=5
```

스크립트는 끝에서 총 행 수 · 타깃 행 수 · HNSW 인덱스 존재를 스스로 검사하고 어긋나면
예외로 죽는다. 적재가 조용히 절반만 된 코퍼스 위에서 판정하는 것이 이 스파이크의
가장 비싼 실패 방식이다.

### 2. 검색 함수 생성

```bash
cat supabase/spike/0002_search_fn_rpc.sql \
  | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
```

### 3. 러너 실행

```bash
uv run --with httpx python scripts/spike_db_transport.py --transport rpc --k 20 --repeat 3
```

asyncpg 경로는 공급망 게이트에서 승인된 **정확한 버전**으로만 실행한다. 버전을 고정하지
않으면 매 실행이 다른 것을 설치해 3회 반복의 재현성 전제가 깨진다.

```bash
uv run --with httpx --with 'asyncpg==0.31.0' \
  python scripts/spike_db_transport.py --transport asyncpg --k 20 --repeat 3
```

`--forced-hnsw`는 진단 전용 플래그다. 정렬 경로를 막아 플래너가 HNSW를 고르게 만든 뒤
GUC가 실제 HNSW 스캔까지 도달하는지를 따로 관측한다. 기본 계획에서 `has_hnsw_index_scan`이
거짓일 때 그 원인이 "GUC 미전달"인지 "플래너의 비용 판단"인지를 가르는 데 쓴다.

```bash
uv run --with httpx --with 'asyncpg==0.31.0' \
  python scripts/spike_db_transport.py --transport rpc --k 20 --repeat 3 --forced-hnsw
```

접속 정보(`API_URL` · `PUBLISHABLE_KEY` · `DB_URL`)는 `supabase status -o json`에서 읽는다.
CLI 인자(`--supabase-url`, `--anon-key`, `--database-url`)나 환경변수가 있으면 그쪽이 우선한다.

## 판정 기준 (`02-CONTEXT.md > D-03`)

셋 다 참일 때만 RPC를 채택한다. 하나라도 거짓이면 asyncpg다.

| 조건 | 러너 출력 키 |
| --- | --- |
| GUC 3종이 전부 적용되었다 | `gucs_applied` (`iterative_scan` · `ef_search` · `max_scan_tuples`) |
| EXPLAIN 계획이 HNSW 인덱스를 실제로 스캔했다 | `hnsw_index_scan` (`has_hnsw_index_scan`) |
| `k=20` 요청에 정확히 20행이 돌아왔다 | `k_rows_returned` (`returned_rows`) |

반복 회차 간 판정이 하나라도 어긋나면 러너가 non-zero로 종료한다.

## 정리

```bash
supabase db reset
```

## 알려진 사실

- **`authenticated`/`service_role`에 테이블 DML 권한이 없다.** 이 스택의
  `pg_default_acl`은 `public` 스키마 테이블에 `Dxtm`만 주며 `arwd`를 주지 않는다.
  RLS 정책은 이미 가진 권한을 좁힐 뿐이므로 `0004`의 정책들은 현재 상태에서 무력하다.
  `0002_search_fn_rpc.sql`이 스파이크 진행을 위한 최소 `grant select`만 국소적으로
  넣어 두었고, 영구 조치는 `0007`(02-06-PLAN)의 몫이다.
- **얇은 관통(200행)에서는 `has_hnsw_index_scan`이 거짓이 정상이다.** 타깃이 작으면
  플래너가 `source_chunks_workspace_idx` btree 스캔 + 정렬을 고른다. 코퍼스가 작으면
  판정이 변별력을 잃는다는 `D-02`의 경고가 그대로 관측되는 지점이다.
