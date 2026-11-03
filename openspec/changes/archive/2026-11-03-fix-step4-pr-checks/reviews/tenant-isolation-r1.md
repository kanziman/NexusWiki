# Tenant Isolation 리뷰 — fix-step4-pr-checks r1

- 판정: pass
- 대상: `7d2a9855e5d68cf79763d31f3f6f011af64b9aad` 이후 테스트 이동·dashboard 폰트 로딩·의존성 작업 트리 변경과 해당 change 산출물
- 일시: 2026-11-03T00:56:39Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 제품 요청 경로 변경 없음. 특권 DB import는 API 테스트에서 제거되고 worker 통합 테스트에만 남는다(`apps/worker/tests/test_wiki_proposals.py:20-21`). 동적 import·검사 예외를 추가하지 않는다. |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 테이블·정책 변경 없음. |
| A-3 | anon 신규 GRANT·정책 | 해당 없음 | GRANT·정책 변경 없음. |
| A-4 | 워커의 workspace_id 명시 필터 | 통과 | 워커 제품 코드 변경 없음. 이동한 테스트의 적용 호출은 기존처럼 owner.workspace_id를 전달한다(`test_wiki_proposals.py:251-255`). 실제 헬퍼의 테넌트 필터는 변경하지 않는다. |
| A-5 | 복합 FK | 해당 없음 | DDL 변경 없음. |
| B-6 | 0행 → 403 매핑 | 통과 | 오류 매핑 제품 코드 변경 없음. 기존의 viewer·비멤버 거부, 타 테넌트 제안 식별의 동일 409 검증을 그대로 보존한다(`test_wiki_proposals.py:104-129`). |
| B-7 | 42501 → 403 | 통과 | 기존 403 경계와 viewer 본문 비공개 검증이 보존된다(`test_wiki_proposals.py:104-172`). 오류 렌더러·RPC는 수정하지 않는다. |
| C-8 | 핸들러 멱등성 | 통과 | 제품 핸들러 변경 없음. 두 번 적용 후 본문·개정·상태를 확인하는 테스트와 동일 잡 개정 1건 검증이 그대로 이동한다(`test_wiki_proposals.py:221-267`, `:290-314`). |
| C-9 | jobs 직접 UPDATE | 해당 없음 | 새 jobs 쓰기 없음. 기존 통합 테스트 본문과 제품 큐 함수는 바뀌지 않는다. |
| D-10 | iterative_scan | 해당 없음 | 검색 SQL 변경 없음. |
| D-11 | 토크나이저 일치 | 해당 없음 | 색인·질의 제품 코드 변경 없음. 기존 lexical 색인 단언은 이동된 테스트에 유지된다(`test_wiki_proposals.py:260`). |
| D-12 | search_tsv 생성 컬럼 | 해당 없음 | 스키마 변경 없음. |
| D-13 | str.format | 해당 없음 | 프롬프트 조립 변경 없음. |
| D-14 | 인용 앵커 | 해당 없음 | LLM 컨텍스트·인용 경로 변경 없음. |
| E-15 | 마이그레이션 번호 | 해당 없음 | 신규 마이그레이션 없음. |

## 검증 보존과 조용한 실패 추가 점검

- 이동 전 `HEAD:apps/api/tests/test_wiki_proposals.py`와 이동 후 파일을 읽어 `_PROPOSED_BODY`부터 끝까지 개행 정규화 후 비교했다. 테스트 본문이 동일함을 확인했다. 여섯 테스트를 삭제·축소하거나 성공하도록 완화하지 않았다.
- 기존 API conftest의 LOCAL_STACK과 네 fixture를 명시적으로 가져온다(`apps/worker/tests/test_wiki_proposals.py:14-18`). 로컬 스택 주소 고정·루프백 검사·정리 루틴을 복제하거나 우회하지 않는다(`apps/api/tests/conftest.py:33-64`, `:191-225`, `:228-292`, `:435-457`). 특권 키 사용은 로컬 통합 검증용이며 제품 요청자 JWT 경계에 추가되지 않는다.
- `scripts/ci_check_service_usage.sh`와 `.github`·API·worker 제품 코드·Supabase의 작업 트리 변경이 없음을 확인했다. SEC-03 탐지 허용 목록·탐색 대상·실패 판정은 그대로다.
- 폰트는 세 고정 Fontsource 5.3.0 패키지를 `next/font/local`로 읽는다(`apps/dashboard/package.json:16-18`, `apps/dashboard/app/layout.tsx:12-38`). 기존 Inter·Plus Jakarta Sans·JetBrains Mono CSS 변수와 굵기 범위를 유지하며 인증·데이터 경로를 변경하지 않는다. 새 원격 스크립트·런타임 폰트 요청 경로는 추가하지 않는다.
- 무관한 `docs/ref` 삭제와 `skills-lock.json`은 이 검토 대상에 포함하지 않는다.

## 조치가 필요한 항목

없음.

## 검증 범위와 한계

- 리뷰어는 코드·diff·산출물을 읽고 이동 전후 테스트 본문을 비교했다. 요청에 따라 DB 테스트·제품 코드 수정을 수행하지 않았다.
- 호출자 결과: 이동한 통합 6개와 위험 정책 33개 합계 39개 통과, 루트 1,093개 수집 유지, SEC-03 LF 임시 사본으로 301개 파일 검사 통과 후 사본 삭제, Ruff·ESLint·TypeScript·프로덕션 빌드·포맷·strict validation 통과.
- dashboard 최초 전체 실행은 Windows의 5초 시간 초과로 중단됐다. 이후 CLI `--maxWorkers=2 --testTimeout=15000`으로 재실행한 최종 결과는 exit 0, 79개 파일·473개 테스트 통과(393.48초)다. 워커 종료 경고 1건이 있었으나 최종 실행은 성공했다. 검증 설정이나 테스트 소스를 바꿔 결과를 우회한 것은 아니다.
- CI·Vercel의 외부 재실행 결과는 커밋·push 뒤 별도로 확인해야 한다. 이 보고서가 외부 체크 통과·운영 DB 적용·머지를 주장하지 않는다.

## 판정 근거

테스트 책임 이동은 기존 격리·오류 매핑·멱등성 검증을 그대로 보존하며 특권 모듈을 worker 영역에 둔다. 보안 검사 계약이나 제품 데이터 경계를 약화하지 않는다. 폰트 로딩 변경에도 테넌트 데이터 경로가 없으며 관련 전체 UI 검증과 빌드가 완료됐다. 해당 변경에서 새로운 테넌트 격리·조용한 실패 위반을 찾지 못해 `pass`로 판정한다.
