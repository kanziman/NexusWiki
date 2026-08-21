## Context

See `proposal.md` for motivation. 대시보드의 공개 API URL은 `apps/dashboard/lib/env.ts`가 `NEXT_PUBLIC_API_URL` 하나만 읽지만 `.env.sample`은 이전 이름인 `NEXT_PUBLIC_API_BASE_URL`을 안내한다. 대시보드 전용 `.env.example`은 이 키를 Supabase Kong 포트 54421로 잘못 연결하고, 루트 `.env.local`은 `apps/dashboard`에서 실행되는 Next.js가 자동으로 읽지 않는다. 또한 `supabase/migrations/0015_workspace_slug.sql`은 `workspaces.slug`를 `not null`로 전환했지만 API·worker 통합 테스트 픽스처와 검색 벤치마크 시드는 `name`과 `owner_id`만 INSERT한다.

올바른 런타임 값과 유효한 slug를 직접 제공한 네트워크 왕복에서는 Markdown 업로드가 HTTP 202를 반환하고 `raw_sources`와 `jobs(type=parse, status=queued)`를 각각 생성했다. 따라서 API 업로드 구현 자체가 아니라 실행 예시와 테스트 준비 데이터의 계약 이탈을 복구한다.

## Goals / Non-Goals

**Goals:**

- 공개 API URL의 로컬 설정 예시를 대시보드가 실제로 읽는 키와 일치시킨다.
- 워크스페이스를 직접 만드는 통합 테스트·벤치마크 경로가 최신 필수 컬럼을 모두 제공하게 한다.
- 실제 로컬 Supabase 스택에서 소스 업로드 API 테스트가 준비 단계부터 완료까지 실행되게 한다.

**Non-Goals:**

- 업로드 API, RLS 정책, Storage 경로 또는 잡 체인 동작을 변경하지 않는다.
- 사용자의 추적되지 않는 `.env.local` 값이나 클라우드 자격증명을 덮어쓰지 않는다.
- 새로운 로컬 프로세스 관리자나 환경변수 로더 의존성을 추가하지 않는다.

## Decisions

### 현재 공개 환경변수 이름을 예시의 정본으로 사용한다

`.env.sample`의 `NEXT_PUBLIC_API_BASE_URL`을 `NEXT_PUBLIC_API_URL`로 교체하고 `apps/dashboard/.env.example`의 API URL은 FastAPI 기본 주소 `http://127.0.0.1:8000`으로 고친다. README는 루트의 서버 환경과 별개로 대시보드 전용 예시를 `apps/dashboard/.env.local`로 복사하도록 안내한다. 애플리케이션에 이전 이름 폴백을 추가하면 잘못된 배포 설정이 계속 살아남고 fail-fast 계약도 약해지므로 기각한다. 자격증명 값이나 추적되지 않는 개인 설정 파일은 바꾸지 않는다.

### 테스트·벤치마크 워크스페이스 slug는 기존 고유 식별자에서 파생한다

API·worker 픽스처가 이미 생성하는 `test-<hex>`·`queue-it-<hex>` 이름을 slug에도 사용한다. 검색 벤치마크는 결정적 workspace UUID에서 `benchmark-<UUID>` slug를 만든다. 모두 `0015`의 형식·길이 제약을 만족하고 실행 간 충돌을 피한다. DB 기본값이나 테스트 전용 트리거를 추가하는 방식은 운영 스키마 계약을 테스트 편의를 위해 약화하므로 기각한다.

### 기존 통합 테스트를 회귀 검증으로 사용한다

픽스처 준비가 복구되면 `test_sources_router.py`의 파일·텍스트·URL 경계, 중복, 격리, 예산 테스트가 실제 로컬 DB에서 다시 실행된다. 같은 실패를 위한 별도 모의 테스트는 픽스처와 스키마 사이의 실제 불일치를 검출하지 못하므로 추가하지 않는다.

### 벤치마크 JSON 인코딩을 UTF-8로 고정한다

검색 fixture와 결과 record는 UTF-8 JSON이므로 모든 관련 `Path.read_text`·`write_text`에 `encoding="utf-8"`을 명시한다. 플랫폼 기본 인코딩에 맡기면 Windows CP949 환경에서 slug SQL을 생성하거나 golden 결과를 검증하기도 전에 디코딩이 실패한다. fixture를 ASCII로 축소하는 방식은 한국어 검색 corpus의 목적을 훼손하므로 기각한다.

## Risks / Trade-offs

- [개발자의 기존 `.env.local`에 이전 키가 남아 있을 수 있음] → 추적된 예시를 수정하고 기존 개인 파일은 보존한다. 로컬 실행 시 새 키로 옮겨야 함을 완료 보고에 명시한다.
- [공용 actor와 큐 픽스처를 쓰는 다른 통합 테스트에도 상태가 남을 수 있음] → 기존 teardown을 유지하고 관련 API·worker 테스트를 로컬 스택에서 새로 실행한다.

## Migration Plan

DB나 사용자 데이터 마이그레이션은 없다. 예시 키 변경과 테스트 데이터 생성 수정은 각각 해당 파일을 되돌리면 롤백된다.
