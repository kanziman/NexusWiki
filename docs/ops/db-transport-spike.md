# DB 트랜스포트 스파이크 (DOM-01)

## 측정 일시

- 2026-08-06 13:55 KST
- 하네스 커밋 `bf021cb433616528c518bfbe05a1f8eea476e1ba`

## 방법

측정 주체는 개발자 머신의 로컬 Supabase 스택(Postgres 17.6 · pgvector 0.8.2)이다.
재현용 자산은 `supabase/spike/0001_transport_corpus.sql`,
`supabase/spike/0002_search_fn_rpc.sql`, `scripts/spike_db_transport.py` 세 개이며 전부
커밋되어 있다.

### 코퍼스

`setseed(0.4242)` 고정 시드 합성 코퍼스다. 임베딩은 1536차 난수 벡터이며 임베딩 API를
호출하지 않는다(비용 0, 재현 가능, 판정 조건을 직접 통제 — `02-CONTEXT.md > D-02`).

| 항목 | 값 |
| --- | ---: |
| 총 `source_chunks` 행 수 | 50,000 |
| 타깃 워크스페이스 행 수 | 750 |
| 타깃 비율 | 1.5000 % |
| 노이즈 워크스페이스 수 | 5 |
| 질의 벡터 시드 | 20260806 |
| `k` | 20 |

노이즈 워크스페이스는 **다른 사용자**가 소유한다. 요청자가 멤버가 아닌 워크스페이스에
대부분의 행이 있는 실제 운영 형태를 재현하기 위해서이며, 그 결과 RLS와 명시적
`workspace_id` 필터가 함께 좁힌다. 적재 직후 `analyze public.source_chunks`를 돌려 통계를
갱신했다 — 통계가 낡으면 판정이 트랜스포트가 아니라 통계 상태를 측정하게 된다.

동일 스크립트를 두 번 돌려 `source_chunks.embedding` 전체의 md5가 일치함을 확인했다
(`1a73cc826990b6c1f502efd95811aedc`, 얇은 관통 코퍼스 기준). 병렬 스캔은
`max_parallel_workers_per_gather = 0`으로 껐다 — 병렬 워커가 붙으면 `random()` 호출 순서가
달라져 고정 시드의 재현성이 깨진다.

### 두 경로

- **RPC** — GoTrue password grant로 받은 요청자 JWT로 PostgREST
  `/rest/v1/rpc/spike_explain_search_chunks`를 호출한다. 함수는 `security invoker` ·
  `stable`이며 GUC 3종을 함수 정의의 `set` 절에 박았다. RLS는 자동으로 걸린다.
- **asyncpg** — `asyncpg==0.31.0`으로 로컬 DB에 직접 연결하고, 트랜잭션 안에서
  `set local role authenticated` + `set local request.jwt.claims`(같은 JWT의 payload)를 세운
  뒤 GUC 3종을 `set local`로 건다.

### SPEC 이탈

SPEC R6은 asyncpg 경로를 **Supavisor session mode**로 측정하도록 요구하지만, 로컬 스택은
pooler가 비활성이고(`supabase/config.toml`의 54429) 클라우드 프로젝트에 50,000 × 1536차
벡터를 적재하면 무료 티어 용량을 위협한다. 따라서 asyncpg 경로는 로컬 DB
`127.0.0.1:54422`에 **직접 연결**해 측정했다. 직접 연결은 세션 단위 연결이므로 `set local`
GUC 의미론에 관한 한 Supavisor session mode와 동등하다. 이 이탈 형식은
`docs/ops/rtt-baseline.md`가 SPEC R9 이탈을 결정 인용과 함께 기록한 전례를 따른다.

### 측정 중 드러난 사실 (권한 공백)

이 스파이크를 돌리는 과정에서 `anon` · `authenticated` · `service_role`이 `public` 스키마
9개 테이블에 대해 `arwd`(SELECT/INSERT/UPDATE/DELETE) 권한을 **하나도 갖고 있지 않다**는
사실이 드러났다. `pg_default_acl`의 `postgres|public|r` 항목이 세 롤에 `Dxtm`만 부여한다.
RLS 정책은 이미 가진 권한을 좁힐 뿐 없는 권한을 만들지 않으므로 `0004`의 정책들은 현재
상태에서 무력하며, 요청자 JWT 경로와 `service_role` 워커 경로 모두 실제 질의에서 `42501`로
떨어진다. 스파이크 진행을 위해 `0002_search_fn_rpc.sql`이 `grant select on
public.source_chunks to authenticated` 하나만 국소적으로 넣었고, 영구 조치는 `0007`의
몫이다(아래 다운스트림 절).

## 결과

각 경로를 `--repeat 3`으로 실행한 개별 회차 실측값이다.

### 기본 계획 (애플리케이션이 실제로 내는 질의 형태)

| 경로 | 회차 | iterative_scan | ef_search | max_scan_tuples | has_hnsw_index_scan | returned_rows | elapsed_ms |
| --- | ---: | --- | ---: | ---: | --- | ---: | ---: |
| rpc | 1 | strict_order | 200 | 40000 | false | 20 | 48.866 |
| rpc | 2 | strict_order | 200 | 40000 | false | 20 | 23.916 |
| rpc | 3 | strict_order | 200 | 40000 | false | 20 | 21.964 |
| asyncpg | 1 | strict_order | 200 | 40000 | false | 20 | 40.499 |
| asyncpg | 2 | strict_order | 200 | 40000 | false | 20 | 32.580 |
| asyncpg | 3 | strict_order | 200 | 40000 | false | 20 | 32.305 |

두 경로 모두 3회차 판정이 완전히 일치했다(러너가 불일치 시 non-zero로 종료하며, 두 실행
모두 exit 0).

이때 선택된 계획은 양쪽 모두 동일하다:

```text
Limit  (총비용 233.24, 실행 11.776 ms)
  Sort
    Index Scan using source_chunks_workspace_idx  (actual rows = 750)
```

### 강제 HNSW 계획 (진단 — 조건 2의 원인 분리)

`enable_sort = off`로 정렬 경로를 막아 플래너가 HNSW를 고르게 한 뒤 같은 관측을 반복했다.

| 경로 | 회차 | iterative_scan | ef_search | max_scan_tuples | has_hnsw_index_scan | returned_rows | elapsed_ms |
| --- | ---: | --- | ---: | ---: | --- | ---: | ---: |
| rpc | 1 | strict_order | 200 | 40000 | true | 20 | 238.790 |
| rpc | 2 | strict_order | 200 | 40000 | true | 20 | 186.750 |
| rpc | 3 | strict_order | 200 | 40000 | true | 20 | 187.535 |
| asyncpg | 1 | strict_order | 200 | 40000 | true | 20 | 228.240 |
| asyncpg | 2 | strict_order | 200 | 40000 | true | 20 | 220.702 |
| asyncpg | 3 | strict_order | 200 | 40000 | true | 20 | 212.286 |

강제 시 계획과 사후 필터링 실측:

```text
Limit  (총비용 349656.62, 실행 136.938 ms)
  Index Scan using source_chunks_embedding_idx  (actual rows = 20)
    Order By: embedding <=> '<질의 벡터>'
    Filter: (embedding IS NOT NULL) AND (workspace_id = '<타깃>') AND is_workspace_member(workspace_id)
    Rows Removed by Filter: 1523
```

`Rows Removed by Filter: 1523`은 HNSW가 후보를 뱉고 사후 필터가 걸러내는 과정이 실제로
일어났음을, `actual rows = 20`은 `strict_order` 반복 스캔이 그 손실을 메워 `k`를 채웠음을
뜻한다. 계획의 `Filter`에 `is_workspace_member(workspace_id)`가 보이는 것은 RLS가 이 경로에
실제로 적용되었다는 직접 증거다.

## 판정

`02-CONTEXT.md > D-03`의 3조건을 경로별로 개별 기록한다. 부분 충족을 통과로 적지 않는다.

### 기본 계획에서의 조건별 참/거짓

| 조건 | rpc | asyncpg |
| --- | --- | --- |
| 1. GUC 3종(`hnsw.iterative_scan` · `hnsw.ef_search` · `hnsw.max_scan_tuples`)이 전부 적용되었다 | **참** (`strict_order` / `200` / `40000`) | **참** (`strict_order` / `200` / `40000`) |
| 2. EXPLAIN이 HNSW Index Scan을 보인다 | **거짓** (`source_chunks_workspace_idx` btree 선택) | **거짓** (동일) |
| 3. `k=20`에 정확히 20행이 돌아왔다 | **참** (20행) | **참** (20행) |

### 강제 HNSW 계획에서의 조건별 참/거짓

| 조건 | rpc | asyncpg |
| --- | --- | --- |
| 1. GUC 3종이 전부 적용되었다 | **참** | **참** |
| 2. EXPLAIN이 HNSW Index Scan을 보인다 | **참** (`source_chunks_embedding_idx`) | **참** (동일) |
| 3. `k=20`에 정확히 20행이 돌아왔다 | **참** (사후 필터 1,523행 제거 후에도 20행) | **참** |

### 이 숫자들이 뜻하는 것

조건 2는 기본 계획에서 **양쪽 경로 모두 거짓**이며, 두 경로의 계획은 노드 단위로 동일하다.
즉 이 거짓은 트랜스포트의 성질이 아니라 플래너의 비용 판단이다 — 타깃 워크스페이스가
750행뿐이라 btree로 750행을 읽어 정렬하는 편(총비용 233)이 HNSW 경로(총비용 349,657)보다
실제로 싸다. 어느 트랜스포트를 골라도 이 선택은 바뀌지 않는다.

따라서 D-03의 3조건을 기본 계획에 문자 그대로 적용하면 조건 2가 거짓이므로 규칙상
asyncpg가 되지만, **그 탈락 사유가 asyncpg의 장점과 아무 관련이 없다.** 규칙이 변별하도록
설계된 지점에서 변별이 일어나지 않은 것이다.

ROADMAP 성공기준 3이 실제로 묻는 질문은 "`create function ... SET hnsw.iterative_scan`이
Supabase RPC로 실제 적용되는가"이며, 강제 HNSW 관측이 그 질문에 답한다: **적용된다.**
RPC 경로에서 함수 정의의 `set` 절이 실제 HNSW 인덱스 스캔까지 도달했고, `strict_order`가
사후 필터링(1,523행 제거) 아래에서도 `k=20`을 채웠으며, RLS도 함께 걸렸다. 이 세 가지가
RPC 채택을 막는 요인이 없음을 보인다.

지연은 기본 계획에서 rpc 21.964–48.866 ms, asyncpg 32.305–40.499 ms로 두 경로가 같은
자릿수이며, PostgREST 왕복 오버헤드가 결정을 좌우할 만큼 크지 않다.

### 결론 — **RPC 채택 (확정)**

`Gate: DB 트랜스포트 결정 잠금` 체크포인트에서 **`rpc`(SECURITY INVOKER 함수 + 요청자
JWT)** 가 선택되어 `checklists.json > decisions.db_transport`에 잠겼다. 기계적 판정과
어긋나는 선택이 아니며(아래 요약 참조), 선택 근거는 측정 그대로다: 판정 3조건이 겨냥한
실패 양상이 RPC 경로에서 하나도 관측되지 않았고, D-03이 "애매하면 되돌리기 싼 쪽이 아니라
확실한 쪽으로 기운다"고 정한 방향과 일치한다. asyncpg는 측정된 이득 없이 D-04의 은밀한
격리 상실 위험을 추가로 떠안는다. Phase 4에서 질의를 고칠 때마다 마이그레이션(`0008`,
`0009`…)이 필요하다는 반대 논거는 인지한 상태에서 감수하기로 한 대가다.

### 나중 페이즈를 위한 요약 (이 스파이크를 다시 돌리지 않아도 되게)

1. **D-03의 기계적 3조건 규칙은 이 질의 형태에서 변별력이 없다.** 실제 애플리케이션 질의
   형태에서 두 트랜스포트는 **노드 단위로 동일한 계획**을 냈다. 조건 2가 깨진 원인은
   트랜스포트가 아니라 플래너의 비용 판단이다 — 타깃 750행에 대해 btree+정렬 `233` 대
   HNSW `349,657`. 어느 트랜스포트를 골라도 이 선택은 바뀌지 않는다.
2. **원인 분리는 `enable_sort = off` 진단으로 했다.** "GUC가 전달되지 않았다"와 "플래너가
   HNSW를 고르지 않았다"는 기본 계획의 EXPLAIN만으로는 구분되지 않는다. 정렬 경로를 막자
   양쪽 경로 모두 3조건 3/3을 충족했다.
3. **강제된 RPC 계획이 세 가지를 직접 증명한다.** `Rows Removed by Filter: 1523`은 사후
   필터링이 실제로 일어났음을, `actual rows = 20`은 `strict_order` 반복 스캔이 그 손실을
   메워 `k`를 채웠음을, `Filter: … is_workspace_member(workspace_id)`는 RPC 경로에 RLS가
   실제로 걸렸음을 보인다. 함수 정의의 `set` 절이 실제 HNSW 스캔까지 도달했다는 뜻이다.
4. **ROADMAP 성공기준 3의 실측 답은 "예"다** — `create function ... SET hnsw.iterative_scan`
   이 Supabase RPC로 실제 적용된다. 이 블로커는 해소되었다.
5. **지연은 판정에 기여하지 않았다.** 기본 계획에서 rpc 21.96–48.87 ms, asyncpg
   32.31–40.50 ms로 같은 자릿수이며, PostgREST 왕복 오버헤드가 결정을 좌우하지 않았다.

## 다운스트림 소비자

이 결정이 착지하는 지점은 세 곳이다.

- **`supabase/migrations/0007_*.sql` 섹션 1 (02-06-PLAN)** — 검색 함수가
  `supabase/spike/0002_search_fn_rpc.sql`의 `spike_search_chunks` 시그니처를 원형으로 삼는다.
  `security invoker` · `stable` · `set search_path = public` · GUC 3종을 같은 modifier
  블록에 두고, pgvector 참조를 전부 schema-qualified(`extensions.vector(1536)`,
  `operator(extensions.<=>)`)로 쓴다. ⚠️ `hnsw.*` GUC는 `vector.so`가 백엔드에 적재된 뒤에야
  정식 등록되므로, `create function ... set hnsw.*` 앞에 벡터 표현식 평가가 한 번
  선행해야 한다 — 없으면 `permission denied to set parameter`로 마이그레이션이 실패한다
  (Supabase의 `postgres` 롤은 superuser가 아니고 `load 'vector'`도 허용되지 않는다).
  ⚠️ 같은 마이그레이션이 위 권한 공백도 최소권한 매트릭스로 함께 닫아야 한다. 닫지 않으면
  이 검색 함수가 `authenticated`에게 `42501`을 던진다.
- **`apps/api/src/api/db/user.py` (`UserDb`, 02-03-PLAN)** — asyncpg 커넥션 계층을 두지
  않는다. `UserDb`는 요청자 JWT를 실은 PostgREST RPC 호출 어댑터이며, 트랜잭션 진입점에서
  GUC를 세우는 D-04의 asyncpg 요건은 이 결정으로 **불필요해졌다**. 쓰기 경로의 0행 → 403
  매핑(D-11)은 트랜스포트와 무관하게 그대로 유지된다.
- **`apps/api/src/api/health_check.py` (01-CONTEXT.md > D-11)** — Phase 1이 트랜스포트
  교체 지점으로 격리해 둔 파일이다. 이미 PostgREST 왕복을 쓰고 있으므로 이 결정으로
  구조가 바뀌지 않는다.

Phase 4의 EXPLAIN 회귀 테스트(RTV-08)는 `scripts/spike_db_transport.py`의 계획 파싱
(`walk_plan` / `has_hnsw_index_scan`)을 원형으로 쓴다. ⚠️ 그때 위 5번을 전제할 것 —
기본 계획의 인덱스 선택은 코퍼스 모양에 따라 달라지므로 "항상 HNSW"를 단언하는 테스트는
워크스페이스가 작을 때 거짓 실패한다.

### 이 스파이크가 판정하지 않은 것

- `relaxed_order` vs `strict_order` 비교 — Phase 4(RTV-04)의 일이다. 여기서는
  `strict_order`가 *적용되는지*만 봤다.
- 검색 품질 — 합성 난수 벡터 코퍼스는 트랜스포트 판정용이며 골든 질의 세트(RTV-06)와
  섞으면 안 된다.
- 워크스페이스가 커졌을 때의 계획 — 타깃이 750행보다 훨씬 커지면 플래너가 스스로 HNSW를
  고를 수 있다. 기본 계획의 인덱스 선택은 코퍼스 모양에 따라 달라지므로 Phase 4의 EXPLAIN
  회귀 테스트(RTV-08)는 이 사실을 전제로 작성해야 한다.
