# 검증 기록

## 기준선

- 독립 worktree: `/private/tmp/nexuswiki-evidence-research`, 기준 HEAD `5dded7b`.
- 독립 스택: `NexusWikiReplay`, 546xx, API OFF 8031 / ON 8032. 주 작업의 544xx와 분리했다.
- 합성 문서 8개를 한 번 수집해 위키 13쪽을 만들었다. 수집 비용 $0.233546.
- 고정 fixture: `scripts/fixtures/evidence_research.v1.json`이 기존 30문항에 전용 12문항을 추가한다.
- 첫 OFF 실측: 42/42 실행, 38/42 통과, 위조 인용 0. 전체 호출 비용 $1.203720, 총 지연 p50 9.862초 / p95 18.883초.
- 원본 기록: `/private/tmp/nexuswiki-research-eval/off-1.json`. 자격증명이 든 state 파일과 원문·임베딩 snapshot은 공개 export 대상이 아니다.
- 첫 OFF의 기존 요약 `model`은 임베딩을 함께 집계하면서 `BAAI/bge-m3`를 선택한 계측 표시 오류가 있다. 실제 답변 모델은 실행 환경의 `anthropic/claude-sonnet-4.6`이며 `conditions.model`에 기록됐다. 이후 계측은 kind로 답변 모델을 구분한다. 비용·토큰은 의도대로 임베딩을 포함한 전체 값이다.
- 실측은 커밋 전 작업트리에서 수행한다. 기록의 revision은 기준 HEAD이며 측정한 변경이 그 커밋에 포함됐다는 뜻이 아니다. 첫 OFF API는 main에 평가 계측만 추가한 상태로 시작해 전체 기준선이 끝날 때까지 재시작하지 않았다.

## 구현 검증

- 관련 core·API·검색·도구·LLM·회계·eval 테스트 455개 통과, 선택적 DB 테스트 4개 skipped.
- 대시보드 전체 테스트 493개 통과, typecheck·lint 통과.
- ruff 및 diff 공백 검사, change strict validation 통과.
- 프로덕션 빌드에서 평가 페이지와 JSON 다운로드의 정적 생성 확인. 브라우저에서 데스크톱·390px 모바일, 전용 12문항 필터 및 상세 펼침 확인.
- 정상 3쌍 재실측 뒤 최종 검증을 새로 실행한다. (2026-11-08 사용자 비용 절감 요청으로 1쌍으로 축소)

## 최종 측정 (2026-11-09)

판단 스트림 소비 수정(설계 D2 추가 결정) 뒤 같은 수집 결과에서 OFF/ON 1쌍을 새로 측정했다. 실행 지문 `dfda4a4d582ec5f389ba03986d19ef3241aab1973c34d92628fcba951efa2d08`, 모델 `anthropic/claude-sonnet-4.6`, 두 기록의 조건 해시가 일치한다.

| 항목 | OFF | ON |
| --- | --- | --- |
| 통과 | 39/42 (실패 q01·q03·r11) | 39/42 (실패 q01·q04·r11) |
| 전체 비용 | $1.220335 | $2.030962 (+66.4%) |
| 총 지연 p50 / p95 | 10.908초 / 20.973초 | 12.914초 / 22.156초 |
| 측정 장애 · 위조 인용 | 0 · 0 | 0 · 0 |

- ON 판단: 충분 40, 검색 1(q30, OFF에서도 통과), 판단 실패 1(q28, `incomplete_decision`). q03·q04의 통과 변화는 두 문항 모두 검색 0회라 재검색 효과가 아니라 답변 편차다.
- 복구 대상(첫 문맥에 기대 문서 전체가 없던 전용 문항)이 0건이라 복구율은 미측정(null)이다.
- 채택 판정 `adopted=false`. 미충족은 답변 복구·전체 통과 증가·비용 상한(50%) 세 항목이다. 반복 안정성은 미측정이다.
- 실제 지출: 재생 DB `usage_events` 기준 220회 호출 $3.309429(2026-11-08 23:16:26Z~23:53:39Z). q28 단일 점검 $0.058130, r07에서 중단된 ON 부분 실행, 재개분을 모두 포함한다.
- ON 중단과 재개: r07에서 OpenRouter 크레딧 소진(공급자 402)으로 중단됐고, 충전 뒤 같은 서버·지문에서 r07~r12만 재개했다. 이 402는 워커가 응답 헤더를 보낸 뒤 공급자를 호출하는 기존 구조 때문에 연결 끊김으로 전달된다. Ask 스트리밍 전체의 기존 문제라 이 change 밖에서 다룬다.

원본은 Git 밖 `.worktrees/research-fix-20261109/`(사본 `/private/tmp/research-fix-20261109/`)에 있다.

| 파일 | sha256 |
| --- | --- |
| `off-1.json` | `b1d41336ad29dc4841af50c1263c4981c9c80fef9bdac4ff4688fd97fb4d52fc` |
| `on-1.json` | `0dcd112682dcea316d052e8c0b748a1d612a402d0ee45d5174a6d3fb1c590240` |
| `on-1.partial.json` | `939280b6c5f5c6ff5d2422b84d899b0fec5c05b4b4ec14665cdd0e353071e91e` |
| `probe-q28.json` | `d78f0a8e2b17104f0cff435a0fdf50d5454fbada8220c8c270db2b85fabd02e9` |
| `logs/evaluation-runtime.json` | `75696156f9cd826670f771fa2d3aa4e476d518c49c1f6932846af80a1de49ee3` |

공개 사본 `apps/dashboard/content/evidence-research.json`을 이 쌍의 export로 교체했다. 행 필드 집합은 이전 공개 사본과 같다. 쇼케이스 컴포넌트 테스트 3개·typecheck·lint가 통과했다.

수정 검증: 판단 무효 시 스트림 소비 테스트 2개를 추가했고, 수정을 되돌리면 두 테스트가 실패함을 확인했다. API·워커·core 테스트 1187개 통과, 19개 실패는 로컬 544xx DB에 마이그레이션 0035·0036이 적용되지 않은 환경 문제다(백필 함수 부재, control 품질 집계). 최종 검증은 4.1에서 새로 실행한다.

## 최종 검증과 리뷰 (4.1, 2026-11-09)

- 로컬 544xx DB에 미적용이던 마이그레이션 0035·0036을 적용한 뒤 새로 실행했다. API·워커·core 테스트 1206개 통과·1개 skip, 대시보드 테스트 493개·typecheck·eslint 통과, `ruff check apps packages`·format 통과, change strict validation 통과. `ruff check .`의 43건은 이 change가 건드리지 않은 벤치마크 스크립트 2개의 기존 오류이며 CI 검사 범위 밖이다.
- spec-conformance-reviewer r1 `needs_fix`(공개 페이지의 3쌍 고정 분모·선택지, 유효 결과 렌더링 테스트 부재, 평가 재개 거부 테스트 부재, 재검색 거부의 오류 턴 테스트 부재) → 코드·테스트 수정 → r2 `pass`. 수정 뒤 관련 테스트 677개·대시보드 495개·typecheck·eslint·strict validation을 다시 통과했다. 추가한 테스트는 결함을 되살리면 실패함을 확인했다.
- r2 권고(판정 무관): 공지·필터의 고정 문항 수, 렌더링 테스트의 고정값 단언, 예산 초과 본문 잘림·판단 출력 상한 256 직접 테스트. 근거: `reviews/`.
- tenant-isolation-reviewer는 사용자 요청으로 생략했고 격리 관련 테스트는 위 실행에 포함된다.

## 외부 차단 사유와 재개 지점 (역사 기록)

- ON 1차 q27의 최종 답변 공급자 요청이 HTTP 403으로 실패했다. 키 상태 조회에서 한도 $5, 잔여 한도 0을 확인했다. 키 한도는 변경하지 않았다.
- 나머지 반복은 임베딩 장애와 연쇄 rate limit으로 오염됐다. 모든 원본을 보존하고 공개 페이지는 비교를 보류한다. 후속 실행 도구는 첫 측정 장애에서 중단하도록 보강했다.
- 초기 기록에는 모델 출력 상한 등의 실제 서버 설정 manifest가 없다. 새 실행은 serve 스크립트가 생성하는 `evaluation-runtime.json`을 필수로 받아 조건을 검증한다. 따라서 기존 기록의 조건 검증도 완료로 주장하지 않는다.
- 사용자에게 한도 조정 또는 사용 가능한 키 제공을 요청했다. 한도 확보 뒤 동일 수집 결과에서 새 디렉터리로 정상 OFF/ON 3쌍을 실행한다. 재수집하지 않는다.
- task 1.1·3.1·4.1·4.2는 미완료다. spec 리뷰·스펙 동기화·archive·커밋·push·PR·배포는 수행하지 않았다. 이슈는 모두 열려 있다.
- 재실행 명령: `docs/ops/evidence-research-eval.md`. 로컬 페이지 미리보기는 3032 포트에서 실행 중이며 평가 API와 워커는 중지했다. Supabase 평가 스택·state·문서 스냅샷은 보존했다.

## 리뷰 범위

사용자 명시 요청으로 tenant-isolation-reviewer는 생략한다. 권한 인자 주입 거부·멤버십 회수·동일 UserDb 및 workspace 사용·기존 격리 관련 테스트는 유지한다. spec-conformance-reviewer는 최종 구현 후 수행한다.
