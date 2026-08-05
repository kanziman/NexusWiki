# Phase 01: User Setup Required

**Generated:** 2026-08-05
**Phase:** bootstrap-and-ground-truth
**Status:** Complete

Supabase Cloud bootstrap에 필요한 사람 전용 설정은 이번 계획 실행 중 완료했다.

## Environment Variables

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [x] | `SUPABASE_ACCESS_TOKEN` 또는 Supabase CLI 로그인 세션 | Supabase Dashboard → Account → Access Tokens 또는 `supabase login` | 로컬 CLI 세션만; Railway 런타임에는 추가하지 않음 |
| [x] | `SUPABASE_DB_PASSWORD` | Supabase Dashboard → Project Settings → Database → Database password | `.env.local` |

## Dashboard Configuration

- [x] **프로젝트 리전이 Southeast Asia (Singapore) `ap-southeast-1`인지 확인**
  - Location: Supabase Dashboard → Project Settings → General → Region
  - Result: CLI와 프로젝트 설정에서 `ap-southeast-1` 확인

## Verification

```bash
supabase projects list
supabase migration list --linked
```

Expected results:

- 대상 프로젝트가 `ap-southeast-1`에 있다.
- 로컬과 원격 양쪽에 `0001`~`0006`이 표시된다.

실제 secret 값은 이 문서나 저장소에 기록하지 않는다.
