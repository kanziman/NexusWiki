# Spec Conformance 리뷰 — backfill-wiki-evidence r1

- 판정: pass
- 대상: `HEAD` (`c802b1c`) 및 작업 트리 변경분 (`supabase/migrations/0035_wiki_evidence_backfill.sql`, `apps/worker/src/worker/evidence_backfill.py`, `apps/worker/tests/test_evidence_backfill.py`, `docs/ops/wiki-evidence-backfill.md`, `docs/reference/stack.md`, `.gitignore`)
  - 범위 밖 무관한 작업 트리 변경(검토 제외): `docs/ref/ref0.png`, `docs/ref/ref2.png`, `skills-lock.json`
- 일시: 2026-11-03T11:13:00+09:00

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 기존 본문을 보존하는 근거 백필 / 검증 완료 페이지의 근거 보완 | 충족 | `supabase/migrations/0035_wiki_evidence_backfill.sql:138-148` · `apps/worker/src/worker/evidence_backfill.py:301-357` · 테스트 `apps/worker/tests/test_evidence_backfill.py:62-87,285-333,693-842` |
| 기존 본문을 보존하는 근거 백필 / 후보 생성 | 충족 | `supabase/migrations/0035_wiki_evidence_backfill.sql:11-58` · `apps/worker/src/worker/evidence_backfill.py:97-139,160-228` · 테스트 `apps/worker/tests/test_evidence_backfill.py:195-209,285-312,335-361,693-775` |
| 기존 본문을 보존하는 근거 백필 / 다른 워크스페이스 또는 출처의 후보 | 충족 | `supabase/migrations/0035_wiki_evidence_backfill.sql:44-46,105-120` · `apps/worker/src/worker/evidence_backfill.py:183-184,254-260,287-288` · 테스트 `apps/worker/tests/test_evidence_backfill.py:211-238,410-449,693-783` |
| 검토 결과의 제한된 적용 / 승인하지 않은 후보 | 충족 | `apps/worker/src/worker/evidence_backfill.py:212,276-290,314-323` · `supabase/migrations/0035_wiki_evidence_backfill.sql:138-146` · 테스트 `apps/worker/tests/test_evidence_backfill.py:270-282,313-325,784-833` |
| 검토 결과의 제한된 적용 / 검토 후 내용 변경 | 충족 | `supabase/migrations/0035_wiki_evidence_backfill.sql:6-8,27,33-37,118-134` · `apps/worker/src/worker/evidence_backfill.py:148-153,446-450` · `docs/ops/wiki-evidence-backfill.md:100-105` · 테스트 `apps/worker/tests/test_evidence_backfill.py:363-408,843-890` |
| 검토 결과의 제한된 적용 / 반복 적용과 기존 근거 | 충족 | `supabase/migrations/0035_wiki_evidence_backfill.sql:137-148` · `apps/worker/src/worker/evidence_backfill.py:316-357` · 테스트 `apps/worker/tests/test_evidence_backfill.py:315-325,472-480,483-521,801-832` |
| 검토 결과의 제한된 적용 / 근거가 부족하다 | 충족 | `apps/worker/src/worker/evidence_backfill.py:107-127,212,314-315` · `docs/ops/wiki-evidence-backfill.md:47-49` · 테스트 `apps/worker/tests/test_evidence_backfill.py:335-361,726-842` |
| 검토 결과의 제한된 적용 / 배치 일부가 유효하지 않다 | 충족 | `supabase/migrations/0035_wiki_evidence_backfill.sql:71-146` · `apps/worker/src/worker/evidence_backfill.py:244-290` · 테스트 `apps/worker/tests/test_evidence_backfill.py:211-238,363-408,410-449` |
| 검토 결과의 제한된 적용 / 검토와 적용 사이의 동시 변경 | 충족 | `supabase/migrations/0035_wiki_evidence_backfill.sql:61,94-102,104-135` · 테스트 `apps/worker/tests/test_evidence_backfill.py:650-690` |
| 검토 결과의 제한된 적용 / 일반 사용자와 익명 역할 | 충족 | `supabase/migrations/0035_wiki_evidence_backfill.sql:154-161` · 테스트 `apps/worker/tests/test_evidence_backfill.py:451-472` |

## Task 인수 조건 및 불변 조건 대조 요약

- **Task 1.1 (`export` 및 읽기 전용 후보 보고서)**:
  - 50페이지 단위 UUID 커서 순회(`supabase/migrations/0035_wiki_evidence_backfill.sql:11-58`, `apps/worker/src/worker/evidence_backfill.py:171-199`), 53페이지 합성 fixture 전수 순회(`apps/worker/tests/test_evidence_backfill.py:335-361`) 확인.
  - 어휘 유사도 0점 후보 포함 결정적 정렬(`apps/worker/src/worker/evidence_backfill.py:79-82,188-190`), HTML 이스케이프 및 CSP(`apps/worker/src/worker/evidence_backfill.py:97-139`, `apps/worker/tests/test_evidence_backfill.py:195-209`) 확인.
  - 저장소 내부 출력 경로 `.local/evidence-backfill/` 제한 및 `.gitignore` 등록(`.gitignore:44`, `apps/worker/src/worker/evidence_backfill.py:85-94`, `apps/worker/tests/test_evidence_backfill.py:247-250`) 확인.
- **Task 2.1 (`validate` · `apply` 및 원자적 추가)**:
  - 로컬 파일 해시·스키마·중복 키·workspace·좌표 유효성·500쌍 상한 사전 검증(`apps/worker/src/worker/evidence_backfill.py:50-72,230-298`, `apps/worker/tests/test_evidence_backfill.py:211-244,523-568`) 확인.
  - 원문 → 페이지 → 청크 UUID 오름차순 `FOR SHARE` 잠금 및 토큰 재검증(`supabase/migrations/0035_wiki_evidence_backfill.sql:94-135`), 동시 수정/삭제 경합 테스트(`apps/worker/tests/test_evidence_backfill.py:650-690`) 확인.
  - DB 커밋 후 결과 파일 쓰기 실패 시 롤백으로 오보고하지 않는 `committed_but_result_write_failed` 분리(`apps/worker/src/worker/evidence_backfill.py:352-356`, `apps/worker/tests/test_evidence_backfill.py:599-625`) 확인.
- **Task 3.1 (운영 절차 문서 및 End-to-End 검증)**:
  - 합성 워크스페이스 기반 부분 승인·미확정 보존·품질 집계(`control_quality_snapshot`)·stale 재검토·본문/비밀 비노출 검증(`apps/worker/tests/test_evidence_backfill.py:693-894`) 및 운영 절차서(`docs/ops/wiki-evidence-backfill.md:1-146`), 기술 스택 참조(`docs/reference/stack.md:54,85`) 반영 확인.

## 조치가 필요한 항목

없음 (미충족 항목 0건).

## 판정 근거

`openspec/changes/backfill-wiki-evidence/specs/wiki-compilation/spec.md`의 두 Requirement와 10개 Scenario, 그리고 `tasks.md`의 3개 Task 인수 조건이 모두 SQL 마이그레이션(`0035_wiki_evidence_backfill.sql`), 워커 CLI(`evidence_backfill.py`), 회귀 테스트(`test_evidence_backfill.py`), 운영 문서(`docs/ops/wiki-evidence-backfill.md`)로 빠짐없이 구현·검증되었으며 조용한 범위 축소나 스펙 밖 동작이 없다.
