# Supabase Cloud bootstrap 검증 기록

## 선행 상태

### 측정 일시

2026-08-04 07:16:11 KST

### 방법

- Supabase CLI 로그인 세션에서 `.env.local`의 `SUPABASE_URL`과 일치하는 프로젝트를 찾아 리전과 상태를 확인했다.
- `supabase link`를 비대화형으로 실행한 뒤 `supabase migration list --linked`로 로컬·원격 migration ledger를 비교했다.
- `supabase db query --linked`로 `supabase_migrations.schema_migrations`와 `information_schema.tables`를 각각 직접 조회했다.
- `.env.local`의 API 키 두 종류는 값이 아니라 접두 형식만 검사했다.

### 결과

- 대상은 Supabase `ap-southeast-1` 프로젝트이며 상태는 `ACTIVE_HEALTHY`였다. 리전 조건 pass.
- 로컬 migration은 `0001`, `0002`, `0003`, `0004`, `0005`, `0006` 여섯 개이며 원격 열은 모두 비어 있었다.
- push 직전 `supabase_migrations.schema_migrations` 직접 조회는 `테이블 없음`(`42P01`)을 반환했다. 선행 ledger 0행으로 판정, pass.
- `information_schema.tables`에서 `public` 스키마의 `workspaces`, `raw_sources`, `wiki_pages`, `jobs`를 센 결과는 `0`이었다. ledger 없이 스키마만 존재하는 흔적 없음, pass.
- 발급 키는 `sb_publishable_` 및 `sb_secret_` 접두 형식을 사용했다. 실제 키 값은 기록하지 않았다, pass.
- 종합 판정: 상태 A — migration ledger가 비어 있고 대상 public 테이블도 없다.

## SPEC 편차

1. `01-SPEC.md` §Acceptance Criteria가 요구한 확인 시점은 `0005` 작성 전이고, 실제 확인 시점은 `0005` 작성 후 · push 직전이다.
2. 계획 그래프상 이 계획은 `0005`를 저술하는 계획에 의존하므로 SPEC 문구대로는 실행할 수 없다.
3. 순서가 어긋나는 위험은 작성 시점이 아니라 push 시점에 발생하므로, push 직전 확인은 그 사이의 창까지 닫아 보증을 약화하지 않고 강화한다.
4. `0005` 작성 이전 시점의 방증은 `01-CONTEXT.md` §Canonical References의 스카우트 관측(`supabase/.temp/`에 `project-ref` 부재 → CLI link 이력 없음)이며, 위 push 직전 실측과 함께 기록한다.
