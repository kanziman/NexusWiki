# 🤝 Handoff Document

- **작성 일시**: 2026-08-17 (세션 종료 시점)
- **작업 브랜치**: main
- **이번 세션 커밋**: 15개 (`665b98a` ~ `a46795f`). **산출물은 전부 커밋 완료** — `docs/`·`apps/`·`supabase/` 에 미커밋 변경 없음.

## 🎯 1. 작업 목표 & 현재 상태

- **목표**: 마일스톤2 대시보드 재설계. (1) v2 프로토타입의 중복 CSS 정리 → (2) PRD 를 하나씩 실제 스키마·코드와 대조하며 재작성.
- **진행률**: CSS 정리 **완료**. PRD 리뷰 **4개 중 3개 완료**(workspace-home · source-management · wiki-document-reader). 다음은 workspace-settings.

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
- **정합성**: 프로토타입 카운트 통일(카테고리 합 18 = 문서 18, 백로그 03, 원문 42), 이모지 0개, 미정의 클래스 없음.

### 미검증

- `pnpm test` / `typecheck` / `lint` / `build` 미실행 — 이번 세션은 `apps/` 를 한 줄도 건드리지 않았다.
- workspace-settings · google-auth · backlog-management · public-sharing PRD 미검토.

## ⚠️ 4. 주의사항 & 남은 작업 (TODO)

### 🔴 최우선 — 저장소 상태 경고

- [ ] **`.claude/skills/` 하위 841개 파일이 working tree 에서 삭제된 상태**(`git status` 상 `D`, 미스테이징). **이번 세션에서 내가 지운 것이 아니다.** 이전 세션 HANDOFF 가 `.planning/` 227개 삭제로 똑같이 경고했던 패턴이다. 의도된 것인지 사용자에게 확인하고 나서 커밋하거나 복구할 것 — **임의로 커밋하지 말 것.**

### PRD 리뷰 (짝 있는 4개 중 2개 남음)

- [ ] **workspace-settings PRD 리뷰** — 다음 차례. 선행 리뷰 기록상 "100% 정합" 주장이 부분적으로 사실이었던 유일한 문서지만, **RLS 정책 수를 38개로 적었고 실제는 27개**다.
- [ ] **google-auth PRD 리뷰**
- [ ] 짝 없는 2개(`backlog-management`·`public-sharing`)는 프로토타입이 없다. 리뷰 방식을 따로 정할 것.

### 미해결 결정 (PRD 에 `[미구현]`/미해결로 기록해 둠)

- [ ] **컬렉션 스키마·UI 설계** — 방향만 확정했고 테이블 설계는 아직. `wiki-document-reader`·`source-management` 양쪽이 기다린다.
- [ ] **즐겨찾기 · 최근 본 위키 저장소 없음** — 제외할지, `user_wiki_bookmarks` 를 만들지, `localStorage` 로 갈지. 프로토타입은 카운트 뱃지를 빼둔 상태.
- [ ] **`workspaces.slug` 없음** — 라우트 `/w/[workspace_slug]` 가 의존. 현재는 `/w/[workspace_id]` 로 두었다. `workspace_public_settings` 에 넣지 말고 `workspaces.slug` 로 따로 두는 쪽 권고(비공개 워크스페이스도 URL 이 필요하므로).
- [ ] **`wiki_pages_sources_idx` 선행 마이그레이션** — source-management 화면 구현 전에 적용해야 함(§4.1).
- [ ] **JobStepper 단계 총계** — 서버 `CHAIN_ORDER` 5단계 vs 대시보드 `STAGE_TYPES` 4단계. `conflict_check` 를 진행 표시에 넣을지.
- [ ] **아카이브 기능** — `archived_at` 컬럼 + 5채널 제외 필터 + `wiki_embeddings` 처리가 필요. 이번 마일스톤 제외 권고 상태.

### 정리 대상

- [ ] **`docs/design-systems/design-tokens.css`·`.json` 이 옛 Airbnb 팔레트**(`--color-primary: #ff385c`). v2 는 청록 `oklch(.58 .11 190)` 체계다. 지금은 아무도 참조하지 않지만 남겨두면 누가 집어들 위험이 있다. `apps/dashboard/app/globals.css` 가 이걸 쓰는지 확인 후 판단할 것.
- [ ] **v1 preview 를 아직 링크하는 PRD 2개** — `backlog-management-prd.md`, `workspace-settings-prd.md`. 각자 리뷰 차례에 정정.
- [ ] **카테고리 표시명이 문서와 코드에서 갈렸다가 코드로 맞춤** — `GraphLensFilter.tsx` 의 `개념/엔티티/가이드/맵` 이 정본. 프로토타입 LNB 는 아직 `개념/대상/가이드/지도` 일 수 있으니 확인 필요.
- [ ] **source-management 프로토타입이 PRD 와 어긋남** — 시안은 아직 SQL·CSV 파일과 포맷 탭 5개를 보여주는데, PRD 는 3종(`PDF`·`텍스트/마크다운`)으로 확정됐다.

### 주의사항

- **이 세션은 `apps/`·`supabase/migrations/` 를 한 줄도 건드리지 않았다.** 전부 `docs/design-systems/v2/` 안의 문서와 정적 프로토타입 작업이다. 실제 제품 코드 반영은 아직 시작 전.
- **`docs/design-systems/v2/` 가 PRD 정본이다.** 상위 폴더의 중복본 7개는 `a46795f` 에서 제거했고, 상위에는 v1 preview HTML 만 남는다.
- **PRD 의 "확정(Validated)" 라벨을 믿지 말 것.** 이번 세션에서 검증 가능한 구체적 주장(컬럼명·테이블명·정책 수·MIME 목록·단계 수)이 3개 문서 모두에서 틀렸다. 반드시 `supabase/migrations/` 와 `apps/` 에 대조할 것. 로컬 Supabase 가 떠 있으면 쿼리를 실제로 실행해보는 것이 가장 확실하다:
  `docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres`

## 🚀 5. 다음 세션 재개 안내

다음 세션 시작 시 `/catchup` 스킬을 실행하거나 아래 멘트를 입력하세요:

> "HANDOFF.md 확인하고, `.claude/skills/` 841개 삭제가 의도된 것인지부터 확인한 다음 workspace-settings PRD 리뷰를 이어서 진행해줘."
