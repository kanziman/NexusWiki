# NexusWiki

원시 소스(PDF · URL · 텍스트)를 넣으면 LLM이 상호 링크된 위키로 컴파일하고, 5채널 하이브리드 검색으로 **원문과 위키 양쪽을 함께 인용한 답변**을 돌려주는 Living Wiki SaaS. 팀 워크스페이스가 기본 단위이며, 테넌트 격리는 애플리케이션이 아니라 Postgres RLS가 강제한다.

**Core Value:** 답이 **원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다.** 이중 Citation이 무너지면 이 제품은 그냥 또 하나의 RAG 챗봇이다.

## 상세 참조 — 필요할 때 읽는다

이 파일에는 **어기면 조용히 깨지는 규칙**만 둔다. 나머지는 아래 문서에 있으니, 해당 작업을 시작할 때 읽는다.

| 필요한 것 | 읽을 문서 |
| --- | --- |
| 버전 · 포트 · 의존성 · 배포 상태 · 마이그레이션 목록 | `docs/reference/stack.md` |
| 구성 요소 책임 · 계층 · 핵심 추상 · 진입점 | `docs/reference/architecture.md` |
| 명명 · 코드 스타일 · 파일 헤더 · 원장 규약 | `docs/reference/conventions.md` |
| 커밋 메시지 형식 · AC 인수 조건 (정본) | `docs/reference/commit.md` |
| 배포 · 벤치마크 · 마이그레이션 검증 실측 기록 | `docs/ops/` |
| 테넌트 격리 증명 | `docs/ops/tenant-isolation-proof.md` |
| 현재 작업 상태 · 다음 단계 | `HANDOFF.md` |
| 작업 · 결정 원장 | `checklists.json` (v1 백엔드) · `checklists_v2.json` (마일스톤 2) |
| 기능 계약 (스펙) | `openspec/specs/` |

⚠️ 개수 · 버전 · 상태는 이 파일에 쓰지 않는다. 그것들이 이 문서를 stale하게 만든 원인이다 — 참조 문서나 코드를 가리킨다.

## 불변 규칙

### 보안

- **사용자 요청 경로는 요청자 JWT(`user_client`)를 쓴다.** `service_role`은 워커와 마이그레이션 전용이다. `service_role`은 BYPASSRLS라 사용자 경로에 쓰는 순간 격리 정책 전체가 장식이 된다.
- **Next.js는 15.2.3 이상이어야 한다.** CVE-2025-29927은 `x-middleware-subrequest` 헤더 위조로 미들웨어를 건너뛴다 — 이 앱의 테넌트 게이트가 미들웨어다.
- **RLS 위반이 항상 예외인 것은 아니다.** `USING`에 막힌 UPDATE/DELETE는 **예외가 아니라 0행**을 돌려준다. API는 *영향 행 수 0 → HTTP 403*으로 매핑해야 한다. `WITH CHECK` 위반은 SQLSTATE `42501`을 던지며 이것도 403이다.
- **역할은 셋, 권한도 셋.** `anon`은 정책이 아예 없다(완전 거부). `authenticated`는 전적으로 RLS의 지배를 받는다. `service_role`은 BYPASSRLS이므로 **워커 코드가 `workspace_id` 필터를 명시적으로 걸어야 한다.**

### 정합성

- **색인 시점과 질의 시점 토크나이저가 동일해야 한다.** 불일치는 예외 없이 조용히 실패한다. `tsv_tokenizer_version`은 재색인 범위를 좁히려고 존재한다.
- **벡터 검색은 post-filter다.** `where workspace_id = $1 order by embedding <=> $2 limit k`는 HNSW가 먼저 k개를 고르고 그다음 필터링한다 — k보다 적게 돌아올 수 있다. RLS도 같은 post-filter처럼 동작한다. 검색 질의는 `set local hnsw.iterative_scan = strict_order`(pgvector 0.8+)를 설정해야 한다.
- **작업은 at-least-once다.** `reap_stale_jobs` 기본 타임아웃은 15분이며, 가장 오래 걸리는 정상 LLM 작업보다 짧으면 이중 처리가 발생한다. 모든 핸들러는 멱등이어야 한다 — 세 upsert 키 `(workspace_id, slug)`, `(raw_source_id, chunk_index)`, `(wiki_id, chunk_index)`가 정확히 이 목적으로 존재한다.
- **마이그레이션 번호 순서가 곧 적용 순서다.** 이미 클라우드에 push한 번호보다 앞선 번호를 나중에 추가하면 로컬과 클라우드 순서가 어긋난다.

### 운영

- **로컬 포트는 544xx 고정이다.** 같은 머신의 `zettlink` 스택이 543xx를 점유한다. 튜토리얼의 `54321`/`54322`를 쓰면 다른 프로젝트 DB에 붙는다.
- **로컬 `psql`이 없다.** `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres`를 쓴다.
- **리전은 프로젝트 생성 후 변경 불가다.** Supabase `ap-southeast-1` + Railway `asia-southeast1`.
- 예산은 개인 프로젝트 수준이다 — Railway Hobby $5/mo + Supabase + LLM 종량.

## Anti-Patterns

### `service_client()`를 사용자 요청 경로에 쓰기

`service_role`은 BYPASSRLS다. 사용자 경로에서 한 번이라도 쓰면 `0004_rls_policies.sql`의 격리 정책 전체가 무의미해지고, 테넌트 경계는 앱 코드의 실수 하나에 달리게 된다.

**대신**: 요청자 JWT로 만든 `user_client`를 쓴다. 워커처럼 불가피하게 `service_role`을 쓰는 곳은 `workspace_id` 필터를 직접 건다.

### `jobs`를 직접 UPDATE하기

시도 회계와 lock 일관성 CHECK(`jobs_lock_consistency`)가 네 개 함수 안에 산다. 직접 UPDATE는 이를 전부 우회해 잠금 상태가 어긋난 행을 남기고, 그 행은 다시 claim되지도 reap되지도 않는다.

**대신**: `claim_job` / `complete_job` / `fail_job` / `reap_stale_jobs`. 전부 `service_role` 전용이다.

### bigram 문자열을 `to_tsquery`에 그대로 넣기

색인은 앱이 만든 bigram `tsvector('simple', …)`다. bigram 문자열을 `to_tsquery`에 그대로 넘기면 파서가 이를 연산자 문법으로 읽어 예외를 던지거나 **조용히 0건**을 돌려준다.

**대신**: 질의도 색인과 동일한 토크나이저를 통과시킨 뒤 조합한다. `tsv_tokenizer_version`이 일치하는지 확인한다.

### `search_tsv`를 생성 컬럼으로 만들기

Postgres 기본 파서는 한국어를 토큰화하지 못한다. 생성 컬럼으로 만들면 앱의 bigram 토크나이저를 끼워 넣을 수 없고 `tsv_tokenizer_version` 추적도 불가능해진다 — 생성 컬럼이 아닌 것은 실수가 아니라 설계다.

**대신**: 앱이 값을 쓰고 토크나이저 버전을 함께 기록한다.

### 프롬프트 템플릿에 `str.format` 쓰기

템플릿 자리표시자는 `{{variable}}` 이중 중괄호다. `str.format`은 중괄호를 소비해 자리표시자를 깨뜨리고, 프롬프트 안에 든 JSON 예시의 `{`에서 `KeyError`를 던진다.

**대신**: `{{var}}`를 명시적으로 치환한다.

### 인용 앵커 없이 LLM 컨텍스트 조립하기

이중 Citation이 이 제품의 존재 이유다. 앵커 없이 컨텍스트를 만들면 답변을 원문으로도 위키로도 되짚을 수 없다.

**대신**: 원문 청크는 `raw_source_id` + `chunk_index` + char 구간을, 위키는 `wiki_id` + `slug`를 컨텍스트에 함께 실어 보낸다.

## 항상 지키는 규약

전체 규약은 `docs/reference/conventions.md`에 있다. 매 편집에 걸리는 것만 여기 둔다.

- **모든 주석 · 커밋 메시지 · PR 제목과 본문 · 문서는 한국어다.** squash merge가 PR 제목을 `main`의 커밋 제목으로 만들기 때문에 PR 제목도 같은 규칙을 받는다. 식별자 · 키워드 · 파일명은 영문/ASCII를 유지한다. 한국어 코드베이스에 영문 식별자는 사고가 아니라 하우스 스타일이다.
- SQL은 전부 소문자다 — 키워드도 포함(`create table`, `on delete cascade`).
- 자명하지 않은 모든 DDL 선택에 **"안 그러면 뭐가 깨지는지"** 주석을 단다. `⚠️`는 무시하면 데이터나 보안이 조용히 망가지는 함정에만 붙인다.
- **근거를 두 곳에 쓰지 않는다.** 프로젝트 수명 전체의 결정은 `checklists.json > decisions.<key>`를, 하나의 change 안에서만 유효한 결정은 그 change의 `design.md`를 인용한다.
- 커밋 메시지 형식은 `docs/reference/commit.md`가 정본이다 — 쓰기 전에 읽는다. 하나의 작업 = 하나의 커밋.
- 계획에서 벗어나면 파일 주석과 `checklists.json`의 `deviations_from_plan`을 **함께** 갱신한다.

## Agent Workflow

사용자 행동이나 외부 계약을 바꾸는 작업은 하나의 OpenSpec change로 분리한다. 진입점은 다음과 같다.

| 단계 | 진입점 | 산출물 |
|---|---|---|
| 탐색 | `/opsx:explore` | (없음 — 대화) |
| 계획 | `/plan-feature` (게이트·GitHub 추적) → `/opsx:propose` | `proposal.md` · delta spec · `design.md` · `tasks.md` |
| 계획 수정 | `/opsx:update` | 위 산출물 갱신 |
| 구현 | `/opsx:apply` | 코드 + `tasks.md` 체크박스 |
| 스펙 동기화 | `/opsx:sync` | `openspec/specs/` 갱신 |
| 아카이브 | `/opsx:archive` | `openspec/changes/archive/` |
| 리뷰 | 서브에이전트 2종 (아래 「리뷰 게이트」) | `.../reviews/<reviewer>-r<N>.md` |
| PR | `/create-pr [issue]` | commit + GitHub PR |

- 작업 추적은 **GitHub Issues + `kanziman` Project #1**만 사용한다 — Linear는 쓰지 않는다. 계약: `openspec/specs/feature-planning-workflow/spec.md`
- 개발 workflow나 검증 계약 자체를 바꾸는 문서·도구 작업도 OpenSpec change로 관리한다.
- 순수 문서 편집은 범위를 사용자와 확인하고 관련 검증만 실행한다.
- Codex용 진입점은 `AGENTS.md`다. 두 진입점은 같은 스펙을 인용하며 규칙을 복제하지 않는다.

### 리뷰 게이트

`/opsx:apply`가 모든 task를 끝낸 뒤 `/create-pr` **직전에 1회** 돈다. 두 리뷰어를 병렬로 띄운다.

| 리뷰어 | 보는 것 |
| --- | --- |
| `spec-conformance-reviewer` | delta spec의 Given/When/Then ↔ 실제 구현 |
| `tenant-isolation-reviewer` | 격리 · 403 매핑 · 멱등성 · 조용한 실패 |

일반 버그·품질 리뷰는 이 게이트에 없다. 필요하면 `/code-review`를 따로 부른다.

각 리뷰어는 `openspec/changes/<change>/reviews/<reviewer>-r<N>.md`에 보고서를 쓰고 `pass` · `needs_fix` · `blocked` 중 하나를 판정한다.

- **둘 다 `pass`** → PR로 진행
- **하나라도 `needs_fix`** → 지적 사항을 고치고 라운드를 올려 재리뷰
- **하나라도 `blocked`** → 진행하지 않는다. 스펙 모호·범위 이탈이거나 테넌트 경계가 뚫리는 경우이므로 사람의 결정이 필요하다
- ⚠️ **최대 3라운드.** 3라운드에서도 `pass`가 아니면 `blocked`으로 확정하고 사람에게 넘긴다. 리뷰-수정 루프를 무한히 돌지 않는다

서브에이전트의 최종 응답은 사용자에게 표시되지 않는다. 판정 등급과 보고서 경로를 반드시 사용자에게 중계한다.

### 연속 진행 권한

계약: `openspec/specs/autonomous-workflow/spec.md`

- 사용자가 "한번에 진행", "승인없이 계속", "이어서 진행"처럼 연속 진행을 명시하면, 해당 범위의 change를 계획 → 구현 → 검증 → spec sync → archive까지 반복 승인 없이 완료한다.
- 이 권한은 이미 검증된 task의 완료 처리와 아카이브를 멈추지 않는다. 완료 후에는 다음 미차단 우선순위 이슈로 이동한다.
- ⚠️ 다음 세 경우에만 중단하고 필요한 후속 조치를 보고한다. 그 외의 사유로 멈추면 권한을 위반한 것이다:
  1. **외부 권한·자격 증명 부재** — 사용자만 가진 credential이 필요할 때. 독립적으로 가능한 작업은 계속한다
  2. **material ambiguity** — 해석에 따라 결과 계약(사용자 흐름 · 경계 동작 · 용어)이 달라질 때
  3. **필수 검증 실패** — 실패한 검증이 있으면 해당 task를 완료 처리하지 않는다

### 완료 보고 규칙

- 완료를 주장하기 전에 관련 테스트 · typecheck · lint · `openspec validate <change> --strict`를 **새로** 실행한다. 이전 실행 결과를 재사용하지 않는다.
- 외부 상태 변경(GitHub 이슈·PR·Project 상태)은 명령 응답으로 성공을 확인한 경우에만 완료로 보고한다. 식별자를 추측하지 않는다.
- task는 명세된 동작이 **전부** 구현됐을 때만 `- [x]` 처리한다. 부분 구현·연기 상태에서는 처리하지 않는다.
