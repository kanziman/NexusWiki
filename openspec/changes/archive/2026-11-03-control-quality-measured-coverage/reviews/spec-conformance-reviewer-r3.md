# Spec Conformance 리뷰 — control-quality-measured-coverage r3

- 판정: pass
- 대상: 커밋되지 않은 작업 트리 (기준 `212d80a`)와 `git diff`, 미추적 `supabase/migrations/0036_control_quality_measured.sql`
- 제외: `docs/ref/*.png` 삭제, `skills-lock.json`, `openspec/specs/wiki-compilation/spec.md` (r1, r2와 동일)
- 일시: 2026-11-03T05:19:07Z
- 이전 라운드: `spec-conformance-reviewer-r2.md` (`needs_fix`, 조치 1건)

⚠️ **이 판정은 스펙 준수만 다룬다. Ruff는 현재 실패한다.** 새 시드에 붙은 주석 한 줄이 E501이다(아래 "스펙 밖 발견"). `tasks.md`의 완료 게이트에 Ruff가 있으므로 PR 전에 고쳐야 한다.

## 검토 범위

요청대로 r2 이후 달라진 부분만 봤다. 파일 수정 시각 기준으로 r2 이후 바뀐 대상은 `apps/api/tests/test_control_router.py`, `proposal.md`이고, `design.md`도 r2 판정 근거를 읽은 뒤에 바뀌어 함께 봤다. 나머지(`0036`, `ControlRoom.tsx`, `ControlRoom.test.tsx`, delta spec, `stack.md`, 백필 문서)는 r2에서 읽은 뒤 수정되지 않아 r2의 판정을 그대로 잇는다. 나머지 13개 시나리오의 판정 근거는 `spec-conformance-reviewer-r2.md`를 따른다.

## 이번 라운드에서 직접 확인한 것

| 확인 | 결과 |
| --- | --- |
| `uv run pytest` 3개 파일 `-k "control_quality or risk or proposal"` | 8건 통과, 건너뜀 없음 |
| `npx vitest run tests/ControlRoom.test.tsx` | 21건 통과 |
| `openspec validate control-quality-measured-coverage --strict` | 통과 |
| 로컬 함수 본문과 `0036` 파일 비교 | 동일 (실행 후 다시 비교, 롤백으로 원래 본문 유지) |
| `uv run ruff check apps/api/tests/test_control_router.py` | **실패 1건**, `:865` E501 |

전체 pytest, 대시보드 전체 테스트, typecheck, lint는 요청에 따라 실행하지 않았다. 운영 DB에는 접속하지 않았다.

## 새 시드의 조건 약화 검증

로컬 스택의 롤백 트랜잭션에서 `apps/api/tests/test_control_router.py:824-883`의 시드를 같은 값으로 재현했다. `finalize_ask_turn`은 `p_control_report`를 그대로 저장하므로 직접 넣어도 저장값이 같다. 이어서 저장점마다 `measured`의 조건 하나를 지워 함수를 다시 만들고, owner 역할로 호출해 테스트의 기대값(`:938-947`)과 비교했다.

| 약화한 조건 | 전체 | 측정 | 위반 | 인용 없음 | 위조 | 수리 시도 | 수리 성공 | Fallback | 테스트 단언 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 없음 (기준) | 10 | 2 | 2 | 1 | 1 | 2 | 1 | 1 | 통과 |
| `violations` 배열 삭제 | 10 | **3** | 2 | 1 | 1 | 2 | 1 | 1 | **실패** |
| `repair_attempted` 불리언 삭제 | 10 | **3** | **3** | **2** | 1 | 2 | 1 | 1 | **실패** |
| `repaired` 불리언 삭제 | 10 | **3** | **3** | **2** | 1 | 2 | 1 | 1 | **실패** |
| `mode` 삭제 | 10 | **3** | 2 | 1 | 1 | 2 | 1 | 1 | **실패** |
| `quality` 객체 검사 삭제 | 10 | 2 | 2 | 1 | 1 | 2 | 1 | 1 | 통과 |
| 복원 후 기준 | 10 | 2 | 2 | 1 | 1 | 2 | 1 | 1 | 통과 |

- 조건 네 개는 각각 단독으로 단언을 깨뜨린다. r2 조치 1의 지적은 해소됐다.
- 객체 검사 삭제는 등가 변이다. `mode` 조건은 `->>`가 객체에서만 값을 돌려주므로 비객체에서 이미 거짓이다. 어떤 시드로도 구별할 수 없어 테스트 누락이 아니다.
- 한계: 이 비교는 롤백 트랜잭션 안에서 RPC 수치를 기대값과 대조한 것이다. 약화한 함수를 커밋해 pytest를 실제로 돌리지는 않았다. 함수 약화를 커밋하면 다른 세션에 보이므로 피했다. 단언이 `body["ask"]`와의 전체 딕셔너리 비교이고 라우터는 값을 그대로 옮기므로(`apps/api/src/api/routers/control.py:570-577`) 결론은 같다고 판단한다.

## 시나리오 판정 (r2 이후 달라진 항목)

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 품질 탭 / 품질 기록의 형식이 잘못됐다 | 충족 | 구현 `supabase/migrations/0036_control_quality_measured.sql:72-79` · 테스트 `apps/api/tests/test_control_router.py:849-857,865-883,938-947` · 위 약화 검증 |

`tasks.md` 1.1의 "품질 기록이 모두 없거나 형식이 잘못됐을 때"도 같은 근거로 충족한다. 나머지 13개 시나리오와 인수 조건은 r2의 충족 판정을 잇는다.

## 문서 변경 확인

| 항목 | 결과 | 증거 |
| --- | --- | --- |
| `design.md` Context | D2와 일치 | `design.md:3`의 "`quality`의 모드와 형식으로 측정 여부를 판별할 수 있지만(D2)" |
| `proposal.md` | 구현과 일치 | `proposal.md:12`의 "기존 필드의 이름은 유지하되 … 의미를 좁힌다" |

`design.md`의 수정 시각(14:15:19)은 r2 보고서의 작성 일시(14:15:54 KST)보다 앞선다. r2 참고 1은 그 전에 읽은 내용으로 쓴 것이라 작성 시점에 이미 낡았을 수 있다. 현재 문구는 맞다.

## 조치가 필요한 항목

스펙 준수 측면에서는 없음.

## 스펙 밖 발견 (판정 등급에 반영하지 않음)

1. **Ruff E501** — `apps/api/tests/test_control_router.py:865` 주석이 103자로 제한 100자를 넘는다. 이번 라운드에 추가된 줄이다. `tasks.md`의 완료 게이트에 Ruff가 있으므로, 이전에 보고된 Ruff 통과는 더 이상 유효하지 않다. PR 전에 주석을 줄이고 Ruff를 다시 실행해야 한다.
2. **같은 주석의 내용이 일부 틀리다** — "측정으로 세면 위반 건수도 함께 늘어난다"는 수리 플래그 시드 두 건에는 맞지만, `violations`가 문자열인 시드는 `[]`로 대체되어 위반 건수가 2로 그대로다(위 표). 뒷부분을 지우면 1번도 함께 해결된다. 주석만 바뀌므로 스펙 판정은 달라지지 않는다.

## 참고 (판정에 영향 없음, r2에서 이어짐)

1. `tasks.md` 1.1의 Given에 `off`와 필드 없는 응답이 적혀 있지 않다. 판정 기준은 delta spec이고 둘 다 구현됐다.
2. 한 경로만 비었을 때의 안내는 시나리오로 명문화되어 있지 않다.
3. 승인 반영과 거부의 기간은 제안 생성 시각 기준이다(`supabase/migrations/0034_control_risk_tab.sql:58,60`).
4. 기존 `{"violations": "조작", ...}` 시드(`:853`)는 여전히 `mode`가 없어 그 조건에서 탈락한다. 필드별 검증은 새 시드 세 건이 맡으므로 지금은 조작된 기록에서 조회가 실패하지 않는지를 확인하는 역할이다.
5. 백필 문서의 건수가 운영 실측과 같은지는 세 라운드 모두 확인하지 않았다.

## 판정 근거

r2의 유일한 미충족이던 형식 오류 시나리오의 자동 테스트가 추가됐고, 조건을 하나씩 약화했을 때 단언이 실제로 깨짐을 확인했다. 14개 시나리오가 모두 증거와 함께 충족되므로 스펙 준수 판정은 `pass`다. Ruff 실패는 스펙 밖이라 등급에 넣지 않았지만, 고치기 전에는 완료 게이트를 통과할 수 없다.
