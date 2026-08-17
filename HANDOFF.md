# 🤝 Handoff Document

- **작성 일시**: 2026-08-17 (세션 종료 시점)
- **작업 브랜치**: main
- **이번 세션 커밋**: 18개 (`665b98a` ~ HEAD). **산출물은 전부 커밋 완료** — `docs/`·`apps/`·`supabase/` 에 미커밋 변경 없음.

## 🎯 1. 작업 목표 & 현재 상태

- **목표**: 마일스톤2 대시보드 재설계. (1) v2 프로토타입의 중복 CSS 정리 → (2) PRD 를 하나씩 실제 스키마·코드와 대조하며 재작성.
- **진행률**: CSS 정리 **완료**. PRD 리뷰 **짝 있는 5개 전부 완료**(workspace-home · source-management · wiki-document-reader · workspace-settings · auth-google). 남은 것은 프로토타입이 없는 `backlog-management` · `public-sharing` 2개.

### 이번 세션의 가장 중요한 발견

**3계층 정보구조(프로젝트 > 지식 그룹)는 PRD 와 v2 시안에만 존재하던 허구였다.**
`projects`·`wiki_groups` 테이블도 `wiki_pages.project_id`·`group_id` 컬럼도 실재하지 않는다. 그런데 **실제 앱(`apps/dashboard/`)은 처음부터 2계층으로 올바르게 구현되어 있었다** — 라우트는 `/w/[workspaceId]/{sources,ask,wiki,graph,settings}` 이고 `GraphLensFilter.tsx` 는 `wiki_pages.category` 4값을 그대로 재사용한다는 주석까지 달려 있다.

즉 **시안이 올바른 구현에서 멀어지고 있었던 것**이고, 이번 작업은 시안·문서를 구현 쪽으로 되돌린 것이다. 다음 세션도 이 전제로 판단할 것 — **의심스러우면 실제 코드가 정답이다.**

## ✏️ 2. 주요 변경 사항 & 의사결정 (Why)

### A. v2 공용 디자인 시스템 CSS 신설 (`9657825`~`866818c`)

- `docs/design-systems/v2/nexuswiki-design-system.css` 신설. 6개 프로토타입이 각자 9~16KB 씩 중복 정의하던 토큰·셸·프리미티브를 한곳으로.
- 인라인 CSS 합계 **76,591 → 52,732 bytes (31% 감소)**, 공용 CSS 16,571 bytes.
- 클래스명은 workspace-home 계열(`.sidebar`/`.topbar`/`.nav-item`)을 채택. 축약어(`.side`/`.top`/`.mark`)와 달리 `apps/dashboard/components/` 의 React 컴포넌트명으로 그대로 넘어가기 때문.
- **명세와 코드가 어긋난 3건은 명세를 따랐다**: LNB 활성 상태(`--soft` 배경), `.brand` 를 제품 로고 전용으로 분리하고 스위처는 `.switcher`, 버튼 기본값 `8px/12px·800`.

### B. 전환 중 발견해 고친 버그 3건

1. **LNB 프로필 아바타가 6개 화면 전부 깨져 있었다** — `.profile span` 이 `.avatar`(도 span)까지 잡아 `display:grid` 를 `block` 으로 덮어써서 이니셜이 원 밖으로 밀려나고 색까지 `--muted` 가 됐다. 공용 CSS 는 `.profile-text` 안에서만 잡도록 좁혔다.
2. **google-auth 로고가 아예 안 떴다** — `<img src>` 3개가 외부 도구의 죽은 API URL 을 가리켰다.
3. **reader 의 마크다운 내보내기가 죽어 있었다** — 같은 URL 치환기가 `URL.createObjectURL(blob)` 을 `URL.createObjecturl(/api/projects/.../blob?...)` 로 망가뜨려 문법 오류였다. 6개 화면 `node --check` 통과 확인.

### C. 불변식 문서 재작성 (`79d545e`, `ce247ea`)

`docs/design-systems/v2/PRODUCT-INVARIANTS.md` 가 정본이다.

- **§1 정보구조 = 2계층 확정.** 계층 대신 쓰는 수단(`category` 4종 CHECK, `wiki_links` 레드링크, `aliases`)을 실재하는 것만 표로.
- **§3 `verification_status` 오류 정정** — 이전 판이 `('unverified','verified','stale')` 로 적었으나 실제는 **`('verified','partial','unverified','disputed')`**. `stale` 은 존재하지 않는다.
- **§6 워크스페이스 생성 계약 신설** — `owner_id` 는 NOT NULL 이고 `workspaces_add_owner_member` 트리거가 owner 멤버 등록을 이미 하므로 PRD 가 중복 기술하지 않는다.
- **`[구현됨]`/`[미구현]` 표기 체계 도입.** PRD 가 없는 테이블을 "확정" 딱지와 함께 적는 반복 실패를 구조적으로 막기 위함.

### D. 컬렉션 방향 확정 (`ce247ea`) — 리뷰 중 지적 반영

3계층 위계를 없앤 것은 유지하되, **사용자 생성 묶음까지 없앤 것은 과했다.** LNB 트리 자리를 카테고리 렌즈로 채운 것은 **그릇(container)을 필터(lens)로 바꿔치기한 오류**였다 — 카테고리는 컴파일러가 배정하는 4종 고정값이라 `[+]` 로 만들 수 없다.

→ **평면 컬렉션을 마일스톤2 범위로 확정**(위계 없음, 한 문서가 여러 컬렉션에 속함). 다만 **스키마·UI 설계는 아직**이고, 설계 전까지 프로토타입 LNB 에 컬렉션 구획과 `[+]` 를 그리지 않기로 했다.

### E. PRD 재작성 3건

| PRD | 핵심 정정 |
| --- | --- |
| **workspace-home** (`a5fa10f`) | §5 DB 계약이 참조하는 객체가 **하나도 실재하지 않았다**(`category_lens`·`project_id`·`group_id`·`archived_at`·`wiki_page_citations`). 실행하면 통째로 에러. 3계층 라우트 축소, 데모 장치(시뮬레이션 모드 스위처·로그인 버튼) 제거 |
| **source-management** (`1815993`, `770bfa6`) | 지원 형식이 구현과 달랐고(실제 3종/20MiB vs PRD 6종/50MB), 탭 필터 축이 스키마에 없었으며(→`mime_type` 으로 고정), **역인용 조회에 GIN 인덱스가 없어 전체 스캔**이었다 |
| **wiki-document-reader** (`1bf75a1`) | `[+ 소스 추가]` 가 "이 문서에 소스 연결"로 적혀 파이프라인 계약과 충돌, `archived_at` 미구현, JobStepper 단계 수 하드코딩, 유사도 0.91 근거 없음 |
| **workspace-settings** | §E-1 참조 — 15건 정정 |

### E-1. workspace-settings PRD 재작성 (4번째)

**"100% 정합" 이라던 문서에서 15건이 틀렸다.** 이 화면은 나머지 3개와 달리 **이미 구현되어 있어서**(`SettingsMembersPanel`·`MembersList`·`InviteForm`·`OperationsPanel`) 코드가 정본이다. 큰 것만:

- **RLS 38개 → 27개**, 그리고 **RLS 상태 위젯 자체가 화면에 없다.** `/operations` 응답에 정책 필드가 없고 `pg_policies` 를 사용자 경로에서 읽을 방법도 없다. 정책 **개수**는 격리가 작동한다는 증거도 아니다 — `● 100% 격리 정상` 초록 뱃지는 검증하지 않은 안전 신호라 요구사항에서 삭제했다.
- **파이프라인 3대 → 5단계.** 라벨(`원문 소스 수집 & 청킹` 등)도 어디에도 없는 것이었다. 서버 `STEP_LABELS` 가 라벨을 소유한다.
- **초대는 이메일을 보내지 않는다.** 이미 가입한 사용자만 즉시 추가하고 미가입은 `NW404`. "초대장 발송"·"가입 승인 파이프라인"은 사용자가 받은편지함을 기다리게 만드는 문구다. 초대 권한도 **Owner/Editor 가 아니라 owner 전용**.
- **역할 변경 UI 는 없다.** RLS 정책(`workspace_members_update_owner`)은 있는데 화면이 없다 → `[UI 미구현]` 표기 체계를 이 PRD 에 추가.
- **`editor` 는 원문 소스를 삭제할 수 없다** (`raw_sources_delete_owner`). 이전 판이 editor 권한으로 적었다.
- **예산 단위는 micro-dollar 정수**(`monthly_budget_micros`, 기본 5,000,000 = $5)이고 `authoritative: false` 다 — 집행은 `enqueue_source_job` 이 하고 초과 시 `NW402`. 화면 수치는 표시용.

**코드 쪽 실제 버그 1건 발견**: `SettingsMembersPanel.tsx:120-128` 이 `currentRole` 을 갖고 있으면서 초대 폼을 **무조건 렌더한다.** `InviteForm.tsx` 주석은 "비-owner 에게는 폼 자체를 숨기는 것이 우선"을 전제하고 `42501` 분기를 마지막 방어선으로만 뒀는데 그 전제가 성립하지 않는다. 문서가 아니라 코드 수정이므로 별도 태스크로 뺐다.

### E-2. auth-google PRD 재작성 (5번째) — 문서 전체가 미구현 기능이었다

**제목부터 본문까지 Google OAuth 를 기술했는데, 구현된 로그인은 이메일 + 비밀번호이고 이는 누락이 아니라 잠긴 결정이다.**

> **D-01**: 로그인은 이메일 + 비밀번호만 지원한다 (매직링크/OAuth 없음). — **Reversibility: costly**
> (`.planning/phases/06-dashboard/06-CONTEXT.md`. 디렉터리가 `3e6bcef` 에서 삭제됐으므로 `git show 3e6bcef^:…` 로 읽는다.)

`signInWithOAuth` 호출 0건, `config.toml` 에 `[auth.external.google]` 블록 **자체가 없음**(있는 건 `apple = false` 하나), `/auth/callback` 라우트 없음. 셀프서브 워크스페이스 생성(`OnboardingWorkspaceCard`)도 없고, **그게 사양이다** — `openspec/specs/workspace-entry-flow/spec.md` 가 0개 사용자에게 초대 안내를 유지하라고 명시적으로 요구한다.

**→ 사용자가 D-01 번복을 결정했다 (E-3 참조).** PRD 는 그 결정을 반영해 **구현 계약** 형태로 다시 썼다.

**🔴 이번 리뷰 최대 발견 — 계정 생성 경로가 닫혀 있다.** OAuth 불일치보다 우선한다.

- 회원가입 UI 가 **없다** (`signUp`·`회원가입` 전역 grep 0건, 라우트는 `/login` 하나)
- `invite_workspace_member` 는 미가입 이메일을 `NW404` 로 **거부**한다 — 초대 대상이 먼저 계정이 있어야 한다
- 워크스페이스 0개 사용자에게는 `관리자에게 초대를 요청하세요` 를 보여준다

닫힌 고리다. 지금 새 사용자를 들이는 유일한 방법은 Studio/Admin API 로 계정을 직접 만드는 것이다. **"구현 안 됨"과 "그렇게 하기로 함"이 구분되지 않는 상태**가 진짜 문제라, 폐쇄 베타로 명시 확정하든 `/signup` 을 만들든 결정이 필요하다.

**코드 쪽 불변식 위반 1건 발견**: `WorkspaceEntryChooser.tsx:27,33` 이 `프로젝트 선택` / `계속할 프로젝트를 선택하세요.` 를 렌더한다. **`프로젝트` 계층은 존재하지 않는다**(불변식 §1). 시안이 아니라 **실제 배포 코드**에 남은 3계층 잔재다 — 2줄 수정.

### E-3. 🔒 D-01 번복 — 인증을 Google OAuth 로 단일화 (2026-08-17 사용자 결정)

`checklists.json > decisions.auth` 에 기록했다(revision 7). **근거를 여기 되풀이하지 않는다 — 그 항목을 인용할 것.**

| 결정 | 값 |
| --- | --- |
| 가입 | `/signup` 신설, **Google 계정만** |
| 로그인 | `/login` 에서 이메일+비밀번호 폼 **제거**, Google 단일화 |
| 가입 후 진입 | **셀프서브 워크스페이스 생성 허용** |

**로그인 단일화는 선택이 아니라 귀결이다** — Google 로 만든 계정에는 비밀번호가 없어 `signInWithPassword` 가 구조적으로 실패한다. "Google 전용 가입 + 비밀번호 전용 로그인"은 성립하지 않는 조합이다.

**설계상 파급 3가지 (전부 PRD 에 계약으로 적어 뒀다):**

1. **D-02 에 예외가 생긴다.** `exchangeCodeForSession` 은 세션 쿠키를 **직접 쓴다.** 1회용 authorization code 라 미들웨어에 위임할 수 없다(중복 실행 = 실패). → D-02 를 "미들웨어가 유일한 기록자" → **"OAuth 콜백과 미들웨어 두 곳만"** 으로 개정. `/auth/callback` 은 matcher 에서 **제외**해야 한다 — 미들웨어가 먼저 돌면 세션 없는 상태로 `/login` 리다이렉트가 걸려 코드가 소비되지 못한다.
2. **거버닝 스펙 개정 필요.** `openspec/specs/workspace-entry-flow/spec.md` 가 0개 사용자에게 초대 안내 유지를 **MUST** 로 요구한다. 셀프서브 생성과 정면 충돌 → 해당 시나리오만 개정하되, **"접근 불가 워크스페이스의 존재·개수를 노출하지 않는다"는 유지**한다(초대 안내와 무관한 정보 노출 방지 요구사항이다).
3. **계정 열거 방지(D-12)는 승계된다.** 비밀번호 폼이 사라져도 원칙은 남는다 — 콜백 실패는 원인 무관 단일 문구. `invite_workspace_member` 의 `NW404` 와 상반돼 보이지만 그건 owner 전용 표면이라 의도된 차이다.

**남은 구멍**: `/signup` 이 열려도 `invite_workspace_member` 는 여전히 미가입 이메일을 `NW404` 로 거부한다. owner 는 상대의 가입 여부를 알 수 없고 알려줄 수단도 없다 → PRD §9-2.

### E-4. backlog-management PRD 재작성 (6번째) — 화면의 절반이 스키마 없는 기능이었다

`wiki_links` 실컬럼은 **7개**(`id`·`workspace_id`·`from_wiki_id`·`target_slug`·`to_wiki_id`·`resolved`·`created_at`)인데 PRD 는 감지 경로·인용 문맥·해결 상태·수동 등록을 전부 기술했다. DB 실측으로 확정:

- `authenticated` 의 `wiki_links` 권한은 **SELECT 하나뿐**, 정책도 `wiki_links_select_member` 하나 → **`[+ 수동 백로그 등록]` 은 불가능하다**
- `resolved` 는 `GENERATED ALWAYS` → 직접 쓸 수 없다. `[해결 완료]` 상태로 전환한다는 서술은 성립하지 않는다
- **"소스 삭제 시 백로그로 전이"는 경로가 통째로 없다.** `on delete set null (to_wiki_id)` 는 **위키 페이지** 삭제 때 걸리고 `wiki_pages.sources` 는 jsonb 라 FK 도 없다. 게다가 **소스 삭제 API 엔드포인트 자체가 없다**(`sources.py` 는 POST 3개뿐)
- 이모지 5종을 쓰면서 §4.2 에 "Zero Emojis"를 적어 뒀다 — 문서가 자기 규칙을 위반
- "로즈/레드 틴트"는 불변식 §7.1 이 **명시적으로 금지한 팔레트**다

**핵심 통찰 — 백로그는 할 일 목록이 아니라 본문의 파생 상태다.** `link_sync.py` 가 재컴파일마다 `delete_wiki_links_not_in` 으로 본문에 없는 링크를 **지운다.** 사용자가 항목을 만들어도 다음 컴파일이 지운다. 이게 수동 등록·보류·담당자 지정이 전부 같은 벽에 부딪히는 이유다.

**이미 구현된 표면이 있다** — `RedLinkCta.tsx`. 문구 계약 `아직 작성되지 않음 · 지금 생성`(글자 그대로), 클릭 시 `sources?prefillTitle=…&tab=text`. **"이 백로그에 소스 연결"이 아니라 "워크스페이스에 소스 추가"** 다 — wiki-document-reader §2.2 와 같은 정정이다.

**인덱스 실측에서 나온 함정**: 미해결 링크가 테이블 대부분인 초기 상태에서는 `EXPLAIN` 이 `Seq Scan` 을 보여주는데 **이게 정상이다**(모든 행이 부분 인덱스 조건에 맞으면 인덱스 경유가 손해). 20개 워크스페이스·20,000행 중 미해결 1,000행(5%)으로 만들면 `Bitmap Index Scan on wiki_links_unresolved_slug_idx` 로 넘어간다. **Seq Scan 보고 인덱스를 더 만들지 말 것** — PRD §4.1 에 실측표로 남겼다.

### F. 트러블슈팅

- **macOS Chrome 이 창 너비를 최소 485px 로 강제한다.** `--window-size=390` 으로 찍으면 이미지만 390px 로 잘려 "모바일이 깨졌다"고 오판했다. 실제 390px 뷰포트를 보려면 **iframe 하네스**가 필요하다(`scratchpad/frame.py` 패턴).
- **DOTALL 정규식으로 HTML 블록을 지우다 reader 의 `nav-stack` 을 통째로 날렸다.** 커밋 안 된 작업이 있어 되돌리지 않고 정본 LNB 를 새로 생성해 복구했다. HTML 을 정규식으로 자를 때 `<svg.*?</svg>` 가 버튼 경계를 넘어간다.

## 🧪 3. 검증 상태

### 완료된 검증

- **렌더 비교**: 6화면 × 390/640/900/1280/1680px 에서 `scrollWidth == clientWidth`(가로 스크롤 금지 규칙). 원본과 렌더 일치 확인.
- **JS 문법**: 6화면 `node --check` 통과.
- **DB 계약 실행 검증** (로컬 Supabase `supabase_db_NexusWiki`):
  - workspace-home §5.1 — 구판은 `owner_id` NOT NULL 위반으로 실패 재현, 신판은 `workspace_members` owner 행 **정확히 1개**(트리거 중복 없음)
  - workspace-home §5.2/5.3/5.4 — 3개 쿼리 에러 없이 실행
  - source-management §4.1 — 3,000행 넣고 `Seq Scan` → `Bitmap Index Scan` 전환 확인
  - wiki-document-reader §3 — 4개 계약 실행 확인, `p_fanout` 21 입력이 거부되는 것까지 확인
  - backlog-management §4 — 3개 계약 실행 확인. `wiki_links` 컬럼 **7개**·`resolved = GENERATED ALWAYS`·`authenticated` 권한 **SELECT 단독**·정책 1개 실측. 인덱스는 현실 비율(20 ws / 20,000행 중 미해결 5%)에서 `Bitmap Index Scan on wiki_links_unresolved_slug_idx` 확인
  - auth-google §5 — 구판 §5.2 1단계가 `owner_id` NOT NULL 위반으로 **실패 재현**, 신판은 성공 + `workspace_members` owner 행 **정확히 1개**. 전역 프롬프트 템플릿 `ask 4 / compile 1` 이 `workspace_id IS NULL` 로 존재(=바인딩 단계 없음), `workspaces.slug` **부재** 확인
  - workspace-settings §4 — 6개 계약 실행 확인 + `invite_workspace_member` 가 비-owner 를 `42501` 로 거부하는 것까지 확인. `pg_policies` **27행**, `role` CHECK 3종, `monthly_budget_micros` 기본값 `5000000`, RPC 5개 전부 `prosecdef = t` 로 실재, `workspace_public_settings`·`wiki_page_publications`·`user_profiles`·`workspaces.slug` **전부 부재** 확인
- **정합성**: 프로토타입 카운트 통일(카테고리 합 18 = 문서 18, 백로그 03, 원문 42), 이모지 0개, 미정의 클래스 없음.

### 미검증

- `pnpm test` / `typecheck` / `lint` / `build` 미실행 — 아직 `apps/` 를 한 줄도 건드리지 않았다.
- backlog-management · public-sharing PRD 미검토.
- **프로토타입 HTML 은 하나도 안 고쳤다.** workspace-settings §5(11건) · auth-google §7(8건)에 정정 목록만 표로 남겼다.
- **E-3(Google 인증)은 결정만 됐고 코드는 한 줄도 안 썼다.** PRD 는 구현 계약이지 구현 현황이 아니다.

## ⚠️ 4. 주의사항 & 남은 작업 (TODO)

### 저장소 상태 — 해소됨

- [x] **`.claude/skills/` 하위 840개 파일 삭제는 사용자가 의도한 것으로 확인**(2026-08-17). 더 이상 경고 대상이 아니다. 스테이징·커밋은 아직 안 했다 — 사용자가 별도로 지시할 때 처리할 것.

### 🔴 최우선 — Google 인증 구현 (E-3 결정, 전량 미구현)

착수 순서는 `auth-google-prd.md` §7 체크리스트. **하나라도 빠지면 콜백이 조용히 실패한다.**

- [ ] Google Cloud OAuth 2.0 클라이언트 생성 + 로컬·클라우드 리디렉션 URI 등록
- [ ] `config.toml` 에 `[auth.external.google]` **블록 신설** — 현재 이 블록 자체가 없다(있는 건 `apple = false` 하나). 시크릿은 `env(...)` 참조로만
- [ ] `skip_nonce_check = true` — **로컬 전용**, 클라우드에 넘기지 말 것 (config 주석: "Required for local sign in with Google auth")
- [ ] 클라우드 프로젝트 Auth Provider 별도 설정 — `config.toml` 은 로컬 스택용이다
- [ ] `app/auth/callback/route.ts` Route Handler 신설 (PRD §4.3)
- [ ] `middleware.ts` matcher: `/signup` **추가**, `/auth/callback` **제외**
- [ ] `LoginForm.tsx` 삭제 → `GoogleAuthButton` 교체, `/signup` 신설
- [ ] `/` 0개 분기를 셀프서브 온보딩으로 교체 (PRD §5)
- [ ] `openspec/specs/workspace-entry-flow/spec.md` 개정 (PRD §8)
- [ ] **클라우드 기존 계정 확인** — `select provider, count(*) from auth.identities group by 1`. 로컬은 2개 전부 `email` 이라 `db reset` 이면 되지만 클라우드는 별도. 같은 이메일의 자동 계정 연결을 **가정하지 말고 실측할 것** (어긋나면 한 사람에게 계정이 둘 생기고 한쪽에만 멤버십이 붙는다)
- [ ] **이용약관 · 개인정보 처리방침 문서** — `/signup` 이 링크해야 하는데 문서 자체가 없다. 가입을 여는 이상 미룰 수 없다

### PRD 리뷰

- [x] **backlog-management PRD 리뷰 완료** (E-4). 프로토타입 없이 문서만 봤다.
- [ ] **public-sharing PRD 리뷰** — 마지막 1개. 프로토타입 없음.

### 미해결 결정 (PRD 에 `[미구현]`/미해결로 기록해 둠)

- [ ] **컬렉션 스키마·UI 설계** — 방향만 확정했고 테이블 설계는 아직. `wiki-document-reader`·`source-management` 양쪽이 기다린다.
- [ ] **즐겨찾기 · 최근 본 위키 저장소 없음** — 제외할지, `user_wiki_bookmarks` 를 만들지, `localStorage` 로 갈지. 프로토타입은 카운트 뱃지를 빼둔 상태.
- [ ] **`workspaces.slug` 없음** — 라우트 `/w/[workspace_slug]` 가 의존. 현재는 `/w/[workspace_id]` 로 두었다. `workspace_public_settings` 에 넣지 말고 `workspaces.slug` 로 따로 두는 쪽 권고(비공개 워크스페이스도 URL 이 필요하므로). **DB 실측으로 부재 확정.**
- [ ] **초대 폼 owner 게이트 (코드 수정)** — `SettingsMembersPanel.tsx` 가 `currentRole === "owner"` 로 `InviteForm` 을 감싸야 한다. 지금은 viewer/editor 도 폼을 보고 제출 후에야 `권한이 없습니다.` 를 받는다.
- [ ] **멤버 로스터 `가입 일시` 표시 여부** — RPC 는 `created_at` 을 주고 시안은 열을 그리는데 `MembersList` 가 렌더하지 않는다. 표시 권고.
- [ ] **역할 변경 UI** — `workspace_members_update_owner` 정책은 있고 화면이 없다. owner 자기 강등은 `protect_owner_membership` 이 막으므로 owner 행은 비활성이어야 한다.
- [ ] **워크스페이스 이름 변경·삭제 UI** — 정책만 있고 화면 없음. 삭제는 `owner_id … on delete restrict` 와 맞물린다.
- [ ] **멤버 표시 이름** — `auth.users` 에도 `workspace_members` 에도 이름이 없다. `user_profiles` 신설이 필요하며 이번 마일스톤 제외 권고.
- [ ] **초대 흐름의 남은 구멍** — `/signup` 이 열려도 `invite_workspace_member` 는 미가입 이메일을 `NW404` 로 거부한다. `NW404` 문구에 `/signup` 링크를 넣을지, Supabase `inviteUserByEmail` 로 초대 메일 경로를 따로 만들지. (auth-google PRD §9-2)
- [ ] **첫 워크스페이스의 `kind`** — PRD §6.2 는 `'personal'` 제안. `'team'` 이 맞다면 근거를 `decisions` 에 적을 것.
- [ ] **`wiki_pages_sources_idx` 선행 마이그레이션** — source-management 화면 구현 전에 적용해야 함(§4.1).
- [ ] **JobStepper 단계 총계** — 서버 `CHAIN_ORDER` 5단계 vs 대시보드 `STAGE_TYPES` 4단계. `conflict_check` 를 진행 표시에 넣을지.
- [ ] **아카이브 기능** — `archived_at` 컬럼 + 5채널 제외 필터 + `wiki_embeddings` 처리가 필요. 이번 마일스톤 제외 권고 상태.

### 정리 대상

- [ ] **`docs/design-systems/design-tokens.css`·`.json` 이 옛 Airbnb 팔레트**(`--color-primary: #ff385c`). v2 는 청록 `oklch(.58 .11 190)` 체계다. 지금은 아무도 참조하지 않지만 남겨두면 누가 집어들 위험이 있다. `apps/dashboard/app/globals.css` 가 이걸 쓰는지 확인 후 판단할 것.
- [x] **v1 preview 링크 정정 완료** — `workspace-settings` · `backlog-management` 둘 다.
- [ ] **backlog 는 v2 프로토타입이 없다** — 만들 경우 `RedLinkCta` 문구 계약을 그대로 따를 것 (PRD §5-4).
- [ ] **소스 삭제 API 부재** — source-management PRD §3.6·§3.7 이 삭제 흐름을 정의하는데 `sources.py` 에 DELETE 엔드포인트가 없다(POST 3개뿐). RLS 정책은 있으니 **[UI·API 미구현]** 표기가 필요하다. backlog 리뷰 중 발견.
- [ ] **프로토타입 LNB 의 카테고리 표시명이 코드와 어긋난다 (확인 완료)** — 시안은 `개념/대상/가이드/지도`, 실제 `GraphLensFilter.tsx` 는 `개념/엔티티/가이드/맵`. PRD 는 코드 쪽으로 이미 맞췄으니 **시안 2군데(`대상`→`엔티티`, `지도`→`맵`)만 고치면 된다.**
- [ ] **source-management 프로토타입이 PRD 와 어긋남** — 시안은 아직 SQL·CSV 파일과 포맷 탭 5개를 보여주는데, PRD 는 3종(`PDF`·`텍스트/마크다운`)으로 확정됐다.
- [ ] **workspace-settings 프로토타입 정정 11건** — 목록은 `workspace-settings-prd.md` §5 표에 있다. 그중 **`EDITOR … 위키 재컴파일` 문구는 불변식 §2 직접 위반**이라 우선순위가 높다.
- [ ] **auth-google 프로토타입 정정** — 목록은 `auth-google-prd.md` §10 표. **E-3 결정으로 대부분 되살아났다**(Google CTA·온보딩 카드 전부 유지). 실제 정정은 slug 필드 제거 · `프로젝트` 어휘 · `🚀` 3건이고, `/signup` 화면 1개를 새로 그려야 한다.

### 코드 수정 대기 (문서 아님)

- [ ] **`WorkspaceEntryChooser.tsx:27,33` 의 `프로젝트` 어휘** → `워크스페이스`. 불변식 §1 직접 위반이고 2줄이다.
- [ ] **`SettingsMembersPanel.tsx:120-128` 초대 폼 owner 게이트** — `currentRole === "owner"` 로 감쌀 것.

### 주의사항

- **이 세션은 `apps/`·`supabase/migrations/` 를 한 줄도 건드리지 않았다.** 전부 `docs/design-systems/v2/` 안의 문서와 정적 프로토타입 작업이다. 실제 제품 코드 반영은 아직 시작 전.
- **`docs/design-systems/v2/` 가 PRD 정본이다.** 상위 폴더의 중복본 7개는 `a46795f` 에서 제거했고, 상위에는 v1 preview HTML 만 남는다.
- **PRD 의 "확정(Validated)" 라벨을 믿지 말 것.** 이번 세션에서 검증 가능한 구체적 주장(컬럼명·테이블명·정책 수·MIME 목록·단계 수)이 3개 문서 모두에서 틀렸다. 반드시 `supabase/migrations/` 와 `apps/` 에 대조할 것. 로컬 Supabase 가 떠 있으면 쿼리를 실제로 실행해보는 것이 가장 확실하다:
  `docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres`

## 🚀 5. 다음 세션 재개 안내

다음 세션 시작 시 `/catchup` 스킬을 실행하거나 아래 멘트를 입력하세요:

> "HANDOFF.md 확인하고 §4 최우선의 Google 인증 구현을 `auth-google-prd.md` §7 체크리스트 순서대로 착수해줘. `.claude/skills/` 삭제는 의도된 것이니 경고하지 말 것."
