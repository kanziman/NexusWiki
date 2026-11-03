# Spec Conformance 리뷰 — control-quality-measured-coverage r2

- 판정: needs_fix
- 대상: 커밋되지 않은 작업 트리 (기준 `212d80a`)와 `git diff`, 미추적 `supabase/migrations/0036_control_quality_measured.sql`
- 제외: `docs/ref/*.png` 삭제, `skills-lock.json`, `openspec/specs/wiki-compilation/spec.md` (r1과 동일)
- 일시: 2026-11-03T05:15:54Z

## r1 판정 정정

r1의 `pass`는 틀렸다. 당시 구현은 `off` 모드 턴과 `{}` 같은 형식 오류 기록을 측정으로 셌고, 이는 당시 요구사항의 "측정되지 않은 데이터를 위반 없음으로 MUST NOT 표시"에도 어긋났다. r1에서는 `off` 턴을 시드하지 않았고 `quality` 객체의 생성 경로(`apps/api/src/api/services/ask.py:1051-1057`)도 읽지 않아 놓쳤다. 이번 라운드는 생성 경로부터 대조했다.

## 이번 라운드에서 직접 확인한 것

| 확인 | 결과 |
| --- | --- |
| `uv run pytest` 3개 파일 `-k "control_quality or risk or proposal"` (`test_control_router.py`, `test_tenant_isolation_full_path.py`, `test_wiki_proposals.py`) | 8건 통과, 건너뜀 없음 |
| `npx vitest run tests/ControlRoom.test.tsx` | 21건 통과 |
| `openspec validate control-quality-measured-coverage --strict` | 통과 |
| 로컬 함수 본문과 `0036` 파일 비교 (`pg_proc.prosrc`, 빈 줄 제외) | 동일. `security definer`, `anon` 실행 불가, `authenticated` 실행 가능 |
| `npx -y supabase@2.111.0 migration list --linked` (읽기 전용) | `0035`까지 일치, `0036` Remote 없음. 따라서 미적용 파일을 고친 것은 안전하다 |
| 생성 경로 대조 | `ask.py:1051-1057`이 `mode`, `violations`(리스트), `repair_attempted`, `repaired`(불리언)를 항상 함께 쓴다. `settings.py:77`의 모드는 `off`, `shadow`, `enforce`뿐이다. 따라서 강화된 조건이 정상 턴을 탈락시키는 경로는 없다. 형태가 `1c3776c`부터 같았다는 점은 격리 리뷰 r1의 기록이며, `repair_attempted`가 이 커밋에서 처음 등장한 것만 `git log -S`로 확인했다 |

전체 pytest, 대시보드 전체 테스트, typecheck, lint, Ruff는 요청에 따라 실행하지 않았다.

로컬 스택 롤백 트랜잭션 실행 결과. 각 멤버의 JWT 클레임을 설정한 `authenticated` 역할로 호출했다. 운영 DB에는 쓰지 않았다.

| 경우 | 시드 | 결과 |
| --- | --- | --- |
| A owner | 유효 4건(`enforce` 2, `shadow` 2) + 미측정 2건(`control_report` null, `quality` 키 없음, 둘 다 `fallback`) + viewer 본인 유효 1건 | 전체 7, 측정 5, 위반 3, 인용 없음 2, 위조 1, 수리 시도 2, 성공 1, Fallback 1 |
| A viewer | 같은 워크스페이스 | 전체 1, 측정 1, 위반 0, 수집 0 |
| B owner | 미측정 16건. 비객체, `{}`, null 변형, `off` 2건(위반 포함 1건), 그리고 `mode`, `violations`, `repair_attempted`, `repaired`를 **하나씩만** 깨거나 뺀 기록 | 전체 16, 측정 0, 모든 지표 0, 조회 예외 없음 |
| C owner | `off` 1건 + `enforce` 1건 | 전체 2, 측정 1 |

## 시나리오 판정

바뀐 시나리오를 먼저 적는다.

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 품질 탭 / 품질 기록의 형식이 잘못됐다 **(확장)** | 동작 충족, 테스트 부족 | 구현 `supabase/migrations/0036_control_quality_measured.sql:72-79`, 위 B 실행으로 필드별 확인. 자동 테스트는 "없거나, 객체가 아니거나"만 검증한다. "위반 목록과 수리 여부의 형식" 분기는 검증하지 않는다 (조치 1) |
| 품질 탭 / 인용 계약 검사가 꺼진 턴 **(신규)** | 충족 | `0036:74` · 테스트 `apps/api/tests/test_control_router.py:859-864,921-922`. 위 B, C 실행으로도 확인 |
| 품질 탭 / 측정 건수를 모르는 응답 **(신규)** | 충족 | `apps/dashboard/components/ControlRoom.tsx:199,209,715-716,738,741,767,769` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:676-694` (양쪽 필드 삭제, `undefined` 미표시 단언) |
| 품질 탭 / 측정 전 데이터가 일부 섞여 있다 | 충족 | `0036:72-79,100-107`, `ControlRoom.tsx:738` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:624`(4 / 6), `apps/api/tests/test_control_router.py:921-922`(2 / 7). RPC의 수치는 위 A 실행으로 확인 |
| 품질 탭 / 측정된 데이터가 하나도 없다 | 충족 | `ControlRoom.tsx:741-742,769-770` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:642,696` |
| 품질 탭 / editor가 품질 탭을 연다 | 충족 | `apps/api/src/api/routers/control.py:570-577`, `ControlRoom.tsx:726-808` · 테스트 `apps/api/tests/test_control_router.py:937`, `apps/dashboard/tests/ControlRoom.test.tsx:452` |
| 품질 탭 / viewer가 품질 탭을 연다 | 충족 | `0036:95,117,141` · 테스트 `apps/api/tests/test_control_router.py:944-946`, `apps/dashboard/tests/ControlRoom.test.tsx:504,696`. viewer 측정 1건은 위 A 실행으로 확인 |
| 품질 탭 / 비멤버의 요청 | 충족 | `0036:58-61` · 테스트 `apps/api/tests/test_control_router.py:915`, `apps/api/tests/test_tenant_isolation_full_path.py:649` |
| 품질 탭 / 집계할 데이터가 없다 | 충족 | `ControlRoom.tsx:718-725` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:537` |
| 품질 탭 / 멤버가 지표의 기준을 확인한다 | 충족 | `ControlRoom.tsx:735,762-764,798` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:707` |
| 리스크 탭 / editor가 대기 제안을 처리한다 | 충족 | `ControlRoom.tsx:658-695` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:733` |
| 리스크 탭 / viewer가 리스크 탭을 연다 | 충족 | `ControlRoom.tsx:697` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:822,852`, `apps/worker/tests/test_wiki_proposals.py:159-160` |
| 리스크 탭 / 비멤버의 요청 | 충족 | `apps/api/src/api/routers/control.py:607-618` · 테스트 `apps/worker/tests/test_wiki_proposals.py:132` |
| 리스크 탭 / 멤버가 지표의 기준을 확인한다 | 충족 | `ControlRoom.tsx:643,651`, 집계 기준 `supabase/migrations/0034_control_risk_tab.sql:47-51,53,56,58,60` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:822` |

## tasks.md 인수 조건 판정

| Task | 결과 | 증거 |
| --- | --- | --- |
| 1.1 측정 건수 표시, 측정 데이터만 집계 | 충족 | 위 표 |
| 1.1 기록 없음 또는 형식 오류 시 측정 기록 없음, 조회 실패 없음 | 동작 충족, 테스트 부족 | 위 표, 조치 1 |
| 1.1 viewer 본인 측정만, 비멤버 403 | 충족 | 위 표 |
| 2.1 묶음별 기준 표시, viewer 버튼 없음 | 충족 | 위 표 |
| 3.1 `stack.md` 표기 | 충족 | `docs/reference/stack.md:54,77-86`, `migration list --linked` 결과와 일치 |
| 3.1 운영 적용 순서 | 충족 | `docs/reference/stack.md:86`, `0036:12-13`, `design.md`의 위험 항목이 모두 `0036`, API, 대시보드 순서로 일치 |
| 3.1 백필 문서 | 충족 (문서 내용 기준) | `docs/ops/wiki-evidence-backfill.md:4-5,12-14,44,81,150-177`. 3.4절 제목이 1절의 위임과 일치한다. 기록된 건수와 운영 실측의 일치는 운영 DB를 조회하지 않아 확인하지 않았다 |

## 조치가 필요한 항목

1. **확장된 형식 오류 시나리오의 자동 테스트가 없다** — `measured`의 네 조건(`0036:73-77`) 중 `violations` 배열, `repair_attempted` 불리언, `repaired` 불리언 조건을 지워도 라우터 테스트가 통과한다.
   - 근거 Scenario: "답변 턴의 품질 기록이 없거나, 객체가 아니거나, **위반 목록과 수리 여부의 형식이 유효하지 않다** … 측정 건수에서 제외되며".
   - 원인: 미측정 시드는 `{"violations": "조작", ...}`, `"조작"`, `{}`, `off`, JSON null이다(`apps/api/tests/test_control_router.py:849-865`). 모두 `mode`가 없거나 `off`이거나 객체가 아니어서 앞의 조건에서 탈락한다. 조건을 "객체이고 `mode`가 `shadow`/`enforce`"로 줄여 평가해도 다섯 시드의 결과가 전부 같음을 로컬에서 확인했다. 특히 `{"violations": "조작", ...}`는 형식 검사를 시험하는 것처럼 보이지만 실제로는 `mode` 누락으로 탈락한다.
   - 영향: 현재 동작은 맞다(위 B 실행). 하지만 이 조건들은 격리 리뷰 r1의 지적 2를 해결한 코드이고, 지워져도 아무 테스트도 실패하지 않는다. `tasks.md` 1.1이 `- [x]`이므로 `/opsx:apply`가 금지하는 미검증 완료에 해당한다.
   - 제안: `mode: "enforce"`를 유지하고 한 필드만 깨뜨린 시드를 추가해 `measured_turns`가 그대로 2인지 단언한다. 최소 세 건이다. `violations`가 문자열, `repair_attempted`가 비불리언, `repaired`가 비불리언. 기존 `{"violations": "조작", ...}` 시드에도 `mode`를 넣으면 그 의도가 살아난다. 이때 `turns` 기대값도 함께 올려야 한다.

## 참고 (판정에 영향 없음)

1. **`design.md` Context와 D2의 불일치** — Context 첫 문단은 아직 "답변 턴은 `quality`가 객체인지로 측정 여부를 판별할 수 있지만"이라고 쓰는데, D2는 "객체 여부만으로는 판별할 수 없다"고 쓴다. 코드와 스펙은 D2와 일치한다. 조치 1을 고칠 때 함께 고치기 쉽다.
2. **`proposal.md`의 "기존 필드의 이름과 의미는 유지한다"** — 같은 문서가 위반 지표를 측정된 데이터의 값으로 재정의하고, 실제로 `ask.fallback` 등의 값이 측정 턴으로 좁아졌다. 이름만 유지된다. 스펙은 올바르다.
3. **`tasks.md` 1.1의 Given** — 새 시나리오 2건(`off`, 필드 없는 응답)이 인수 조건에 적혀 있지 않다. 판정 기준은 delta spec이고 둘 다 구현됐으므로 범위 축소는 아니다.
4. **r1 참고에서 넘어온 항목** — 한 경로만 비었을 때의 `이 기간의 답변이 없습니다` 안내(`ControlRoom.tsx:703-711`, 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:661`)는 여전히 시나리오로 명문화되어 있지 않다. 승인 반영과 거부의 기간은 여전히 제안 생성 시각 기준이다(`0034:58,60`). 키 없음과 `control_report` null의 자동 테스트 부재도 그대로이나, 이 경우는 어느 조건을 지워도 결과가 바뀌지 않아 조치 1과 성격이 다르다.

## 판정 근거

14개 시나리오의 동작은 모두 코드 경로와 직접 실행으로 확인됐고, 스펙 모호성이나 범위 이탈은 없다. 다만 이번 라운드에서 넓어진 형식 오류 시나리오의 핵심 분기를 지키는 자동 테스트가 없다. 스펙을 고칠 필요 없이 테스트 시드만 추가하면 해결되므로 `blocked`가 아니라 `needs_fix`다. 리뷰 게이트의 최대 라운드는 3이며 이번이 2라운드다.
