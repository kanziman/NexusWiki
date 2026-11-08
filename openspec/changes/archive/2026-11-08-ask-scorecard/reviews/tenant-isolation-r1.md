# Tenant Isolation 리뷰 — ask-scorecard r1

- 판정: pass
- 대상: `git diff` 미커밋 변경 (기준 HEAD c97d3b3, 브랜치 feat/ask-scorecard)
- 일시: 2026-11-07

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 해당 없음 | 변경은 `scripts/ask_replay.py`(로컬 도구)뿐. API·앱 코드 변경 없음. `ask_messages` 조회는 요청자 토큰(`token=token`, `ask_replay.py:676`) |
| A-2 | 신규 테이블 RLS | 해당 없음 | 마이그레이션 변경 없음(최대 번호 0036 그대로) |
| A-3 | anon GRANT/정책 | 해당 없음 | SQL 변경 없음 |
| A-4 | service_role 코드의 workspace_id 필터 | 통과 | `_select`(`ask_replay.py:481-503`)가 `workspace_id` 키 없으면 `ValueError`. 신규 `usage_events` 조회(`:684-694`)는 `workspace_id=eq.<state>`와 `trace_id`를 모두 건다. 기존 호출부(jobs, wiki_pages, usage_events 합계)도 전부 필터 포함. 루프백 아닌 주소는 `assert_loopback`이 거부 |
| A-5 | 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6/7 | 0행→403, 42501→403 | 해당 없음 | API 변경 없음 |
| C-8 | 멱등성 | 해당 없음 | 워커 핸들러 변경 없음. `append_scorecard`는 추가 전용 로컬 파일 기록 |
| C-9 | jobs 직접 UPDATE | 통과 | jobs는 SELECT만 |
| D-10~12 | 검색 설정·토크나이저·생성 컬럼 | 해당 없음 | 검색 코드 변경 없음 |
| D-13 | str.format | 통과 | HTML은 `__DATA__`를 `str.replace`로 치환. 템플릿에 format 없음 |
| D-14 | 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음. `verdict`는 `fabricated_anchor_count`·`dual_citation_rate`를 읽기만 함 |
| E-15 | 마이그레이션 번호 | 해당 없음 | 신규 없음 |

## 유출 점검 (요청 사항)

- 성적표 줄(`scorecard_line`, `:260-285`)은 label, git_sha, model, 날짜, 집계 수치, 결과 파일 상대 경로만 담는다. 질문·답변 본문, 키, 이메일, credential, workspace_id 없음.
- `LOCAL_SERVICE_KEY`/`credential`은 `state.json`에만 있고 결과 JSON·HTML로 흐르는 경로가 없다.
- HTML 데이터는 `_json_for_script`가 `<` `>` `&` U+2028/2029를 이스케이프하고, 화면 코드는 `textContent`만 써서 답변 본문의 스크립트 주입이 막힌다.
- HTML 상세에는 결과 파일의 `answer`가 `<details>`로 실린다(합성 샘플 답변, 설계 의도). 비밀은 아니다.

## 조치가 필요한 항목

없음. 참고(심각도 낮음, 판정 영향 없음):
- `_select`의 가드는 `workspace_id` 키 존재만 확인하고 값이 비어 있는지는 보지 않는다(`ask_replay.py:494`). 현재 호출부는 모두 `state`의 값을 넣으므로 문제없다.
- HTML 상세에 답변 본문이 들어가므로, 합성 샘플이 아닌 데이터를 대상으로 돌리게 되면 HTML을 공유 전에 점검해야 한다. 루프백 전용 가드가 이를 막는다.

## 판정 근거

DB·RLS·API·마이그레이션 변경이 없음을 diff로 직접 확인했다. service_role 조회는 루프백 전용 로컬 스크립트에 한정되고 `_select`가 workspace_id 필터를 강제하며, 요청자 소유 테이블은 사용자 토큰으로 읽는다. 성적표 줄과 HTML에서 비밀·본문 유출 경로는 없다.
