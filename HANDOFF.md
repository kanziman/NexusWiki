# 🤝 Handoff Document

- **작성 일시**: 2026-08-13 19:30 KST
- **작업 브랜치**: `main`

## 🎯 1. 작업 목표 & 현재 상태

- **목표**: v1.0 마일스톤 아카이브 이후, 실제로 배포하고 실 계정으로 써보면서 발견되는 문제를 그때그때 진단·수정한다 — "배포는 어떻게 해?"에서 시작해 Vercel 대시보드 배포, Railway 환경변수 누락 4건 발견·수정, 위키 상세 페이지 한글 슬러그 라우팅 버그 진단(미수정), 멤버 초대 RPC 마이그레이션 미적용 발견(수정 제안, **사용자 확인 대기 중**)까지 이어진 세션.
- **진행률**: 배포는 완료(dashboard+api+worker+DB 전부 라이브). 발견한 문제 중 3건 해결, 1건 진단만 완료(코드 수정 보류 지시), 1건 원인 확정 후 수정 제안 상태로 세션 종료.

## ✏️ 2. 주요 변경 사항 & 의사결정 (Why)

### Vercel 대시보드 배포 (완료)
- `apps/dashboard`를 Vercel Production에 처음 배포. **반드시 저장소 루트에서 `vercel --prod`를 실행해야 한다** — `apps/dashboard` 안에서 실행하면 `docs/design-systems/design-tokens.css`를 참조하는 `app/globals.css`의 모노레포 바깥 import가 깨진다(Vercel Root Directory 설정을 `apps/dashboard`로 두고 루트에서 배포해야 "Include files outside the Root Directory" 토글이 실제로 먹힘 — CLI 배포는 실행한 디렉터리를 업로드 스코프로 잡기 때문). 근거: `docs/ops/vercel-deploy-record.md`.
- 배포 URL: https://dashboard-zeta-six-33a27nwo93.vercel.app

### Railway 환경변수 누락 4건 (전부 수정·재배포 완료)
실사용 테스트(소스 등록 → 컴파일 → 임베딩 → Ask) 중 순서대로 발견. `/health`만으로는 하나도 드러나지 않았다. 전부 `docs/ops/railway-env-checklist.md`에 통합 기록:

1. **`CORS_ALLOWED_ORIGINS`** — Railway `api`에 아예 설정 안 되어 있었음(코드 기본값이 localhost 전용). Vercel 도메인 추가.
2. **`LLM_MODEL`** — `anthropic/claude-3.5-sonnet`이 OpenRouter에서 완전히 제거된 슬러그. `anthropic/claude-sonnet-4.6`으로 교체.
3. **`EMBED_BATCH_SIZE`** — 코드 기본값 32였는데, `deepinfra/fp32`(bge-m3) provider pin이 ~27~32KB 요청 본문에서 "No endpoints found"로 404. 실측으로 24개(26.9KB)는 통과, 28개(32.1KB)는 실패 확인. `apps/worker/src/worker/settings.py`에서 기본값 8로 하향(커밋 `a40847d`).
4. **`QUERY_EMBEDDING_INTERNAL_TOKEN`/`URL`, `LLM_STREAM_INTERNAL_TOKEN`/`URL`** — api·worker 양쪽에 전부 미설정. worker의 내부 리스너(`__main__.py:95-96`)가 토큰 없으면 아예 기동하지 않는 설계라, 벡터 검색 채널 전체가 `embedding_unavailable`로 죽고 Ask는 항상 "근거를 찾지 못했습니다"만 반환했다. 32바이트 랜덤 토큰 생성 후 api·worker에 동일 값 주입, `QUERY_EMBEDDING_INTERNAL_URL`/`LLM_STREAM_INTERNAL_URL`은 `http://worker.railway.internal:8081`로 설정. 수정 후 Ask 실제 스트리밍 답변 + `[[wiki:...]]`/`[[src:...]]` 인용 마커까지 직접 확인함.

### 진단만 하고 수정 보류 — 위키 상세 페이지 한글 슬러그 404
- **증상**: 위키 목록 5개 중 순수 ASCII 슬러그(`hmg-sso`)만 열리고, 한글이 섞인 나머지 4개는 전부 "페이지를 찾을 수 없습니다".
- **확인한 사실**: DB 데이터 정상(중복 없음, 바이트 단위로 NFC 정규화 일치 확인), 같은 인증 토큰으로 PostgREST 직접 호출 시 정상 반환, `agent-browser`로 실제 로그인 세션에서 재현 확인(네트워크 요청 자체는 정확히 인코딩된 경로로 나감, 서버는 200 반환하지만 렌더링 내용이 "찾을 수 없음"). middleware.ts는 경로를 건드리지 않음, 정적 캐싱도 아님(빌드 로그상 `ƒ` dynamic).
- **의심 지점**: `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx`의 `const { workspaceId, slug } = await params;` — Next.js가 비-ASCII(멀티바이트 UTF-8) dynamic route segment를 프로덕션(Vercel)에서 제대로 디코딩하지 못하는, 알려진 부류의 프레임워크 버그와 정황이 일치. 제안한 수정(미적용): `decodeURIComponent(slug)` 방어적으로 추가.
- **사용자가 명시적으로 "분석만 하고 소스 수정은 하지마"라고 지시** — 코드는 건드리지 않았다. 다음 세션에서 수정 여부 결정 필요.

### 원인 확정, 수정 제안 상태 — 멤버 초대 실패 (세션 종료 시점 미해결)
- **증상**: "초대를 보내지 못했습니다" (제네릭 에러 — `InviteForm.tsx`의 `NW409`/`NW404`/`42501` 어느 것도 아님).
- **원인**: `supabase migration list --linked` 실행 결과 **마이그레이션 `0014`(`workspace_members_list`/`invite_workspace_member` RPC 2종, Phase 6 06-03)가 로컬에만 적용되어 있고 클라우드 프로젝트에는 한 번도 push된 적이 없음**(`0001`~`0013`은 로컬·클라우드 모두 일치, `0014`만 `remote: ""`). PostgREST가 `PGRST202`(함수를 스키마 캐시에서 찾을 수 없음)를 반환하는 걸 직접 RPC 호출로 재현·확정.
- **검토 결과**: `0014`는 새 테이블·RLS 정책 변경 없이 `SECURITY DEFINER` 함수 2개만 추가하는 순수 additive 마이그레이션(파일 헤더 주석에 명시).
- **제안한 수정**: `supabase db push`로 `0014`를 클라우드에 적용. **사용자에게 확인을 요청했으나 `/handoff` 실행으로 세션이 여기서 끊겼다 — 아직 실행하지 않았다.**

### 로컬 개발 환경 재설정 (완료)
- 재부팅 후 `apps/dashboard/.env.local`을 클라우드 값(`NEXT_PUBLIC_SUPABASE_URL`/`PUBLISHABLE_KEY`/`NEXT_PUBLIC_API_URL`)으로 전환 — 로컬 dashboard가 Railway api/worker + 클라우드 Supabase를 그대로 바라보도록. `.env.local` 편집은 권한상 내가 직접 못 해 사용자가 직접 수정, 이후 `pnpm dev` 재시작으로 실제 반영 확인(`agent-browser`로 실제 로그인 요청이 `dajhhwbkfdaqnuenulsb.supabase.co`로 나가는 것까지 확인).
- 클라우드용 테스트 계정 생성 및 워크스페이스 부여 완료 (아래 참고).

### (참고) 병행된 별도 작업 — 내가 하지 않음
- git 로그에 `bf0607d`~`e144a38` 커밋(대시보드 "quiet editorial" 비주얼 리프레시)이 이 세션 작업과 별개로 존재한다. 이 세션에서 검토·작성하지 않았으므로 내용을 보증할 수 없다 — 다음 세션에서 확인 필요.

## 🧪 3. 검증 상태

- **완료된 검증**:
  - Vercel 프로덕션 빌드 성공, `/login` 200 확인
  - CORS preflight 실측 통과 (`access-control-allow-origin` 헤더 확인)
  - 실제 소스 업로드 → 컴파일 → 임베딩 전 과정 클라우드에서 성공 확인 (worker 로그/DB 직접 조회로 job 상태 succeeded 확인)
  - Ask 엔드포인트 SSE 실측 — `meta`→`delta*` 스트리밍 + `[[wiki:w2]]`/`[[src:s5]]` 인용 마커 포함 실제 답변 확인
  - `apps/worker/tests/test_handlers.py`, `test_settings.py` 35개 통과 (EMBED_BATCH_SIZE 변경 후)
  - `dev-test@example.test`(로컬)/`dev-test+1786601699@nexuswiki.test`(클라우드) 양쪽 로그인 실측 확인
- **미검증/미해결 항목**:
  - 위키 상세 페이지 한글 슬러그 404 — 원인은 특정했으나 수정 미적용(사용자 지시로 보류)
  - 멤버 초대 RPC — `0014` push 자체가 아직 실행 안 됨. push 후 실제 초대 왕복까지 재검증 필요
  - 병행된 대시보드 비주얼 리프레시 커밋들의 실제 동작 미확인

## ⚠️ 4. 주의사항 & 남은 작업 (TODO)

- [ ] **최우선**: `supabase db push`로 마이그레이션 `0014`를 클라우드에 적용할지 사용자 확인 받고 실행 (additive-only, 테이블/RLS 변경 없음 — 낮은 위험으로 판단했으나 프로덕션 DB 변경이라 확인 필요했음)
- [ ] `0014` push 후 초대 플로우 실제 왕복 검증 (`InviteForm.tsx` → `NW404`/`NW409`/성공 각 케이스)
- [ ] 위키 상세 페이지 한글 슬러그 라우팅 버그 — `decodeURIComponent(slug)` 수정 적용 여부 결정 후 진행 (현재 코드 미변경)
- [ ] git 로그의 "quiet editorial" 대시보드 리프레시 커밋들 내용 확인 — 이 세션 작업과 충돌/중복 없는지, 실제 배포에 반영됐는지
- **주의사항**:
  - **로컬 vs 클라우드 계정은 완전히 별개 DB다** — `dev-test@example.test`(로컬 전용, `UatVerify-2026!`)와 `dev-test+1786601699@nexuswiki.test`(클라우드 전용, `Nexus748c6c1174f6!Wiki`)를 섞어 쓰면 로그인 자체가 안 됨. `apps/dashboard/.env.local`의 `NEXT_PUBLIC_SUPABASE_URL`이 어느 쪽을 가리키는지가 유일한 판정 기준.
  - **Next.js는 `.env.local`을 부팅 시 한 번만 읽는다** — 파일만 고치고 dev 서버 재시작을 안 하면 예전 값이 계속 쓰인다(이번 세션에 실제로 헷갈렸던 지점).
  - **Vercel 재배포는 반드시 저장소 루트에서** `vercel --prod` — `apps/dashboard` 안에서 하면 모노레포 바깥 `docs/` 참조가 깨진다.
  - `.vercel/`이 저장소 루트와 `apps/dashboard/` 양쪽에 있다(의도적 — 루트에서 배포하되 프로젝트 root directory 설정은 `apps/dashboard`).
  - `/tmp`에 저장했던 테스트 계정 자격증명 파일(`/tmp/nexuswiki-test-creds.txt`)이 재부팅으로 사라졌다 — 앞으로는 `.env.local` 같은 프로젝트 내 위치(gitignore 대상)에 남기거나 이 문서에 직접 기록하는 편이 낫다. 클라우드 테스트 계정 자격증명은 위 주의사항에 이미 적어 뒀다.

## 🚀 5. 다음 세션 재개 안내

다음 세션 시작 시 `/catchup` 스킬을 실행하거나 아래 멘트를 입력하세요:
> "HANDOFF.md 확인하고, 마이그레이션 0014 클라우드 push부터 확인한 다음 남은 작업 이어서 진행해줘."
