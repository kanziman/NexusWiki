# Tenant Isolation 리뷰 — control-quality-measured-coverage r1

- 판정: needs_fix
- 대상: 커밋되지 않은 작업 트리 (`git diff`, 기준 커밋 `212d80a`) + 미추적 `supabase/migrations/0036_control_quality_measured.sql`
- 제외: `docs/ref/*.png` 삭제, `skills-lock.json`, 내용 차이가 없는 `openspec/specs/wiki-compilation/spec.md`
- 일시: 2026-11-03T14:07:41+09:00

## 검증 방법

- `0031`과 `0036`의 함수 정의를 `diff`로 대조했다. 차이는 측정 컬럼 2개, `measured` 계산, 각 지표의 `measured and` 조건, 주석뿐이다.
- 로컬 DB(`0036` 적용)의 `pg_proc`과 `has_function_privilege`를 조회했다.
- 로컬 DB에서 롤백 트랜잭션으로 owner, viewer, 비멤버 fixture를 만들어 실제 역할(`authenticated`, `anon`, `service_role`)로 RPC를 호출했다. 위조는 작성자 JWT 문맥의 UPDATE로 넣었다. 실행 후 잔여 행은 0이다.
- 운영 DB에는 접속하지 않았다. 운영 원장이 `0035`까지라는 사실은 호출자 제시 값과 `docs/reference/stack.md` 기재에 따른 것이며, 이번 리뷰에서 직접 조회하지 않았다.
- 전체 테스트는 다시 돌리지 않았다. 조치 3은 코드 읽기로 도출했으며 실행으로 재현하지 않았다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apps/api/src/api/routers/control.py:553`의 `_user_db` 경유. RPC 실행 권한에서 `service_role`도 회수됨 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 통과 | `proacl = {postgres=X/postgres,authenticated=X/postgres}`. `anon` 호출은 `permission denied` |
| A-4 | service_role·BYPASSRLS 코드의 `workspace_id` 필터 | 통과 | 워커 변경은 주석 1줄(`llm_gateway.py:94`). security definer 함수는 `ask_messages`, `usage_events`, `wiki_pages`를 모두 `p_workspace_id`로 필터링(`0036:83,109,133`) |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 쓰기 경로 없음. 읽기 RPC가 0행이면 403(`control.py:557-558`) |
| B-7 | `42501` → 403 매핑 | 통과 | 비멤버 RPC가 `42501`을 던지고, 라우터 테스트(`test_control_router.py`)와 격리 테스트(`test_tenant_isolation_full_path.py:669-672`)가 HTTP 403을 단언 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 신규·변경 핸들러 없음 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 변경 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 토크나이저 일치 | 해당 없음 | 색인·질의 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트의 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 | 통과 | `0036` > `0035`. `origin/main`의 최대 번호는 `0035`이고 `--all` 이력에 다른 `0036`·`0037`이 없음 |

### 요청받은 확인 항목

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| 재생성 시 `security definer`·`search_path`·역할 검사·권한 회수 | 통과 | `prosecdef = t`, `proconfig = {search_path=""}`, `has_workspace_role` 검사 동일(`0036:58-61`). `anon`·`service_role`·`authenticator` 실행 불가, `authenticated`만 가능. `control_risk_snapshot`·`control_budget_snapshot`과 ACL 동일 |
| viewer는 본인 Ask만, 수집 집계 차단 | RPC·API 통과, 원시 테이블은 기존 개방 | RPC 실측에서 viewer의 Ask는 본인 1턴, 수집·위키 집계는 0. API는 `structured`와 `evidence`를 `null`로 반환. 참고 A 확인 |
| 비멤버 403 | 통과 | 위 B-7. 미인증은 401 |
| 위조 `control_report`가 집계를 실패시키는가 | 통과 | 배열·문자열·`null`·`{}`·타입이 틀린 `violations`·중첩 객체·비불리언 수리 플래그를 넣어도 조회 성공. 최상위 비객체는 CHECK(`ask_messages_control_report_shape`)가 거부. viewer의 남의 턴 UPDATE는 0행 |
| 위조가 다른 멤버 화면을 깨뜨리는가 | 부분 위반 | 조회는 깨지지 않으나, 잘못된 값이 다른 멤버 화면에 "측정됨, 위반 없음"으로 보임. 조치 2 |
| 측정 건수의 개별 턴 역추적·본문 노출 | 통과 | 응답은 집계 수치뿐. UTC 일 절삭이 유지되어 같은 UTC 날짜의 시각을 바꿔도 결과가 같음(9/9/9). 새 컬럼으로 얻는 정보는 일 단위 측정 여부 합계뿐이며 작성자 식별자가 없음 |
| 미측정이 위반 없음으로 보이는 조용한 실패 | 위반 | 조치 1, 2, 3 |
| 번호와 운영 적용 순서 | 통과 | DB 선적용 시 기존 API는 키로 읽어 새 컬럼을 무시. 새 API가 먼저 뜨면 `_number(None) = 0`이 되어 "측정 기록 없음"으로 안전하게 표시. 단일 트랜잭션이고 `notify`는 커밋 시 전달. 대시보드 순서는 조치 3 |
| 운영 문서의 테넌트 정보 | 통과 | 저장소는 PUBLIC이다. 문서에 본문은 없고 워크스페이스명과 건수만 있다. 두 이름은 공개 랜딩 콘텐츠(`content.ts`)에 이미 있다 |

## 조치가 필요한 항목

1. **`off` 모드 턴이 측정됨, 위반 0건으로 집계된다** (심각도: 높음)
   - 위치: `supabase/migrations/0036_control_quality_measured.sql:70`, `apps/api/src/api/services/ask.py:1012,1051-1057`
   - 깨지는 것: `off`에서는 계약 검사를 건너뛰고도 `quality = {"mode": "off", "violations": [], ...}` 객체를 저장한다(`test_ask_router.py:1127-1130`이 이 저장을 고정). `0036`은 `quality`가 객체이면 측정으로 보므로 검사하지 않은 턴이 "측정 N건, 위반 0건"이 된다. 실측에서도 이 값이 측정 건수에 들어갔다. `docs/ops/ask-sample-replay.md:21`은 **위반이 늘면 `off`로 내리라고** 안내하므로, 문제가 커진 시점에 화면이 깨끗해진다. 모드를 다시 올리면 "꺼짐" 표시도 사라지지만 해당 기간의 턴은 최대 90일 조회 범위에 측정 데이터로 남는다. 이 변경이 없애려던 결함이 그대로 남았다.
   - 조치: `measured` 조건에 `m.control_report -> 'quality' ->> 'mode' in ('shadow', 'enforce')`를 넣는다. `mode` 키는 `quality` 도입 커밋(`1c3776c`)부터 항상 기록되므로 기존 측정 턴을 잃지 않는다. `off` 턴이 전체에만 들어가는 라우터 테스트를 추가하고, delta spec에 시나리오를 추가한다. `0036`은 운영 미적용이므로 파일을 직접 고치고 로컬에 다시 적용한다.

2. **형식이 잘못된 품질 기록이 측정됨, 위반 없음으로 집계된다** (심각도: 보통)
   - 위치: `supabase/migrations/0036_control_quality_measured.sql:70-75`, `apps/api/tests/test_control_router.py:853,914`
   - 깨지는 것: `{"quality": {}}`와 `{"quality": {"violations": "조작", ...}}`는 객체라서 측정으로 세고, `violations`는 `[]`로 대체되어 위반 없음이 된다. 실측에서 조회한 owner의 측정 5건 중 3건이 이런 "깨끗한" 값(`off`, `{}`, 타입 오류)이었다. 현재 라우터 테스트의 `measured_turns == 3`이 이 동작을 정답으로 고정한다. 이는 `design.md` D2의 "형식이 잘못된 턴은 측정에서 제외"와 spec의 "측정되지 않은 데이터를 위반 없음으로 MUST NOT 표시"에 어긋난다. viewer도 자기 턴에 쓸 수 있어, 측정 0건인 워크스페이스에서 위조 1건만으로 editor 화면의 "측정 기록 없음" 안내가 "위반 0건" 카드로 바뀐다.
   - 조치: `measured`를 `quality`가 객체이고 `violations`가 배열이며 `repair_attempted`와 `repaired`가 불리언일 때로 좁힌다(조치 1의 `mode` 조건과 함께). 테스트 기대값을 `measured_turns == 2`로 바꾸고 `{}` 시드를 추가한다. spec의 "형식이 잘못됐다" 시나리오를 객체 내부 형식까지 넓힌다.
   - 문서 조치: `design.md`의 "이번 변경으로 넓어지지 않는다"는 정확하지 않다. 이전에는 위조 객체와 미기록 턴의 화면이 같았지만, 이제는 올바른 형식의 위조로 측정 건수를 올려 안내를 지울 수 있다. 형식 검사로는 올바른 형식의 위조를 막지 못하므로, 이 잔여 위험을 수용 사유와 함께 사실대로 고쳐 적는다.

3. **새 대시보드가 새 API보다 먼저 뜨면 미측정이 0건 지표로 보인다** (심각도: 보통)
   - 위치: `apps/dashboard/components/ControlRoom.tsx:735,738,764,766`, `docs/reference/stack.md`의 `0036` 행, `supabase/migrations/0036_control_quality_measured.sql:12-13`
   - 깨지는 것: 기존 API 응답에는 측정 필드가 없다. `undefined === 0`은 거짓이므로 안내 대신 위반 0건 카드가 그려지고 값은 "측정 undefined건 / 전체 N건"이 된다. 대시보드는 Vercel CLI 업로드(`docs/ops/vercel-deploy-record.md:4`), API는 Railway로 따로 배포되는데, 문서는 DB와 API의 순서만 규정한다. 배포 간격 동안, 또는 API만 되돌렸을 때 이 상태가 된다.
   - 조치: 두 조건을 `!ask.measured_turns`, `!structured.measured_calls`로 바꿔 필드가 없어도 안내를 표시하게 하고 숫자 표시도 `?? 0` 등으로 처리한다. 필드가 없는 응답의 테스트를 추가한다. 운영 순서를 `0036` → API → 대시보드로 문서에 적는다.

## 참고 (이번 판정에 반영하지 않음)

- **A. viewer의 수집 집계 차단은 RPC·API 층까지다.** `usage_events_select_member`(`0009:143-145`)는 viewer를 포함한 모든 멤버에게 SELECT를 허용한다. 실측에서 viewer JWT로 `compile` 행의 `metadata ->> 'violation'`을 직접 읽었다. 같은 워크스페이스 안의 일이고 이 변경 이전부터 있던 동작이며, `0009`의 컬럼 주석도 멤버 조회를 전제로 한다. 테넌트 경계를 넘지 않고 이번 change가 넓히지도 않았다. 다만 viewer에게 수집 정보를 숨기는 것이 계약의 의도라면 표면만 막혀 있는 상태이므로, 별도 이슈로 사람이 결정해야 한다.
- **B. `0036`은 아직 미추적 파일이다.** 커밋에서 빠지면 새 API는 측정 0건만 돌려준다. 조치 1, 2로 파일을 고친 뒤 로컬 재적용이 필요하다.

## 판정 근거

테넌트 경계를 넘는 경로는 없다. 함수의 보안 속성과 권한은 `0031`과 동등하고, 비멤버와 `anon`은 차단되며, 위조 값이 집계를 실패시키지 않고, 역추적 경로도 늘지 않았다. 그러나 이 change의 목적인 "측정되지 않은 데이터를 위반 없음으로 표시하지 않는다"가 세 경로에서 지켜지지 않는다. 특히 `off` 모드는 위조 없이 운영 절차만으로 발생한다. 모두 코드 수정으로 해결되고 `0036`이 운영에 미적용이므로 `blocked`가 아니라 `needs_fix`다.
