# Tenant Isolation 리뷰 — ask-scorecard-refusal-verdict r1

- 판정: pass
- 대상: `git diff` (미커밋 변경, 기준 HEAD 5cda037)
- 일시: 2026-11-08

변경 파일은 `scripts/ask_replay.py`, `apps/worker/tests/test_ask_replay_script.py`, `docs/ops/ask-sample-replay.md` 세 개다. `supabase/`, `apps/api/`, 마이그레이션은 diff에 없다(`git diff --name-only`로 확인).

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 해당 없음 | diff에 클라이언트 생성이나 조회 코드가 없다. 추가된 것은 순수 함수 `is_refusal`과 `verdict` 분기뿐이다. 기존 `scripts/ask_replay.py:528-534`의 service_role 조회는 이번 변경 밖이며 `workspace_id` 필터가 없으면 ValueError를 낸다. |
| A-2 | 신규 테이블 RLS | 해당 없음 | 신규 테이블 없음 |
| A-3 | anon GRANT·정책 | 해당 없음 | DB 변경 없음 |
| A-4 | 워커의 workspace_id 필터 | 해당 없음 | 새 조회 없음. `verdict`는 이미 가져온 행 필드만 읽는다. |
| A-5 | 복합 FK | 해당 없음 | 신규 자식 테이블 없음 |
| B-6, B-7 | 0행→403, 42501→403 | 해당 없음 | API·SQL 변경 없음 |
| C-8, C-9 | 멱등성, jobs 직접 UPDATE | 해당 없음 | 핸들러·jobs 접근 없음. `verdict`는 행에서 매번 재계산하는 순수 함수라 재실행에 안전하다. |
| D-10 | hnsw.iterative_scan | 해당 없음 | 검색 질의 변경 없음 |
| D-11, D-12 | 토크나이저, search_tsv | 해당 없음 | 색인·질의 경로 변경 없음 |
| D-13 | 프롬프트 `str.format` | 통과 | 템플릿을 만들지 않는다. `REFUSAL_STATEMENT`는 상수이고 비교는 `startswith`다. |
| D-14 | 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 | 해당 없음 | 마이그레이션 없음 |

## 조용한 실패 점검 (요청 사항)

- **정확한 거절이 아닌 답이 통과로 새는 경로**: 답할 수 없는 질문은 `status == "no-evidence"` 또는 (`status == "resolved"` 그리고 `is_refusal(answer)`)일 때만 거절로 본다(`scripts/ask_replay.py:155-157`). 숫자를 지어낸 답, 거절 문구가 본문 뒤쪽에만 있는 답, `fallback` 상태는 모두 실패로 남는다. 테스트가 세 경우를 고정한다. 위조 앵커 검사는 거절 판정 뒤에도 유지된다(`:160-163`).
- **답변이 None 또는 빈 값**: `(answer or "").splitlines()`가 None과 빈 문자열을 처리한다. 본문 줄이 없으면 `False`를 돌려주므로 `resolved`이면서 답이 비면 실패다(통과로 새지 않음). 테스트가 None, 빈 문자열, 제목만 있는 답을 확인한다. `no-evidence`는 답 텍스트 없이도 통과하며 기존 동작과 같다.
- **status 비교**: `status`는 `str(row.get("status"))`이다. 값이 없으면 `"None"`이 되어 어느 거절 분기에도 들지 못하고 실패한다. 거절 분기는 `resolved`와 `no-evidence` 두 값만 인정하고, `fallback`이나 error 계열 값은 인정하지 않는다. 비교가 정확 일치이므로 누락된 값 때문에 통과하는 경로는 없다.
- **정답 있는 질문 쪽 회귀**: 해당 분기(`:165` 이하)는 diff에서 바뀌지 않았다.

## 조치가 필요한 항목

없음. 아래는 판정에 영향 없는 참고 사항이다.

1. **알려진 한계, 이미 문서화됨** (심각도: 보통, 문서화됨)
   - 위치: `scripts/ask_replay.py:149-151`, `docs/ops/ask-sample-replay.md`
   - 내용: 거절 문구로 시작한 뒤 이어서 답하는 혼합 답변은 통과한다. 임베딩 일시 실패로 생긴 `no-evidence`도 통과로 센다. 성적표(오프라인 재생 지표)에만 영향이 있고 테넌트 경계나 데이터 손상과는 무관하다.
2. **거절 문구 결합** (심각도: 낮음)
   - 위치: `scripts/ask_replay.py:120-123`
   - 내용: `REFUSAL_STATEMENT`는 `0006_seed_prompts.sql`의 문구를 복제한 상수다. 프롬프트가 바뀌면 정확한 거절이 실패로 세어진다. 방향은 안전한 쪽(거짓 실패)이고 주석에 ⚠️가 있다. 굵은 글씨 제목(`**핵심 답변**`)은 건너뛰지 않아 같은 방향의 거짓 실패가 날 수 있지만, 통과로 새지는 않는다.

## 판정 근거

DB·RLS·API·마이그레이션·검색·프롬프트 조립을 건드리지 않고 재생 스크립트의 순수 판정 함수만 바뀌었다. 새 판정은 `resolved`와 첫 본문 줄의 표준 거절 문구가 모두 맞을 때만 통과시키고, None·빈 값·누락된 status는 모두 실패 쪽으로 떨어진다. 통과로 새는 경로는 문서에 적힌 두 한계뿐이며 둘 다 성적표 지표에만 영향을 주므로 `pass`다.
