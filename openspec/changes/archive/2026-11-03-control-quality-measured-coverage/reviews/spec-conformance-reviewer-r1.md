# Spec Conformance 리뷰 — control-quality-measured-coverage r1

- 판정: pass
- 대상: 커밋되지 않은 작업 트리 (기준 `212d80a`)와 `git diff`, 미추적 `supabase/migrations/0036_control_quality_measured.sql`
- 제외: `docs/ref/*.png` 삭제, `skills-lock.json`, `openspec/specs/wiki-compilation/spec.md` (요청에 따라 범위 밖)
- 일시: 2026-11-03T05:07:27Z

## 이번 라운드에서 직접 확인한 것

| 확인 | 결과 |
| --- | --- |
| `uv run pytest apps/api/tests/test_control_router.py -k "quality or risk or proposal"` | 1건 통과, 건너뜀 없음 |
| `uv run pytest apps/worker/tests/test_wiki_proposals.py apps/api/tests/test_tenant_isolation_full_path.py -k "risk or control_quality or proposal"` | 7건 통과, 건너뜀 없음 |
| `npx vitest run tests/ControlRoom.test.tsx` | 20건 통과 |
| 로컬 원장과 함수 (`supabase_migrations.schema_migrations`, `pg_get_function_result`) | `0036` 적용됨, `ask_measured_turns` 컬럼 있음 |
| 로컬 스택에서 롤백 트랜잭션으로 RPC 실행 (아래) | 시나리오 수치와 일치 |
| `npx -y supabase@2.111.0 migration list --linked` (읽기 전용) | `0001`~`0035` Local/Remote 일치, `0036`은 Remote 없음 |

그 밖의 전체 검증(`openspec validate --strict`, 전체 pytest, 대시보드 전체 테스트, Ruff, typecheck, lint)은 호출자가 보고한 결과이며 요청에 따라 다시 실행하지 않았다.

롤백 트랜잭션 실행 결과. 각 멤버의 JWT 클레임을 설정한 `authenticated` 역할로 호출했고, 트랜잭션을 롤백해 로컬에도 남은 데이터가 없다. 운영 DB에는 쓰지 않았다.

| 경우 | 시드 | 결과 |
| --- | --- | --- |
| owner, 일부 측정 | 턴 7건(시나리오의 6건 중 4건 측정 + viewer 본인 측정 1건). 미측정 2건은 `control_report` null과 `quality` 키 없음이며 둘 다 `fallback`. 호출 2건 중 1건만 `policy_version` | 측정 5 / 전체 7, 위반 2, Fallback 1(측정된 것만), 측정 1 / 전체 2, `json_invalid` 1, `exhausted` 0(미측정 호출의 표기 제외) |
| owner, 전부 미측정 | 턴 6건(`quality`가 문자열, 배열, 숫자, JSON null, `control_report` null, 빈 객체). 호출 1건 `policy_version` 없음 | 측정 0 / 전체 6, 모든 턴 지표 0, 측정 0 / 전체 1, 모든 호출 지표 0, 조회 예외 없음 |
| viewer | 위 첫 워크스페이스 | 전체 1, 측정 1, 수집 집계 0 |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 품질 탭 / editor가 품질 탭을 연다 | 충족 | `apps/api/src/api/routers/control.py:570-577` · `apps/dashboard/components/ControlRoom.tsx:728-801` · 테스트 `apps/api/tests/test_control_router.py:929`, `apps/dashboard/tests/ControlRoom.test.tsx:452` |
| 품질 탭 / viewer가 품질 탭을 연다 | 충족 | 본인 한정 `supabase/migrations/0036_control_quality_measured.sql:86`, 수집 차단 `0036:108,132` · 테스트 `apps/api/tests/test_control_router.py:936-938`, `apps/dashboard/tests/ControlRoom.test.tsx:504,676` |
| 품질 탭 / 비멤버의 요청 | 충족 | `0036:58` · 테스트 `apps/api/tests/test_control_router.py:907`, `apps/api/tests/test_tenant_isolation_full_path.py:649` |
| 품질 탭 / 집계할 데이터가 없다 | 충족 | `apps/dashboard/components/ControlRoom.tsx:715-722` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:537` |
| 품질 탭 / 측정 전 데이터가 일부 섞여 있다 | 충족 | 측정 판별 `0036:70`, 측정 한정 집계 `0036:91-98`, 표시 `ControlRoom.tsx:735` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:624`(4 / 6), `apps/api/tests/test_control_router.py:913-914`(3 / 5). 자동 테스트의 6 / 4 수치는 화면 스텁이고 RPC 수치는 3 / 5이며, 위 롤백 실행으로 RPC에서도 확인 |
| 품질 탭 / 측정된 데이터가 하나도 없다 | 충족 | `ControlRoom.tsx:738-739,766-767` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:642,676` |
| 품질 탭 / 품질 기록의 형식이 잘못됐다 | 충족 | `0036:70` · 테스트 `apps/api/tests/test_control_router.py:855-856`. 키 없음과 `control_report` null은 자동 테스트 없음, 롤백 실행으로 확인 (조치 항목 없음, 아래 참고 1) |
| 품질 탭 / 멤버가 지표의 기준을 확인한다 | 충족 | `ControlRoom.tsx:732,760,795`, `.note`는 숨김 처리 없음 `apps/dashboard/components/ControlRoom.module.css:110-115` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:687` |
| 리스크 탭 / editor가 대기 제안을 처리한다 | 충족 | `ControlRoom.tsx:657-694` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:713` |
| 리스크 탭 / viewer가 리스크 탭을 연다 | 충족 | `ControlRoom.tsx:695-697` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:802,832`, `apps/worker/tests/test_wiki_proposals.py:159-160` |
| 리스크 탭 / 비멤버의 요청 | 충족 | `apps/api/src/api/routers/control.py:607-618` · 테스트 `apps/worker/tests/test_wiki_proposals.py:132`(`outsider_resp` 403 단언) |
| 리스크 탭 / 멤버가 지표의 기준을 확인한다 | 충족 | 화면 `ControlRoom.tsx:642-656`, 표시한 기준과 실제 집계 일치 `supabase/migrations/0034_control_risk_tab.sql:47-51,58,60`(기간 제한) · `0034:53,56`(기간 제한 없음) · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:802` |

## tasks.md 인수 조건 판정

| Task | 결과 | 증거 |
| --- | --- | --- |
| 1.1 측정 4 / 6과 1 / 2 표시, 측정 데이터만 집계 | 충족 | 위 표와 롤백 실행. `policy_version` 기록은 `apps/worker/src/worker/llm_gateway.py:94-95`, 테스트 `apps/worker/tests/test_risk_policy.py:141` |
| 1.1 기록 없음 또는 형식 오류 시 측정 기록 없음, 조회 실패 없음 | 충족 | 위 표와 롤백 실행 |
| 1.1 viewer 본인 측정만, 수집 없음, 비멤버 403 | 충족 | 위 표 |
| 2.1 품질과 리스크의 묶음별 기준 표시, viewer 버튼 없음 | 충족 | 위 표 |
| 3.1 `stack.md` 표기 | 충족 | `docs/reference/stack.md:54,77-86`. `운영 미적용`은 줄 54의 안내문과 `0036` 행뿐이고, `migration list --linked` 결과와 일치 |
| 3.1 머지 전 `0036` 선적용 순서 | 충족 | `docs/reference/stack.md:54,86`, `docs/ops/wiki-evidence-backfill.md:27`, `supabase/migrations/0036_control_quality_measured.sql:12-13` |
| 3.1 백필 문서의 실행 범위와 건수, 미실행 3개 워크스페이스 | 충족 (문서 내용 기준) | `docs/ops/wiki-evidence-backfill.md:152-171`. 기록된 건수가 운영 실측과 같은지는 운영 DB를 조회하지 않아 확인하지 않았다 |
| 3.1 위임 경계, 외부 공유 경계, 본문 부재 | 충족 | `docs/ops/wiki-evidence-backfill.md:12-14,44,150-177` |
| 3.1 아카이브 후 계약 경로 | 충족 | `docs/ops/wiki-evidence-backfill.md:4-5`, 경로 `openspec/changes/archive/2026-11-03-backfill-wiki-evidence/` 실재 |

## 설계 결정과의 대조

- D1: `policy_version` 판별(`0036:106`)과 양쪽 주석(`0036:104-105`, `llm_gateway.py:94`) 확인.
- D2: 타입 확인 후 측정 판정과 Fallback 측정 한정(`0036:70,98`) 확인.
- D3: 단일 트랜잭션 재생성과 권한 재설정(`0036:16,20,163-166`) 확인. 로컬에서 `anon` 실행 불가, `authenticated` 실행 가능을 조회로 확인. API 필드 추가(`control.py:571,584`) 확인, 기존 필드 유지.
- D4, D5: 측정 0건 안내와 묶음별 캡션 확인.

델타의 MODIFIED 요구사항은 기존 `openspec/specs/ai-control-room/spec.md:118-150`의 요구사항 문장과 시나리오를 모두 유지한다. viewer 시나리오의 THEN만 측정 건수를 포함하도록 넓어졌다. 조용한 범위 축소는 찾지 못했다.

## 조치가 필요한 항목

없음.

## 참고 (판정에 영향 없음)

1. **미측정 형태의 자동 테스트 범위** — 라우터 테스트는 `quality`가 문자열과 JSON null인 경우만 시드한다. 스펙의 "없다"에 해당하는 `quality` 키 없음과 `control_report` null(`0036:70`의 `coalesce` 분기)은 이번 라운드의 수동 실행으로만 확인했다. 동작은 맞으므로 미충족은 아니다. `_seed_quality_turn`은 항상 `quality` 키를 넣으므로, 회귀 방지를 원하면 이 경우를 별도로 시드할 수 있다.
2. **스펙에 명시되지 않은 표시** — 한 경로만 비어 있을 때(턴 0건이고 호출은 있음, 또는 그 반대) 그 경로에 `이 기간의 답변이 없습니다` 안내가 나온다(`ControlRoom.tsx:702-709`, 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:661`). 스펙의 "집계할 데이터가 없다"는 양쪽이 모두 없는 경우만, D4는 전체 빈 상태만 다룬다. "0을 정상 수치처럼 꾸미지 않는다"의 직접적인 귀결이고 새 기능이 아니어서 범위 이탈로 보지 않았다. 원한다면 `/opsx:sync` 전에 시나리오로 명문화할 수 있다.
3. **승인 반영과 거부의 기간 축** — `0034:58,60`은 처리 시각이 아니라 제안 생성 시각으로 기간을 자른다. 40일 전에 만들어져 어제 반영된 제안은 "최근 30일 기준" 묶음에 세지 않는다. 스펙은 축을 정하지 않았고 이번 변경이 바꾼 동작도 아니지만, 이번에 캡션이 생기면서 사용자가 읽는 의미가 됐다.
4. **문서 제목** — `docs/ops/wiki-evidence-backfill.md:81`의 `apply — 운영자 전용` 제목은 1절의 위임 예외(줄 14)를 반영하지 않는다. 경계 자체는 1절에 명확하다.

## 판정 근거

delta spec의 12개 시나리오와 tasks.md 인수 조건이 모두 코드 경로, 테스트 또는 직접 실행으로 확인됐다. `needs_fix`나 `blocked`에 해당하는 미충족 시나리오, 스펙 모호성, 범위 이탈은 없다. 운영 `0036` 적용과 머지는 tasks.md대로 운영자 몫이며 이 판정의 대상이 아니다.
