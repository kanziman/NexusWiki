# 테넌트 격리 증명 (SEC-06)

## 배경

`0004_rls_policies.sql`은 9개 테이블에 20여 개의 정책을 걸었고, `0007` 섹션 8이 그 정책이
실제로 효력을 갖도록 권한 공백을 닫았다. 그러나 여기까지는 전부 **데이터베이스 안에서만**
확인된 사실이다. "사용자 A가 워크스페이스 B를 건드리려 하면 애플리케이션이 Forbidden을
돌려준다"는 SEC-06의 문장은, 요청이 HTTP로 들어와 라우터와 `UserDb`를 거쳐 PostgREST까지
갔다가 돌아오는 왕복 전체가 있어야 검증할 수 있다.

Phase 2 이전까지 이 저장소에는 도메인 라우터가 하나도 없었다. 증명할 표면이 없었다는
뜻이다. `apps/api/src/api/routers/workspaces.py`의 `PATCH`/`DELETE /workspaces/{id}` 두
경로는 그래서 존재한다 — **제품 기능이 아니라 격리 증명 표면**이며, 실제 도메인 라우터는
Phase 3~5가 세운다. 라우터를 최소로 유지한 이유도 같다: 증명하려는 것이 라우터의 기능이
아니라 그 아래 계층의 격리이기 때문이다.

이 두 경로가 왕복 검증에 충분한 이유는 격리 판정이 라우터가 아니라 그 아래에서 일어나기
때문이다. 라우터는 요청자 JWT로 `UserDb`를 만들어 호출할 뿐이고, 상태 코드도 예외 처리도
직접 다루지 않는다. RLS가 막은 결과는 `UserDb`가 영향 행 수로 판정하고
(`02-CONTEXT.md > D-11`), 렌더링은 `api/errors.py`의 단일 핸들러가 한다
(`02-CONTEXT.md > D-13`). 따라서 이 두 경로에서 관측되는 것은 `workspaces` 라우터의
성질이 아니라 **모든 사용자 요청 경로가 공유하는 계층의 성질**이다.

### D-12의 귀결 — 세 가지가 같은 응답을 받는다

`02-CONTEXT.md > D-12`는 존재하지 않는 리소스와 격리 위반을 구분하지 **않기로** 했다.
Not Found를 돌려주면 다른 테넌트의 리소스 존재 여부가 상태 코드로 새어나가 열거 공격이
성립하기 때문이다. 그 결정의 귀결로, 아래 세 가지가 응답에서 구별되지 않는다.

| 요청 | 실제 상황 | 응답 |
|---|---|---|
| A가 B의 워크스페이스에 `PATCH`/`DELETE` | 격리 위반 | Forbidden |
| A가 존재한 적 없는 UUID에 `PATCH`/`DELETE` | 리소스 부재 | Forbidden |
| A가 자기 워크스페이스를 삭제한 뒤 다시 삭제 | 이미 사라진 리소스 | Forbidden |

세 번째 줄이 특히 직관에 어긋나 보인다 — 자기 것을 지웠는데 두 번째 호출이 Forbidden이다.
이것은 버그가 아니라 D-12를 채택한 순간 결정된 귀결이다. 응답을 다르게 만들려면 "그 id의
리소스가 존재하는가"를 응답에 실어야 하고, 그 순간 남의 워크스페이스에 대해서도 같은 정보가
새어나간다.

## 방법

### 측정 일시

- 2026-08-07
- 로컬 스택 `supabase_db_NexusWiki`, 마이그레이션 `0001`~`0007` 적용 상태

### 대상

`apps/api/tests/test_workspaces_isolation.py` 13건. 워크스페이스 2개 × 사용자 2명을
테스트마다 새로 만들고 정리하며, `CROSS_TENANT_CASES` 2행(`PATCH`/`DELETE`)을 양방향 ·
부재 UUID · 소유자 정상 경로 · 미인증 5종으로 돌린다.

### 위반 픽스처

`supabase/tests/0004_loosened_rls_violation.sql`. `workspaces`의 SELECT · UPDATE ·
DELETE 정책에서 테넌트 술어만 걷어내고 `to authenticated`는 그대로 둔다 — 그것까지 풀면
"격리가 깨졌다"가 아니라 "인증이 깨졌다"를 관측하게 되어 red의 원인을 구별할 수 없다.

적용 명령:

```bash
# 느슨하게
sed -n '/-- 1\./,/-- 2\./p' supabase/tests/0004_loosened_rls_violation.sql \
  | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
# 되돌리기
sed -n '/-- 2\./,$p' supabase/tests/0004_loosened_rls_violation.sql \
  | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
```

### 절차

1. 정상 정책에서 격리 테스트가 통과함을 확인한다.
2. 느슨한 정책을 적용한다.
3. 같은 테스트가 non-zero로 종료하는 것을 관측하고 어떤 케이스가 어떻게 실패했는지 적는다.
4. 되돌리기 섹션을 적용하고, `pg_policies`의 `qual`/`with_check` 문자열을 2단계 이전 값과
   대조해 복원을 확인한다 — "되돌리기를 실행했다"는 사실만으로는 복원의 증거가 아니다.
5. 테스트가 다시 통과함을 확인한다.

## 결과

### 3단계 종료 코드

| 단계 | 정책 상태 | `pytest … test_workspaces_isolation.py` 종료 코드 | 결과 |
| --- | --- | ---: | --- |
| 1 (정상) | `0004` 원본 | **0** | 13 passed |
| 3 (느슨) | 위반 픽스처 적용 | **1** | 5 failed, 8 passed |
| 5 (복구) | 되돌리기 적용 | **0** | 13 passed |

### 느슨 단계에서 실패한 케이스

```text
FAILED test_cross_tenant_write_is_forbidden[PATCH-남의 워크스페이스 이름 변경]
FAILED test_cross_tenant_write_is_forbidden[DELETE-남의 워크스페이스 삭제]
FAILED test_cross_tenant_write_is_forbidden_in_the_other_direction[PATCH-남의 워크스페이스 이름 변경]
FAILED test_cross_tenant_write_is_forbidden_in_the_other_direction[DELETE-남의 워크스페이스 삭제]
FAILED test_read_that_rls_blocks_returns_empty_instead_of_forbidden
```

실패 형태는 전부 `assert 200 == 403`이다 — 교차 테넌트 쓰기가 실제로 성공해 갱신된 행이
돌아왔다. `service_role`로 다시 읽어 대상 워크스페이스의 `name`이 실제로 바뀐 것도 확인했다.
관측된 것은 "테스트가 까다로워졌다"가 아니라 "격리가 실제로 뚫렸다"이다.

반대로 아래 8건은 느슨 단계에서도 green이며, 그것이 정상이다.

- 부재 UUID 2건 — 어떤 테넌트에도 그 행이 없으므로 정책과 무관하게 0행이다.
- 재삭제 1건 — 같은 이유.
- 미인증 2건 — `to authenticated`를 건드리지 않았으므로 인증 계층은 그대로다.
- 소유자 정상 경로 2건 + 픽스처 신선도 1건 — 정책을 넓히는 변경이라 영향받지 않는다.

즉 red/green의 분포가 "무엇을 풀었는지"와 정확히 대응한다. 전부 빨개졌다면 그것은 테스트가
정책이 아니라 다른 무엇(환경·인증)에 반응한다는 신호였을 것이다.

### 부수 발견 — 교차 테넌트 쓰기를 막는 술어는 두 겹이다

처음 만든 위반 픽스처는 UPDATE·DELETE 정책만 풀었고, 그 상태에서 격리 테스트는 **13건 전부
통과했다**. 원인은 테스트의 공허함이 아니라 Postgres의 동작이었다. `update … where id = $1`은
대상 행을 먼저 읽어야 찾으므로, SELECT 정책이 그 행을 가리고 있으면 UPDATE 술어를 아무리
풀어도 0행이 돌아온다. 두 방향을 각각 확인했다.

| 느슨하게 만든 정책 | A가 B의 워크스페이스에 `PATCH` | B의 행이 실제로 바뀌었나 |
| --- | --- | --- |
| UPDATE·DELETE만 | HTTP 200, 본문 `[]` → 403 | 아니오 |
| SELECT만 | HTTP 200, 본문 `[]` → 403 | 아니오 |
| SELECT + UPDATE | HTTP 200, 갱신된 행 반환 | **예** |

`workspaces_select_member`와 `workspaces_update_owner`가 각각 독립적으로 교차 테넌트 쓰기를
막고 있다. 이것은 설계된 심층 방어라기보다 Postgres RLS의 구조에서 따라 나온 성질이지만,
결과적으로 한 정책이 실수로 넓어져도 다른 하나가 남는다. 뒤집어 말하면 **정책 하나를 푸는
것만으로는 이 표면에서 격리 회귀를 재현할 수 없다** — 앞으로 이 종류의 fail-first를 쓸 때
반드시 알고 있어야 하는 사실이라 위반 픽스처의 ⚠️ 주석에도 남겼다.

### 복원 확인

되돌리기 적용 후 `pg_policies`의 4개 정책 행(`policyname | qual | with_check | roles`)이
느슨하게 만들기 전과 문자열 단위로 일치했다. 이후 `supabase db reset`으로 마이그레이션만
적용한 상태와도 다시 대조해 일치를 확인했다 — 느슨한 정의가 마이그레이션 경로에 흘러들지
않았다는 뜻이다. `git diff --name-only supabase/migrations/`는 빈 출력이다.

테스트 실행 후 잔여 행도 0이다 (`workspaces where name like 'test-%'` = 0,
`auth.users where email like 'test-%@example.test'` = 0).

## 한계

- **이 증명은 `workspaces` 라우터 2개 표면에 한정된다.** `PATCH`/`DELETE /workspaces/{id}`
  가 다루는 것은 `workspaces` 테이블 하나이며, 나머지 8개 테이블과 Storage 경로는 여기서
  확인되지 않았다. 모든 애플리케이션 경로에 대한 전수 격리 스위트는 Phase 7의 OPS-04다
  (`.planning/REQUIREMENTS.md:279`). `CROSS_TENANT_CASES`는 그때 행만 추가하면 되도록
  만들어 두었다.
- **자기 워크스페이스 재삭제가 Forbidden인 것은 버그가 아니라 D-12의 직접 귀결이다.**
  존재 여부를 상태 코드로 노출하지 않기로 한 결정이 이 지점에서 그렇게 보인다. 두 번째
  호출을 다르게 응답하려면 "그 id의 리소스가 존재하는가"를 응답에 실어야 하고, 그 순간
  남의 워크스페이스에 대해서도 같은 정보가 새어나간다.
- **읽기 경로의 교차 테넌트 차단은 "빈 결과"로만 확인했다.** 읽기에는 0행 = 403 규칙이
  적용되지 않으므로(D-11) 여기서 관측되는 것은 상태 코드가 아니라 결과 집합이다. 읽기
  경로에서 격리가 풀리면 응답 코드는 변하지 않고 내용만 늘어난다 — 조용한 실패이며,
  그래서 `test_read_that_rls_blocks_returns_empty_instead_of_forbidden`이 존재한다.
- **로컬 스택에서만 관측했다.** 클라우드(`ap-southeast-1`)는 `0007`까지 같은 스키마·같은
  권한 매트릭스임이 `docs/ops/migration-0007-record.md`에서 확인되었지만, 실제 왕복 격리
  테스트를 클라우드에 대고 돌린 적은 없다. 이 픽스처는 루프백 주소에서만 동작하도록
  `apps/api/tests/conftest.py`가 강제한다 — 사용자와 워크스페이스를 만들고 지우는 테스트를
  운영 프로젝트에 겨누는 사고를 구조적으로 막기 위해서다.
- **동시성은 확인하지 않았다.** 픽스처는 테스트마다 고유한 행을 만들어 실행 순서에 무관하지만,
  같은 워크스페이스에 대한 동시 쓰기 경합은 이 증명의 범위 밖이다.
