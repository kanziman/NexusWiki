## Why

로컬 소스 업로드 진단에서 대시보드 실행 예시가 현재 환경변수 계약과 어긋나고, `workspaces.slug`가 필수가 된 뒤에도 API 통합 테스트 픽스처가 이전 INSERT 형식을 유지하는 회귀가 확인됐다. 실제 업로드 경로를 신뢰성 있게 검증하려면 로컬 설정 예시와 테스트 데이터 생성 경로를 현재 코드·스키마에 맞춰야 한다.

## What Changes

- 루트와 대시보드 전용 환경변수 예시에서 대시보드가 실제로 읽는 `NEXT_PUBLIC_API_URL`과 FastAPI 기본 포트 8000을 사용하고, 대시보드 전용 `.env.local` 준비 경로를 명확히 한다.
- API·worker 통합 테스트 픽스처를 최신 워크스페이스·worker 설정 계약에 맞추고, 검색 벤치마크 시드가 유효한 slug를 생성하며 JSON을 운영체제와 무관하게 UTF-8로 읽고 쓰게 한다.
- 소스 업로드 관련 프런트 단위 테스트와 로컬 Supabase 기반 API 통합 테스트를 새로 실행해 회귀 복구를 확인한다.

## Capabilities

### New Capabilities

없음. 기존 로컬 실행·테스트 경로를 현재 계약에 맞추는 유지보수 변경이다.

### Modified Capabilities

없음. 사용자 동작, API 응답, 데이터 계약은 변경하지 않는다.

## Impact

- `.env.sample`, `apps/dashboard/.env.example`, `README.md`: 로컬 대시보드 공개 환경변수 예시와 실행 안내
- `apps/api/tests/conftest.py`, `apps/worker/tests/test_queue.py`: 로컬 Supabase 통합 테스트용 워크스페이스 생성
- `scripts/generate_retrieval_benchmark_corpus.py`: 검색 벤치마크 워크스페이스 시드
- 관련 대시보드 단위 테스트와 API·worker 통합 테스트
- GitHub umbrella issue: #62
