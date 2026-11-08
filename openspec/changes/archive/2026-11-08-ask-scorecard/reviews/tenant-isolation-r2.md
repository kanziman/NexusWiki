# Tenant Isolation 리뷰 — ask-scorecard r2

- 판정: pass
- 대상: `git diff` 미커밋 변경 (기준 HEAD c97d3b3, 브랜치 feat/ask-scorecard)
- 일시: 2026-11-07

r1 이후 변경: `scripts/ask_replay.py`의 `_count_kind`, `cited_wiki_count`/`cited_source_count`, `verdict` 이중 인용 기준, usage 조회 select에 `model` 추가.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 해당 없음 | 로컬 전용 스크립트(`assert_loopback`). 앱 요청 경로 변경 없음. `ask_messages`는 요청자 token으로 조회 |
| A-2/A-3/A-5 | 신규 테이블 · anon · 복합 FK | 해당 없음 | 마이그레이션 변경 없음 |
| A-4 | service_role 조회의 workspace_id 필터 | 통과 | `usage_events` 조회에 `workspace_id` + `trace_id` 필터 유지. `_select`가 workspace_id 없으면 `ValueError`. select에 `model`만 추가됨(0027 `model text not null`) |
| B-6/B-7 | 0행 → 403, 42501 | 해당 없음 | API 코드 변경 없음 |
| C-8/C-9 | 멱등성, jobs | 해당 없음 | 워커 핸들러·jobs 접근 없음. 성적표는 append 전용 |
| D-10~12 | 벡터/토크나이저/search_tsv | 해당 없음 | 검색 경로 변경 없음 |
| D-13 | str.format | 통과 | HTML은 `__DATA__` 문자열 치환, `.format` 미사용 |
| D-14 | 인용 앵커 | 통과 | 오히려 `resolved[].kind`로 실제 인용 종류를 센다 |
| E-15 | 마이그레이션 번호 | 해당 없음 | 없음 |

### 요청 중점 확인

- 본문/비밀 유출: 성적표 줄(`scorecard_line`)은 label · sha · model · 수치 · 상대 경로만 담는다. 질문/답변 본문, 키 없음. `_service_headers` 키는 요청 헤더에만 쓰이고 결과·HTML에 실리지 않는다. HTML 상세에는 `answer`가 실리지만 이는 `--out` 결과 파일에 이미 있던 값이며(합성 문서, 로컬 생성물, 문서에 저장소 밖 보관 명시) 새 노출 경로가 아니다. 주입은 `_json_for_script`가 `<`, `>`, `&`, U+2028/2029를 이스케이프하고 화면은 `textContent`만 쓴다.
- None vs 0: `_count_kind`는 `resolved`가 list가 아니면 None, 빈 list면 0으로 구분한다. `verdict`는 둘 다 None이 아닐 때만 답변 단위 기준(0이면 실패)을 쓰고, None이면 문장 기준 `dual_citation_rate > 0`으로 대체해 더 엄격하게(실패 쪽으로) 떨어진다. 인용 이벤트가 없는 resolved 답이 조용히 통과하지 않는다. `fabricated_anchor_count`가 None이면 0으로 취급되나 resolved 답은 인용 개수 None으로 인해 위 대체 기준에서 걸러진다. `keyword_hit is False`만 실패로 보고 None(기대값 없음)은 건너뛰는 것도 의도된 구분이다.

## 조치가 필요한 항목

없음. 참고(보통 이하, 비차단): `build_report_data`가 `scorecard.parent / result_file`을 그대로 열어 `..` 경로를 따라갈 수 있으나, 성적표 파일은 사용자 자신이 소유한 로컬 파일이라 경계를 넘지 않는다.

## 판정 근거

격리·오류 매핑·멱등성·조용한 실패 불변 규칙을 건드리는 새 변경이 없다. service_role 조회의 workspace_id 필터는 유지됐고, 성적표 줄·HTML로 새로 새는 비밀이나 본문이 없으며, 새 필드의 None/0 구분은 실패 방향으로 안전하게 처리된다.
