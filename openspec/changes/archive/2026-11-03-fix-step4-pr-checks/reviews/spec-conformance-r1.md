# Spec Conformance 리뷰 — fix-step4-pr-checks r1

- 판정: pass
- 대상: `7d2a985` 이후 작업 트리의 승인·적용 통합 테스트 이동 및 dashboard 로컬 폰트 로딩 변경
- 일시: 2026-11-03T09:56:29+09:00
- 기준: `skip_specs: true`인 이 change의 proposal·design·tasks, `openspec/specs/tenant-data-isolation/spec.md` 정본. 제품 계약을 추가하지 않으므로 변경 목적과 기존 계약의 보존 여부를 대조했다.

## 시나리오 및 인수 조건 판정

| Requirement / Scenario 또는 인수 조건 | 결과 | 증거 |
| --- | --- | --- |
| 특권 처리 경계 / 요청 처리 컴포넌트가 특권 접근을 시도한다 | 충족 | `apps/worker/tests/test_wiki_proposals.py:20`의 특권 DB import가 worker 영역으로 이동했다. SEC-03의 대상 트리 `scripts/ci_check_service_usage.sh:24`, 탐지식 `:32`, 위반 시 실패 `:74`는 HEAD 대비 변경이 없다. 검사 예외·동적 import 우회를 추가하지 않았다. |
| 테스트 책임 이동 / 검증 수와 의미를 보존한다 | 충족 | 이동 전 `HEAD:apps/api/tests/test_wiki_proposals.py`와 현재 `apps/worker/tests/test_wiki_proposals.py`의 AST 비교에서 **13개 함수, 테스트 6개가 모두 동일**하고 변경·추가·누락 함수가 0개다. 테스트는 권한 `:104`, 본문 비노출 `:132`, 제안 업서트 `:176`, 거부 `:201`, 반복 적용·어휘 색인·개정 `:221`, 개정 멱등성과 멤버 읽기 `:290`을 유지한다. |
| 테스트 책임 이동 / 단독 실행과 루트 수집이 가능하다 | 충족 | `apps/worker/tests/test_wiki_proposals.py:14`가 로컬 접속 정보를, `:15`~`:18`이 네 픽스처를 명시적으로 재사용한다. 로컬 전용 보호·정리 구현은 `apps/api/tests/conftest.py:64`, `:191`, `:211`, `:228`, `:435`를 그대로 사용한다. 부모가 이동 스위트 6개 통과, 위험 정책 테스트 포함 39개 통과 및 루트 1,093개 수집을 확인했다. |
| 기존 격리 검증 / 다른 워크스페이스 요청과 비공개 본문을 거부한다 | 보존 | 실행 위치만 바뀌고 함수 본문은 동일하다. 요청은 기존 `authed_client`를 통한 JWT 경로로 보내며 `apps/worker/tests/test_wiki_proposals.py:104`, `:132`가 viewer·비멤버의 승인 거부와 제안 본문 비노출을 검사한다. 워커용 `ServiceDb`는 `:248`의 승인 적용 검증에만 사용한다. |
| 기존 서체의 결정적 빌드 / 외부 Google 폰트 요청 없이 기존 서체·변수를 유지한다 | 충족 | `apps/dashboard/app/layout.tsx:2`가 `next/font/local`을 사용한다. Inter `:13`, Plus Jakarta Sans `:30`, JetBrains Mono `:36` 모두 고정 패키지 파일이다. 변수와 굵기는 `:14`, `:15`, `:31`, `:32`, `:37`, `:38`에서 보존한다. 패키지 버전은 `apps/dashboard/package.json:16`~`:18`의 5.3.0이며 lockfile도 같은 버전과 integrity를 기록한다. |
| 기존 서체의 결정적 빌드 / 기존 화면과 번들을 검증한다 | 충족 | 부모가 실제 프로덕션 빌드·TypeScript·ESLint 통과를 확인했다. 최종 전체 Vitest는 CLI `--maxWorkers=2 --testTimeout=15000`으로 79개 파일·473개 테스트 모두 통과했다. 패키지 metadata의 family와 weight 축도 기존 서체 및 선언 범위를 포함한다. |

## 범위와 계약 보존 확인

- API·worker 제품 코드, DB 마이그레이션, 보안 탐지 스크립트 및 CI 설정은 이 change에서 수정하지 않았다. 테스트의 위치와 픽스처 import 외 본문을 변경하지 않아 기존 검증을 삭제하거나 약화하지 않는다.
- 폰트는 같은 세 서체의 latin normal 가변 파일로 대체한다. Inter 100~900, Jakarta 700~800, Mono 500~800 선언을 유지하고 기존 변수 클래스·CSS 매핑도 보존한다. Pretendard의 파일·변수·굵기는 그대로다(`apps/dashboard/app/layout.tsx:43`).
- 검사와 로컬 실행의 환경 차이는 검증 기록에 공개한다. Windows의 CRLF 때문에 SEC-03 원본을 LF로 정규화한 임시 사본으로 실행했으며 저장소 스크립트 수정이나 예외 추가는 없다. UI 테스트의 15초 제한도 CLI 실행 옵션이고 저장소 테스트 설정을 바꾸지 않는다.
- 무관한 `docs/ref/ref0.png`, `docs/ref/ref2.png` 삭제와 `skills-lock.json`은 검토 범위에서 제외했다.

## 조치가 필요한 항목

없음.

## 검증과 한계

- 리뷰어는 AST를 통해 테스트 본문 보존을 독립 확인했고, 패키지 metadata·layout·lockfile·보안 스크립트의 정적 대조를 수행했다. 요청에 따라 DB·큐 테스트를 추가 실행하지 않았다.
- 부모의 최신 실행 결과: 이동 스위트 6개 및 위험 정책 포함 39개 통과, 루트 1,093개 수집, SEC-03 301개 파일 통과, Ruff·포맷·strict validation·프로덕션 빌드·TypeScript·ESLint 통과.
- 전체 Vitest 최종 결과는 **79개 파일 / 473개 테스트 통과, exit 0, 393.48초**다. 기본 5초 제한 실행의 Windows 타임아웃을 재시도한 결과이며 워커 종료 지연 경고 1건이 있었으나 최종 성공했다.
- 원격 PR CI·Vercel 재실행은 후속 발행 단계다. 이 보고서는 그 원격 결과나 배포·머지 완료를 주장하지 않는다.

## 판정 근거

기존 보안 검사를 보존하면서 잘못 위치한 통합 검증을 worker 책임 영역으로 이동했고, 함수·검증 수·검증 의미를 유지했다. 서체 공급 방식은 고정된 로컬 파일로 바뀌었으나 서체 종류·사용 변수·요청 굵기를 보존하고 실제 빌드와 전체 UI 검증이 통과했다. 미충족 인수 조건이나 제품 계약을 바꾸는 범위 이탈을 찾지 못해 `pass`로 판정한다.
