# Google 로그인 & 가입 PRD

> **문서 상태**: 방향 확정 · 전량 미구현 (2026-08-17). 이전 판은 Google OAuth 를 **이미 구현된 것처럼** 기술했다. 실제로는 이메일+비밀번호가 전부였고 그것이 잠긴 결정(D-01)이었다. 이번에 **D-01 을 번복하기로 결정**했으므로, 이 문서는 "구현 현황"이 아니라 **구현 계약**이다. 여기 적힌 화면·라우트·설정은 §2 를 빼면 **하나도 존재하지 않는다.**
> **기능 영역**: 가입, 로그인, 세션, 워크스페이스 진입·생성
> **라우트**: `/signup` **[미구현]** · `/login` · `/auth/callback` **[미구현]** · `/`
> **연계 프로토타입**: [`nexuswiki-google-auth.html`](nexuswiki-google-auth.html) — §10 참조
> **상위 불변 규칙**: [`PRODUCT-INVARIANTS.md`](PRODUCT-INVARIANTS.md)
> **디자인 토큰**: [`nexuswiki-design-system.css`](nexuswiki-design-system.css)

미구현은 **[미구현]**, 새 마이그레이션이 필요하면 **[마이그레이션 필요]**, 스키마는 있으나 화면이 없으면 **[UI 미구현]** 으로 표시한다.

---

## 0. 이전 판 대조

### A. 여전히 틀린 것 — 방향과 무관하게 고쳤다

| # | 이전 판 | 실제 | 근거 |
| --- | --- | --- | --- |
| 1 | §5.2 `INSERT INTO workspaces (id, name, created_at)` | **실행하면 실패한다** — `owner_id` 가 `NOT NULL` 인데 빠졌다. workspace-home 구판과 **똑같은 오류** | 로컬 DB 재현: `null value in column "owner_id" … violates not-null constraint` |
| 2 | §5.2 2단계 `INSERT INTO workspace_members … 'owner'` | **적으면 안 되는 문장이다.** `workspaces_add_owner_member` 트리거가 이미 한다 | **불변식 §6** |
| 3 | §5.2 3단계 "기본 프롬프트 템플릿 상속 바인딩" | **그런 동작이 없다.** 전역 템플릿 5종은 `workspace_id IS NULL` 로 두고 그대로 읽는다 | DB 실측: `ask 4` · `compile 1` |
| 4 | `URL 슬러그 (slug)`, `/w/[slug]` | **`workspaces.slug` 컬럼이 없다.** 라우트는 `/w/[workspaceId]`(UUID) | DB 실측 0행 · §9-1 |
| 5 | "팀 섹션과 **지식 그룹**을 자유롭게" | 3계층 잔재. `wiki_groups` 는 존재하지 않는다 | **불변식 §1** |
| 6 | `[🚀 워크스페이스 생성 및 시작하기]` | 이모지 금지 | **불변식 §7.2** |
| 7 | `#FFFFFF` · `#E2E8F0` 직접 지정 | 색은 토큰만 쓴다 | **불변식 §7.1** |
| 8 | 라우트 `/login` **또는 `/auth`** | `/auth` 는 없다. 콜백은 `/auth/callback` 이며 별개다 | §4.3 |
| 9 | 문서 헤더 없음 | v2 PRD 공통 헤더 블록 추가 | — |

### B. 미구현이었고, 이제 만들기로 한 것

| 항목 | 이전 판 서술 | 지금 상태 |
| --- | --- | --- |
| Google OAuth 로그인 | 구현된 것처럼 기술 | **[미구현] · 채택 확정** (§1) |
| `/signup` | 로그인과 "단일화"된다고만 함 | **[미구현] · 별도 라우트로 신설 확정** (§3) |
| `/auth/callback` | "OAuth 콜백 처리" 1줄 | **[미구현] · 계약은 §4.3** |
| 셀프서브 워크스페이스 생성 | `OnboardingWorkspaceCard` | **[미구현] · 채택 확정** (§5). 거버닝 스펙 개정 필요 (§8) |

**살아남은 것**: 진입 분기 Case A(1개 → 리다이렉트) · Case B(2개+ → 선택 화면)는 구현과 정확히 일치한다.

---

## 1. 결정 기록 — D-01 번복

로그인 방식은 Phase 6 시작 시 잠긴 결정이었다:

> **D-01**: 로그인은 이메일 + 비밀번호만 지원한다 (매직링크/OAuth 없음). Supabase Auth 기본 흐름을 그대로 사용.
> **Reversibility: costly** — 이후 매직링크/OAuth 를 추가하려면 로그인 폼과 auth 상태 분기를 다시 설계해야 한다.
>
> *(`.planning/phases/06-dashboard/06-CONTEXT.md`. `3e6bcef` 에서 삭제됐으므로 원문은 `git show 3e6bcef^:.planning/phases/06-dashboard/06-CONTEXT.md`)*

**2026-08-17 결정: 번복한다.** 인증은 **Google OAuth 단일 경로**가 된다.

| 결정 | 값 |
| --- | --- |
| 가입 | `/signup` 신설, **Google 계정만** 허용 |
| 로그인 | `/login` 에서 **이메일+비밀번호 폼 제거**, Google 단일화 |
| 가입 후 진입 | **셀프서브 워크스페이스 생성 허용** |

**왜 로그인까지 함께 바뀌는가 — 선택이 아니라 귀결이다.** Google 로 만든 계정에는 비밀번호가 없어 `signInWithPassword` 가 구조적으로 실패한다. "Google 전용 가입 + 비밀번호 전용 로그인"은 성립할 수 없는 조합이다. 둘 다 유지하는 듀얼 경로도 가능했지만, D-01 이 경고한 "auth 상태 분기 재설계" 비용을 두 배로 내면서 얻는 것이 기존 테스트 계정 2개뿐이라 단일화를 택했다.

⚠️ 이 결정은 프로젝트 수명 전체에 걸리므로 `checklists.json > decisions.auth` 에 기록한다. 이 문서는 그 근거를 되풀이하지 않는다.

---

## 2. 현재 구현 — 이번 작업으로 대체되는 것

제거·교체 대상을 명시해 둔다. "왜 이런 코드가 있지"를 다음 사람이 다시 파헤치지 않도록.

| 대상 | 현재 | 조치 |
| --- | --- | --- |
| [`LoginForm.tsx`](../../../apps/dashboard/components/LoginForm.tsx) | 이메일+비밀번호 폼, `signInWithPassword`, 최소 12자 | **삭제** → `GoogleAuthButton` 으로 교체 |
| 오류 문구 `이메일 또는 비밀번호가 올바르지 않습니다.` | 계정 열거 방지(D-12)를 로그인에 적용 | 폼과 함께 제거. **§4.4 가 계정 열거 방지를 승계한다** |
| `window.location.assign("/")` | RSC 소프트 내비게이션 경쟁 조건 회피 | **패턴 유지** — §4.3 이 같은 이유로 이어받는다 |
| `middleware.ts` matcher `["/w/:path*", "/login"]` | `/` 는 미포함 | `/signup` 추가. `/auth/callback` 은 **제외**(§4.3) |
| [`app/page.tsx`](../../../apps/dashboard/app/page.tsx) 0개 분기 | `워크스페이스가 없습니다 — 관리자에게 초대를 요청하세요.` | **§5 온보딩으로 교체** |

### 2.1 유지되는 세션 경계

* **`middleware.ts` 가 쿠키 기록자다**(D-02). 로그인 화면은 인증 상태를 판정하지 않는다.
* ⚠️ Next.js **15.2.3 이상 필수**. CVE-2025-29927 은 `x-middleware-subrequest` 위조로 미들웨어를 건너뛰는데, 이 앱의 테넌트 게이트가 그 미들웨어다.

---

## 3. `/signup` — [미구현]

### 3.1 화면

* `/login` 과 같은 중앙 카드 레이아웃. 제목 `NexusWiki`, 부제 `팀의 살아있는 지식 베이스`.
* CTA **하나**: `Google 계정으로 시작하기`
  * Google 공식 브랜드 'G' 아이콘. **Zero Emoji 규칙의 유일한 예외이며 멀티컬러 공식 SVG 를 그대로 쓴다** — 브랜드 가이드라인 위반이 되므로 단색화하지 않는다.
  * 버튼 외 `--accent` 사용 요소를 두지 않는다(Primary Visual Anchor).
* 하단: 서비스 이용약관 · 개인정보 처리방침 링크 — **§9-3 미해결**(문서 자체가 없다).
* `/login` 으로 가는 링크. 반대 방향도 마찬가지.

### 3.2 가입과 로그인을 왜 나누는가

Google OAuth 는 **기술적으로 두 흐름이 동일하다** — 같은 `signInWithOAuth` 호출이고, Supabase 가 계정 존재 여부에 따라 알아서 만들거나 붙인다. 그럼에도 라우트를 나누는 이유는 두 가지다.

1. **문구가 달라야 한다.** 처음 오는 사람에게는 약관 동의와 "무엇을 만드는 서비스인지"가 필요하고, 돌아오는 사람에게는 방해다.
2. **`/signup` 은 온보딩(§5)으로 이어지고 `/login` 은 진입 분기(§6.1)로 이어진다.** 도착지가 다르다.

⚠️ **다만 라우트가 갈릴 뿐 인증 자체는 하나다.** `/login` 으로 온 신규 사용자도 정상 가입되고, `/signup` 으로 온 기존 사용자도 정상 로그인된다. 어느 쪽도 오류로 처리하지 않는다 — 사용자가 어느 문을 열었는지로 벌을 주지 않는다.

---

## 4. `/login` 개편 — [미구현]

### 4.1 화면

* 이메일·비밀번호 필드와 제출 버튼을 **제거**한다.
* CTA 하나: `Google 계정으로 계속하기`.
* `/signup` 링크.

### 4.2 OAuth 개시

```ts
await supabase.auth.signInWithOAuth({
  provider: "google",
  options: { redirectTo: `${origin}/auth/callback?next=${encodeURIComponent(next)}` },
});
```

* `next` 는 **내부 경로만** 허용한다. `//evil.com` · `https://…` 같은 절대 URL 을 그대로 넘기면 오픈 리다이렉트가 된다. `next.startsWith("/") && !next.startsWith("//")` 로 검증하고, 실패하면 `/` 로 떨군다.

### 4.3 `/auth/callback` — Route Handler

`app/auth/callback/route.ts` 에 Route Handler 로 만든다(페이지 아님).

```ts
const { error } = await supabase.auth.exchangeCodeForSession(code);
// 성공 → redirect(next ?? "/") · 실패 → redirect("/login?error=auth")
```

⚠️ **D-02("`middleware.ts` 가 유일한 쿠키 기록자")에 예외가 생긴다.** `exchangeCodeForSession` 은 세션 쿠키를 **직접 쓴다.** 미들웨어에 위임할 수 없다 — 코드 교환은 1회용 authorization code 를 소비하므로 중복 실행이 곧 실패다. 따라서:

* 콜백 라우트를 **미들웨어 matcher 에 넣지 않는다.** 미들웨어가 먼저 돌면 세션이 없는 상태로 `/login` 리다이렉트가 걸려 코드가 소비되지 못한다.
* D-02 는 "미들웨어가 유일한 기록자"에서 **"OAuth 콜백과 미들웨어, 두 곳만 기록자"** 로 개정한다. 세 번째 기록자를 만들지 않는다.

⚠️ **리다이렉트는 전체 네비게이션으로 끝난다.** `LoginForm` 이 `router.push` 대신 `window.location.assign` 을 쓴 이유(06-01 실측: `@supabase/ssr` 이 막 쓴 쿠키를 RSC fetch 가 앞질러 미인증 렌더가 나옴)가 여기에도 그대로 적용된다. Route Handler 의 `NextResponse.redirect` 는 항상 새 HTTP 요청이므로 이 조건이 발생하지 않는다.

### 4.4 계정 열거 방지 승계

비밀번호 폼이 사라지면서 `이메일 또는 비밀번호가 올바르지 않습니다.` 도 사라진다. **그러나 원칙은 남는다**(D-12).

* 콜백 실패는 원인과 무관하게 **한 문구**로 수렴한다: `로그인하지 못했습니다. 다시 시도해주세요.`
* "이 Google 계정은 등록되지 않았습니다" 같은 구분을 **하지 않는다.** 구분하는 순간 로그인 화면이 계정 등록 여부 조회기가 된다.
* ⚠️ 이 규칙은 **`invite_workspace_member` 의 `NW404` 와 상반돼 보이지만 의도된 차이다.** 초대 폼은 owner 전용 표면이라 노출이 `0014` 에서 판단·수용됐고, 로그인 화면은 누구나 두드릴 수 있다.

---

## 5. 셀프서브 워크스페이스 생성 — [미구현]

### 5.1 진입 조건

`/` 에서 요청자에게 보이는 워크스페이스가 **0개**일 때 렌더한다. 1개·2개 이상 분기는 §6.1 그대로 유지한다.

⚠️ **이 화면이 기존 `관리자에게 초대를 요청하세요` 문구를 대체한다.** 그 문구는 거버닝 스펙이 요구하던 것이라, 교체하려면 스펙을 함께 고쳐야 한다 — §8.

### 5.2 화면

* 환영 문구: Google 프로필의 이름·이메일 표시 (`{name} 님, 환영합니다`).
  * `user.user_metadata.full_name` · `avatar_url` 에서 읽는다. **없을 수 있으므로 이메일 폴백을 반드시 둔다.**
  * ⚠️ 이건 `auth.users` 메타데이터일 뿐 **`workspace_members` 로스터의 표시 이름이 되지 않는다.** 멤버 로스터는 여전히 이메일만 안다(workspace-settings PRD §6-3).
* 폼 필드 **하나**: `워크스페이스 이름` (1–100자, 한글·영문).
  * **URL 식별자(slug) 필드를 넣지 않는다** — 이름에서 자동 생성한다(§9-1). `slug.py` 의 `slugify` 가 충돌을 숫자 접미로 해소하므로 사용자가 고민할 것이 없다.
  * ⚠️ `taken` 에 **기존 `workspaces.slug` 전체**를 넘겨야 한다. 슬러그는 전역 UNIQUE 라 워크스페이스 스코프로 좁히면 INSERT 가 실패한다.
* CTA: `워크스페이스 만들기` → 성공 시 `/w/[id]` 로 이동.

### 5.3 하지 않는 것

* **템플릿 추천·팀 초대 단계를 붙이지 않는다.** 이름 하나 받고 바로 대시보드로 보낸다.
* **`지식 그룹`·`프로젝트 구성` 같은 중간 계층을 제안하지 않는다** — 존재하지 않는다(불변식 §1).

---

## 6. 데이터베이스 계약

### 6.1 진입 분기 조회 — [구현됨]

```sql
select id, name from public.workspaces order by name;
```

| 조건 | 동작 |
| --- | --- |
| 1개 | `/w/[workspaceId]` 로 리다이렉트 |
| 2개 이상 | `WorkspaceEntryChooser` |
| 0개 | **§5 온보딩** (기존: 초대 안내) |

⚠️ **`where` 절이 없는 것이 맞다.** 테넌트 필터는 RLS(`workspaces_select_member`)가 건다. `owner_id = auth.uid()` 를 더하면 초대받아 들어간 워크스페이스가 사라진다.

### 6.2 워크스페이스 생성

```sql
insert into public.workspaces (name, kind, owner_id, slug)
values (:name, 'personal', auth.uid(), :slug)
returning id, slug;
```

* `owner_id` 는 `NOT NULL`. 빠지면 실패한다.
* ⚠️ **`slug` 은 [마이그레이션 필요]** 다 — 컬럼이 아직 없다(§6.3 실측). 값은 서버가 `slugify(title=:name, taken=<전체 workspaces.slug>)` 로 만들며 사용자에게 입력받지 않는다(§9-1). 컬럼 계약은 [`public-sharing-prd.md`](public-sharing-prd.md) §2.0.
* `kind` 는 `'personal'` · `'team'` 2종. **셀프서브 첫 워크스페이스는 `'personal'`** 로 만든다 — 팀 전환은 멤버를 초대하는 시점의 의미이지 생성 시점이 아니다. *(이 매핑은 §9-4 로 열어 둔다.)*
* ⚠️ **`workspace_members` INSERT 를 이어 적지 않는다.** `workspaces_add_owner_member` AFTER INSERT 트리거가 `role='owner'` 로 등록한다. 계약이 두 곳에 있으면 한쪽만 고쳐질 때 어긋난다 — **불변식 §6**.
* ⚠️ **프롬프트 템플릿에 대해 할 일이 없다.** 전역 5종은 `workspace_id IS NULL` 로 존재하고 그대로 조회된다. 상속·복사 단계가 없다.

### 6.3 검증 완료 (로컬 `supabase_db_NexusWiki`)

* 이전 판 §5.2 1단계(`owner_id` 누락) → `null value in column "owner_id" … violates not-null constraint` **실패 재현**
* §6.2 신판 → 성공, `workspace_members` owner 행 **정확히 1개**(트리거 중복 없음)
* 전역 프롬프트 템플릿 → `ask 4` · `compile 1`, 전부 `workspace_id IS NULL`
* `workspaces.slug` → **0행**

---

## 7. 설정 & 마이그레이션 체크리스트

착수 시 순서대로. 하나라도 빠지면 콜백이 조용히 실패한다.

| # | 작업 | 대상 | 비고 |
| --- | --- | --- | --- |
| 1 | Google Cloud 프로젝트에 OAuth 2.0 클라이언트 생성 | 외부 | 승인된 리디렉션 URI 에 로컬·클라우드 양쪽 등록 |
| 2 | `[auth.external.google]` 블록 추가 | `supabase/config.toml` | **현재 이 블록 자체가 없다.** 있는 건 `[auth.external.apple] enabled = false` 하나 |
| 3 | `client_id` · `secret = "env(SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET)"` | `config.toml` + `.env` | ⚠️ **시크릿을 값으로 적지 않는다** — `config.toml` 의 기존 관행(참조로만 기록) |
| 4 | `skip_nonce_check = true` | `config.toml` | 주석이 명시: *"Required for local sign in with Google auth"*. **로컬 전용**이며 클라우드에 그대로 넘기지 않는다 |
| 5 | `additional_redirect_urls` 에 콜백 추가 | `config.toml` | 현재 `["https://127.0.0.1:3000"]`, `site_url` 은 `http://127.0.0.1:3000` |
| 6 | 클라우드 프로젝트 Auth Provider 설정 | Supabase 대시보드 | `config.toml` 은 로컬 스택용이다. 클라우드는 별도 |
| 7 | `/auth/callback` Route Handler | `apps/dashboard/app/auth/callback/route.ts` | §4.3 |
| 8 | middleware matcher 갱신 | `middleware.ts` | `/signup` **추가**, `/auth/callback` **제외** |
| 9 | 기존 비밀번호 계정 처리 | `auth.users` | §7.1 |

### 7.1 기존 계정

로컬 실측: **총 2개, 둘 다 `provider = 'email'`**. 실사용 계정이 아니므로 로컬은 `db reset` 으로 정리하면 된다.

⚠️ **클라우드는 따로 확인할 것.** 같은 쿼리를 클라우드에 돌려 실사용 계정이 있는지 먼저 본다:

```sql
select provider, count(*) from auth.identities group by 1;
```

* Google 이메일과 **동일한 주소**를 쓰는 기존 계정은 Supabase 가 이메일 검증 상태에 따라 자동 연결할 수 있다. **자동 연결을 가정하지 말고 실제로 확인한다** — 어긋나면 같은 사람에게 계정이 둘 생기고, 한쪽에만 워크스페이스 멤버십이 붙는다.
* 자동 연결이 안 되는 계정은 owner 가 새 계정을 초대하고 기존 멤버십을 옮겨야 한다.

---

## 8. 거버닝 스펙 개정 필요

`openspec/specs/workspace-entry-flow/spec.md` 가 지금 이렇게 요구한다:

> *"MUST retain the existing invitation guidance for a user with no accessible workspaces"*
> *"THEN the system displays the existing invitation guidance without naming or counting inaccessible workspaces"*

**§5 셀프서브 생성은 이 요구사항과 정면으로 충돌한다.** 화면만 바꾸면 스펙과 코드가 어긋난 채로 남는다.

* `Requirement: RLS-scoped workspace entry resolution` 의 0개 시나리오를 **초대 안내 → 워크스페이스 생성 온보딩**으로 개정한다.
* ⚠️ **함께 붙어 있던 "접근 불가 워크스페이스의 존재나 개수를 노출하지 않는다"는 유지한다.** 이건 초대 안내 때문에 있던 문구가 아니라 정보 노출 방지 요구사항이다. 온보딩 화면도 "당신이 못 보는 워크스페이스가 N개 있습니다" 류를 절대 표시하지 않는다.
* `Requirement: Non-disclosing inaccessible workspace handling` 은 손대지 않는다.

---

## 9. 미해결 결정

1. ~~`workspaces.slug` 위치~~ — **2026-08-17 결정 완료.** `workspaces.slug` 정본 + 사이드카 복제(`decisions.workspace_slug`, 계약은 [`public-sharing-prd.md`](public-sharing-prd.md) §2.0).
   **온보딩에 남은 것은 UX 결정이다** — 사용자에게 슬러그를 **입력받을지 이름에서 자동 생성할지**. *권고: 자동 생성.* `slug.py` 의 `slugify(title=이름, taken=전체 슬러그)` 가 충돌을 숫자 접미로 이미 해소하고, 첫 화면에서 필드를 하나로 줄이는 것이 §5.3("이름 하나 받고 바로 대시보드")과 맞는다. 슬러그 변경은 나중에 설정에서 열어 준다.
2. **초대 흐름의 남은 구멍** — `/signup` 이 열려도 `invite_workspace_member` 는 여전히 **미가입 이메일을 `NW404` 로 거부**한다. owner 는 초대 전에 상대가 가입했는지 알 수 없고, 알려줄 수단도 앱 안에 없다. *권고: `NW404` 문구에 `/signup` 링크를 넣거나, Supabase `inviteUserByEmail` 로 초대 메일 경로를 따로 만든다.* 후자는 §1 결정 범위 밖이므로 별도 판단.
3. **이용약관 · 개인정보 처리방침** — `/signup` 이 링크해야 하는데 **문서 자체가 없다.** 가입을 여는 이상 미룰 수 없다.
4. **첫 워크스페이스의 `kind`** — §6.2 는 `'personal'` 로 두자고 제안한다. `'team'` 이 맞다면 그 근거를 `decisions` 에 적는다.
5. **`WorkspaceEntryChooser` 어휘** — 제목이 `프로젝트 선택`, 안내가 `계속할 프로젝트를 선택하세요.` 인데 **`프로젝트` 계층은 존재하지 않는다**(불변식 §1). 시안이 아니라 **실제 배포 코드**에 남은 3계층 잔재다. 코드 2줄.

---

## 10. 프로토타입 정정 목록

시안 3화면은 **§1 확정으로 대부분 되살아났다.** 폐기가 아니라 정정 대상이다.

| 위치 | 현재 | 조치 |
| --- | --- | --- |
| 로그인 카드 `Google 계정으로 계속하기` | — | **유지** — 이제 사실이다 |
| 특징 뱃지 `GOOGLE OAUTH 2.0` | — | **유지** |
| 특징 뱃지 `POSTGRESQL RLS / 테넌트 단위 데이터 격리` | — | **유지** |
| 온보딩 카드 `첫 워크스페이스를 만들어볼까요?` | — | **유지** — §5 로 확정 |
| 온보딩 폼 `URL 식별자 /w/[slug]` | slug 필드 | **제거** — 슬러그는 이름에서 자동 생성한다(§9-1 결정) |
| 완료 화면 `워크스페이스와 팀 프로젝트 구성을 정하면` | `프로젝트` 어휘 | **수정** — 불변식 §1 |
| 전역 `🚀` | 이모지 | **제거** — 불변식 §7.2 |
| LNB `즐겨찾기` · `최근 본 위키` | 저장소 미정 | 보류 (workspace-home PRD 와 동일 항목) |
| 신규 | `/signup` 과 `/login` 이 구분되지 않음 | **화면 1개 추가** — §3.1 |

---

## 11. 검증 계획

| # | 항목 | 검증 기준 |
| --- | --- | --- |
| 1 | OAuth 왕복 | `/login` → Google 동의 → `/auth/callback` → `/` 까지 세션이 붙은 채 도착하는지 |
| 2 | 오픈 리다이렉트 | `next=//evil.com` · `next=https://evil.com` 이 외부로 나가지 않고 `/` 로 떨어지는지 |
| 3 | 코드 재사용 | `/auth/callback?code=…` 를 두 번 열면 두 번째가 `/login?error=auth` 로 가는지(1회용 코드 소비) |
| 4 | 미들웨어 경계 | `/auth/callback` 이 matcher 에 걸리지 않는지. `/signup` 은 로그인 상태에서 `/` 로 리다이렉트되는지 |
| 5 | 계정 열거 방지 | 콜백 실패가 원인과 무관하게 **같은 문구**를 내는지 |
| 6 | 세션 경쟁 조건 | 콜백 직후 `/` 가 인증 상태로 렌더되는지(전체 네비게이션 유지) |
| 7 | CVE-2025-29927 | `x-middleware-subrequest` 위조 요청이 게이트를 통과하지 못하는지. Next.js 15.2.3+ |
| 8 | 진입 분기 | 워크스페이스 0 / 1 / 2개 계정 각각에서 §6.1 표대로 동작하는지 |
| 9 | 생성 계약 | §6.2 실행 후 `workspace_members` owner 행이 **정확히 1개**인지 |
| 10 | 정보 노출 | 온보딩 화면이 접근 불가 워크스페이스의 존재·개수를 흘리지 않는지(§8) |
| 11 | 계정 연결 | 기존 이메일 계정과 같은 주소의 Google 로그인이 계정을 둘로 쪼개지 않는지(§7.1) |
| 12 | 토큰 · 이모지 | Google 'G' 로고 외 멀티컬러 요소 0개, 이모지 0개, 팔레트 밖 색 0개 |
