# Vercel 배포 기록

- 배포 일시: 2026-08-13
- 방법: Vercel CLI (`vercel --prod`), GitHub 연동 없이 CLI 업로드 방식
- 결과: `apps/dashboard`(Next.js 15.5.22)가 Vercel Production에 배포됨

## 프로젝트 구성

| 항목 | 값 |
| --- | --- |
| Vercel 프로젝트 | `dashboard` (`kanzimans-projects` 팀) |
| Project ID | `prj_gaIvrK1CQ377b2NK5wGfbPVtGoeV` |
| Root Directory | `apps/dashboard` |
| "Include files outside the Root Directory" | Enabled |
| Production 도메인 | https://dashboard-zeta-six-33a27nwo93.vercel.app |

## 모노레포 빌드 함정 (실측)

`app/globals.css`는 `@import "../../../docs/design-systems/design-tokens.css"`로 리포 루트의
공유 디자인 토큰을 참조한다(`CLAUDE.md`: 이 파일은 건드리지 않는다는 결정 유지, `06-CONTEXT.md`
canonical ref). 로컬 빌드는 전체 모노레포가 디스크에 있어 항상 성공하지만, Vercel에 처음
CLI로 배포했을 때는 실패했다:

```
Error: Can't resolve '../../../docs/design-systems/design-tokens.css' in '/vercel/path0/app'
```

**원인**: `apps/dashboard` 안에서 `vercel link`/`vercel --prod`를 실행하면 CLI가 그 디렉터리만
업로드 스코프로 잡는다(`/vercel/path0` = `apps/dashboard`). Root Directory 프로젝트 설정의
"Include files outside the Root Directory in the Build Step" 토글은 **Git 연동 배포**(Vercel이
전체 저장소를 클론하는 경우)에만 적용되고, CLI 업로드 배포에는 영향이 없다 — 토글을 켠 뒤
`apps/dashboard`에서 재배포해도 동일하게 68개 파일만 업로드되며 재현됨을 확인했다.

**해결**: 저장소 루트에도 `.vercel/project.json`을 만들어 같은 프로젝트에 링크하고
(`vercel project update dashboard --root-directory apps/dashboard`로 프로젝트의 Root Directory를
`apps/dashboard`로 명시적으로 설정), 저장소 **루트에서** `vercel --prod`를 실행했다. 이러면 CLI가
전체 저장소(1,178개 파일, `docs/` 포함)를 업로드하고, Root Directory 설정에 따라 `apps/dashboard`
안에서 `pnpm install`/`pnpm run build`를 실행한다. 이 조합으로 빌드가 성공했다.

**향후 재배포 시**: 반드시 저장소 루트(`/Users/zorba/projects/NexusWiki`)에서 `vercel --prod`를
실행할 것 — `apps/dashboard` 안에서 실행하면 다시 같은 방식으로 실패한다.

## 환경변수 (Production, `NEXT_PUBLIC_` 접두 — 클라이언트 노출 전제로 안전)

- `NEXT_PUBLIC_SUPABASE_URL` — Supabase Cloud 프로젝트 URL
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` — `sb_publishable_` 키 (`sb_secret_` 키는 여기 넣지 않음 — RLS 우회 위험, worker 전용)
- `NEXT_PUBLIC_API_URL` — Railway `api` 서비스 공개 도메인(`https://api-production-44b4.up.railway.app`)

## 검증

- 배포 상태: `readyState: READY`, `target: production`
- `curl -I https://dashboard-zeta-six-33a27nwo93.vercel.app/login` → HTTP 200
