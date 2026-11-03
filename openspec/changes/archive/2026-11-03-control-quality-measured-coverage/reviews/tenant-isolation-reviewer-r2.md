# Tenant Isolation 리뷰 — control-quality-measured-coverage r2

- 판정: pass
- 대상: 커밋되지 않은 작업 트리 (`git diff`, 기준 커밋 `212d80a`) + 미추적 `supabase/migrations/0036_control_quality_measured.sql`
- 제외: `docs/ref/*.png` 삭제, `skills-lock.json`, 내용 차이가 없는 `openspec/specs/wiki-compilation/spec.md`
- 일시: 2026-11-03T14:14:31+09:00
- 이전 라운드: `tenant-isolation-reviewer-r1.md` (`needs_fix`, 조치 3건)

## 검증 방법

- **수정된 `0036` 파일 자체를 검증했다.** 로컬 DB의 롤백 트랜잭션에서 파일을 실행해 함수를 다시 만들고, 그 함수의 속성과 ACL을 조회한 뒤 실제 역할로 호출했다. 위조 값은 작성자 JWT 문맥의 UPDATE로 넣었다. 실행 후 fixture 잔여 행은 0이고 함수는 1개다.
- 로컬 DB에 올라간 함수 본문과 파일 본문을 대조했다. 차이는 추출 과정에서 생긴 끝 빈 줄뿐이다.
- 관련 테스트만 새로 실행했다.
  - `uv run pytest apps/api/tests/test_control_router.py apps/api/tests/test_tenant_isolation_full_path.py -k quality`: 2건 통과
  - `npx vitest run tests/ControlRoom.test.tsx`: 21건 통과
- 전체 테스트는 돌리지 않았다. 운영 DB에는 접속하지 않았으며, 운영 원장이 `0035`까지라는 사실은 호출자 제시 값과 `docs/reference/stack.md` 기재에 따른 것이다.

## r1 조치 재확인

| r1 항목 | 결과 | 근거 |
| --- | --- | --- |
| 1. `off` 턴이 측정으로 집계 | 해결 | `0036:72-79`의 `mode in ('shadow','enforce')`. `ask.py`가 저장하는 실제 형태의 `off` 값이 미측정으로 판정됨. `test_control_router.py:863`이 고정 |
| 2. 형식 오류 기록이 측정으로 집계 | 해결 | `violations` 배열과 수리 플래그 불리언을 요구. `{}`와 타입 위조가 미측정으로 판정됨. 기대값 `turns 7`, `measured_turns 2`(`test_control_router.py:921-922`) 통과 |
| 2. `design.md`의 잔여 위험 서술 | 해결 | D2와 위험 항목이 수정됨. 올바른 형식의 위조로 안내가 카드로 바뀔 수 있음을 수용한 위험으로 명시. 단, 참고 A의 낡은 문장 1개가 남음 |
| 3. 새 대시보드 + 기존 API에서 0건 카드 | 해결 | `ControlRoom.tsx:715-716`의 `?? 0`, 판정은 `:741,769`. `ControlRoom.test.tsx:676`이 필드 없는 응답과 `undefined` 미표시를 단언. 운영 순서는 `stack.md:86`과 `0036:12` |

### 측정 판정 실측

사례별로 그 턴만 값을 넣고 측정 여부를 확인했다. 13건 모두 기대와 일치했고, 어떤 값에서도 조회가 실패하지 않았다.

| 값 | 측정 |
| --- | --- |
| `off` 실제 형태, `{}`, 타입 위조, 배열, 문자열, `null`, `quality` 키 없음 | 아니오 |
| 플래그 타입 오류, `mode` 없음, `mode` 비문자열 | 아니오 |
| `shadow` 정상, `enforce` Fallback 정상 | 예 |
| 올바른 형식에 이상한 원소가 든 `violations` | 예 (수용한 위험) |

전체 사례를 함께 넣은 owner 집계도 기대와 일치했다. 전체 14, 측정 4, 위반 3, 인용 없음 2, 위조 앵커 1, 수리 시도 1, 수리 성공 0, Fallback 1이다.

**회귀 없음:** `ask.py`의 `quality` 네 키(`mode`, `violations`, `repair_attempted`, `repaired`)는 도입 커밋 `1c3776c`부터 같은 형태로 기록되므로, 강화된 조건이 정상 턴을 미측정으로 떨어뜨리지 않는다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `control.py:553`의 `_user_db` 경유 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 통과 | `proacl = {postgres=X/postgres,authenticated=X/postgres}`. `anon` 호출은 `permission denied` |
| A-4 | service_role·BYPASSRLS 코드의 `workspace_id` 필터 | 통과 | 워커 변경은 주석 1줄. security definer 함수의 세 원천 테이블 필터가 유지됨 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 쓰기 경로 없음. 읽기 RPC가 0행이면 403(`control.py:557-558`) |
| B-7 | `42501` → 403 매핑 | 통과 | 비멤버 RPC가 `42501`을 던지고, 관련 테스트가 HTTP 403을 단언해 통과 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 신규·변경 핸들러 없음 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 변경 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 토크나이저 일치 | 해당 없음 | 색인·질의 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트의 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 | 통과 | `0036` > `0035`. 다른 `0036`·`0037` 없음 |

### r1 요청 항목의 재확인

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| 재생성 시 보안 속성과 권한 회수 | 통과 | 파일에서 만든 함수가 `prosecdef = t`, `search_path=""`. `anon`·`service_role`·`authenticator` 실행 불가. 권한 구문은 `0031`과 동일(`diff` 차이 없음) |
| viewer 범위 | RPC·API 통과 | viewer는 본인 1턴만 받고 수집·위키 집계는 0, API는 `null`. 원시 테이블은 참고 B |
| 비멤버 403, 미인증 401 | 통과 | 테스트 통과, RPC 실측에서 `42501` |
| 개별 턴 역추적·본문 노출 | 통과 | 일 절삭 유지. 같은 UTC 날짜의 경계를 바꿔도 측정 건수가 같음(1/1/1). 응답은 집계 수치뿐 |
| 미측정이 위반 없음으로 보임 | 통과 | r1 세 경로 해결. 구조화 호출에는 `off`에 해당하는 경로가 없음(`QUALITY_MODE`가 worker와 core에 없고 `complete_structured`는 항상 검증). `usage_events`는 `anon`·`authenticated`의 INSERT·UPDATE·DELETE 권한이 없어 작성자가 위조할 수 없음 |
| 적용 순서 | 통과 | 어느 배포 순서에서도 미측정이 0건 지표로 보이지 않음. `0036` 없이 새 API가 뜨면 측정 0건, 새 대시보드에 기존 API면 필드 없음으로 둘 다 안내 표시 |

## 조치가 필요한 항목

없음.

## 참고 (판정에 반영하지 않음)

- **A. `design.md:3`에 수정 전 문장이 남아 있다.** "답변 턴은 `quality`가 객체인지로 측정 여부를 판별할 수 있지만"은 D2와 반대다. 코드와 spec은 맞고 문서의 Context 한 문장만 낡았다. PR 전에 고치면 되며 재리뷰는 필요 없다.
- **B. viewer의 `usage_events` 직접 조회는 그대로다.** r1 참고 A의 동작이며 이 change 이전부터 있었고 테넌트 경계를 넘지 않는다. 호출자가 사용자 결정으로 넘겼으므로 이번 판정에 넣지 않았다. 아직 결정되지 않은 상태다.
- **C. `ask.py`의 `quality` 형태와 `0036` 조건을 잇는 테스트가 없다.** 라우터 테스트는 손으로 쓴 값을 시드한다. `ask.py`에서 키 이름을 바꾸면 모든 턴이 미측정으로 보인다. 위반 없음이 아니라 "측정 기록 없음"으로 드러나는 방향이라 조용한 실패는 아니다. `policy_version`처럼 `ask.py`에 의존 주석을 다는 정도가 적절하다.
- **D. 올바른 형식의 위조는 남아 있다.** `control_report`는 작성자가 쓸 수 있으므로 형식 검사로 막을 수 없고, `design.md`에 수용한 위험으로 기록되어 있다. 측정 건수와 전체 건수가 함께 표시되며 다른 테넌트에는 영향이 없다.
- **E. `0036`은 아직 미추적 파일이다.** 커밋에서 빠지지 않게 해야 하며, 운영 적용과 머지는 운영자가 `0036`, API, 대시보드 순서로 수행한다.

## 판정 근거

r1의 조치 3건이 모두 해결되었음을 수정된 파일의 실행과 관련 테스트로 확인했고, 수정으로 생긴 회귀나 새 위반은 없다. 테넌트 격리 속성은 `0031`과 동등하게 유지된다. 남은 사항은 낡은 문서 한 문장, 사용자 결정으로 넘겨진 기존 동작, 설계에 수용된 위험, 작업 순서 안내이며 어느 것도 이 게이트의 위반이 아니다.
