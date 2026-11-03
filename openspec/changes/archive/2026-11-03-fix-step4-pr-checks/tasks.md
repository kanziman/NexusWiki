# Tasks

Umbrella: https://github.com/kanziman/NexusWiki/issues/207

## 1. 승인·적용 통합 검증의 책임 이동 (#208)

- [x] 1.1 기존 통합 스위트를 워커 영역으로 이동하고 API 로컬 픽스처를 명시적으로 연결한다.
- [x] 1.2 이동한 스위트 단독 실행·루트 수집·Ruff·SEC-03·strict validation으로 검증 보존을 확인한다.

Given 기존 승인·권한·개정·색인 검증, When 워커 테스트로 이동하면, Then 검증 수와 의미를 유지하며 SEC-03는 예외 없이 통과한다.

검증: 이동한 6개 테스트 모두 통과, 루트 1093개 수집 유지, Ruff 전체·변경 파일 포맷·strict 통과. SEC-03 원본을 Windows CRLF만 정규화한 임시 사본으로 실행해 301개 파일 검사 통과 후 사본은 삭제했다. 제품 코드·보안 스크립트 변경 없음.

## 2. 기존 서체의 결정적 빌드 (#209)

- [x] 2.1 기존 세 Google 서체를 버전 고정 Fontsource 파일에서 로드하고 CSS 변수·굵기 범위를 유지한다.
- [x] 2.2 dashboard 전체 테스트·typecheck·lint·프로덕션 빌드로 서체 로딩과 번들을 검증한다.

Given Vercel의 Google 폰트 파싱 실패, When 패키지의 로컬 서체로 빌드하면, Then 외부 폰트 요청 없이 기존 서체·변수를 유지하며 빌드가 통과한다.

검증: 실제 Next 프로덕션 빌드·전체 TypeScript·ESLint·Prettier 통과. 전체 Vitest 79개 파일/473개 테스트 통과(exit 0, 393.48초). Windows의 기본 5초 UI 시간 초과 때문에 CLI `--maxWorkers=2 --testTimeout=15000`으로 재실행했으며 테스트 단언과 저장소 설정은 변경하지 않았다. 종료 지연 경고 1건이 있었으나 최종 성공했다. 승인·적용 통합 및 리스크 회귀도 순차 실행해 39개 통과했다.

## 후속 발행

양 리뷰 게이트 통과 후 아카이브·커밋·push하고 PR #206의 CI·Vercel 결과를 확인한다. 사용자 로그인 후 기존 Vercel 실패 로그를 조회해 원인을 확인했다.
