# 코드 규약 참조

`.claude/CLAUDE.md`가 필요할 때 읽어 들이는 상세 참조다. 전 편집에 걸리는 핵심 규약은 CLAUDE.md에 요약돼 있고, 여기에는 **전체 규칙과 예시**를 둔다.

## 명명

### 마이그레이션
- `NNNN_snake_case_topic.sql`, 4자리 zero-pad
- **번호 순서가 곧 적용 순서다.** 이미 클라우드에 push한 번호보다 앞선 번호를 나중에 추가하면 로컬/클라우드 순서가 어긋난다

### SQL
- 전부 소문자 `snake_case`. SQL 키워드도 소문자(`create table`, `on delete cascade`). `supabase/migrations/` 어디에도 대문자 키워드가 없다
- 테이블: 복수형 명사 — `workspaces`, `wiki_pages`, `source_chunks`
- 인덱스: `<table>_<columns>_idx` — `jobs_poll_idx`, `source_chunks_embedding_idx`
- 트리거: `<table>_<action>` — `workspaces_set_updated_at`, `workspaces_add_owner_member`
- 명명된 CHECK 제약: `<table>_<intent>` — `jobs_lock_consistency`
- 함수: 동사 우선 `snake_case`, 정의·호출 양쪽에서 항상 `public.<name>`으로 스키마 한정
- 함수 파라미터: 컬럼명 충돌을 피하려고 `p_` 접두 — `p_worker_id`, `p_job_id`, `p_backoff`. RLS 헬퍼는 대신 짧은 도메인명(`ws_id`, `min_role`)을 쓴다
- 열거형은 Postgres `enum` 타입이 **아니라** `text` + 인라인 `check (col in (...))`
  - 문서화된 예외 하나: `jobs.type`은 열거 CHECK가 없다(비어있지 않음만 검사). 작업 종류가 자주 바뀌기 때문이다. 대신 **워커는 모르는 `type`을 곧장 `dead`로 보내고 `last_error`를 채워야 한다**

### Python
- `snake_case.py` — `apps/api/src/api/` 또는 `apps/worker/src/worker/`
- 공유 코드는 `packages/core/src/nexuswiki_core/`
- 테스트: 각 워크스페이스 멤버의 `tests/test_<module>.py`

### TypeScript / React
- 컴포넌트: `PascalCase.tsx` — `apps/dashboard/components/`
- 라우트: App Router 소문자 세그먼트 + 라우트 그룹 — `apps/dashboard/app/(auth)/login/page.tsx`
- 테스트: `apps/dashboard/tests/<Component>.test.tsx`

## 코드 스타일

- **SQL**: 2칸 들여쓰기, 컬럼 한 줄에 하나, 인라인 주석 정렬, 파일 내 번호 섹션은 `-- ---` 룰 라인으로 구분
- **Python**: `ruff`
- **TypeScript/TSX**: `prettier`, `strict` 모드에서 `tsc --noEmit` 무결
- `.pre-commit-config.yaml`이 Python에 ruff, dashboard에 prettier를 적용한다
- 게이트: 저장소 루트에서 `pre-commit run --all-files` 통과

### 언어
모든 주석 · 커밋 메시지 · PR 제목과 본문 · 문서는 **한국어**다. 식별자 · 키워드 · 파일명은 영문/ASCII를 유지한다. 한국어 코드베이스에 영문 식별자는 사고가 아니라 하우스 스타일이다 — 맞춰서 쓴다.

## 파일 헤더

- **GitHub Issue와 OpenSpec change를 인용한다** — 현재 작업과 구현 근거를 같은 추적 단위로 연결한다
- **결정의 수명이 인용 계층을 정한다**
  - 프로젝트 수명 전체의 제품 · workflow 계약 → `openspec/specs/<capability>/spec.md`
  - 하나의 change 안에서만 유효한 결정 → 해당 OpenSpec change의 `design.md`
  - 같은 근거를 두 계층에 되풀이하지 않는다
- 결정의 근거를 인라인으로 다시 쓰지 않는다. 원장을 가리킨다
- 하위 소비자를 Issue 또는 change 이름으로 지목해 누가 이 객체에 의존하는지 드러낸다
- 파일이 상태 기계를 인코딩하면 ASCII 상태/흐름도를 헤더에 둔다 (`supabase/migrations/0003_jobs.sql`)

## 주석

- 자명하지 않은 모든 DDL 선택에 **"안 그러면 뭐가 깨지는지"** 주석을 단다
- `⚠️`는 무시하면 데이터나 보안이 **조용히** 망가지는 함정에 붙인다
- 계획에서 벗어난 부분은 해당 OpenSpec change의 `design.md`와 `tasks.md`에 반영하고, 추적 상태는 GitHub Issue에 갱신한다
- 공개 함수에는 계약과 호출자 제한을 설명하는 `comment on function ... is '...'`를 단다
- 자리표시자/경로 규칙은 그 값을 저장하는 컬럼 자리에 문서화한다 (예: `{workspace_id}/{raw_source_id}/{filename}`)

## 디자인 토큰

- CSS 변수 명명: `--<category>-<name>[-<modifier>]` — `--color-primary`, `--color-surface-soft`
- 카테고리: `color`, `typography`(fontFamily + `display-xl`/`display-lg`/`title-md`/`body-md`/`body-sm`), `border.radius`(`none`…`full`), `spacing`(`xxs`…`section`)
- CSS 파일은 번호 배너 주석(`1. COLOR TOKENS`)으로 구획하고 각 토큰에 용도 주석을 단다
- 토큰을 소비한다. 컴포넌트에 생 hex 값이나 임의 px 간격을 넣지 않는다

## 커밋

⚠️ 커밋 메시지 형식의 **정본은 `docs/reference/commit.md`다.** Conventional Commits v1.0.0, 한국어 제목, bullet 본문, `feat`/`fix`의 AC 블록, `Refs:`/`Closes:` 이슈 링크 규칙이 거기 있다. 여기에 복제하지 않는다.

이 저장소에만 해당하는 것:

- scope: `db` · `api` · `worker` · `web` · `config` · `docs`
- 마이그레이션 커밋은 제목에 번호를 앞세운다 — `fix(db): 0015 워크스페이스 슬러그 마이그레이션 기록`
- commit 범위와 PR 발행 안전 규칙은 `openspec/specs/pull-request-workflow/spec.md`를 따른다

## 작업 추적과 역사 기록

- 현재 작업 상태와 우선순위는 **GitHub Issues + `kanziman` Project #1**에서 관리한다
- 현재 제품·workflow 계약은 `openspec/specs/`, 변경 단위 계획·결정·검증은 `openspec/changes/<change>/`에서 관리한다
- 세부 원장 계약은 `openspec/specs/feature-planning-workflow/spec.md`를 인용하고 이 문서에 복제하지 않는다
- `checklists.json`과 `checklists_v2.json`의 phase/task 상태는 GSD 작업 당시의 역사적 스냅샷이다. 현재 진행 상태처럼 갱신하지 않는다
- 과거 결정의 배경을 인용할 때는 checklist의 `document_status.as_of`를 함께 밝혀 현재 계약과 구분한다

## 오류 처리

- 부팅 시 설정 오류는 즉시 실패한다 — 환경 변수 누락은 **어느 키인지 이름을 대며** 기동을 중단해야 한다
- LLM 구조화 출력은 프롬프트 + Pydantic 검증 + **3회 재시도**를 쓴다. OpenRouter 경유라 Anthropic 네이티브 출력 형식을 쓸 수 없다
- 열거형마다 CHECK 제약을 둔다 (`source_type` · `category` · `confidence` · `verification_status` · `role` · `kind`). `jobs.type`만 의도적 예외다
- 부분 유니크 인덱스가 "`target_type`당 기본 템플릿 정확히 하나"를 강제한다
- 트리거가 구조적 불변식을 지킨다 — `add_owner_as_member`, `protect_owner_membership`
- 재시도/데드레터는 큐의 책임이다. 지수 백오프 `base * 2^(attempts-1)`, `p_max_backoff`로 상한

## 로깅

- 구조화 로깅은 `packages/core/src/nexuswiki_core/logging.py`가 소유하고 `apps/api`와 `apps/worker`가 함께 쓴다
- SQL 쪽 진단은 별도 채널로 로깅하지 않고 `jobs.last_error`에 `[reaped]` 표시와 함께 덧붙인다
