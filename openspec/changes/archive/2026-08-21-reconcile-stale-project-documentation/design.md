## Context

`openspec/specs/`는 현재 제품·workflow 계약을 보유하고 있지만, GSD 단계에서 만든 root checklist와 일부 무기한 현재 문서는 여전히 자신을 활성 작업·결정 원장으로 설명한다. 동시에 `0017_wiki_bookmarks.sql`, 공개 공유 구현, 현재 queue 함수처럼 코드에서 확인되는 사실이 reference 문서에 반영되지 않았다. 동기화 대상은 hand-written 문서이므로 구조를 재생성하지 않고 실패한 주장만 교정해야 한다.

## Goals / Non-Goals

**Goals:**

- 현재 상태를 설명하는 문서가 코드와 canonical OpenSpec을 우선 출처로 가리키게 한다.
- GSD checklist의 결정·검증 기록은 보존하면서 진행 상태가 현재 상태로 오인되지 않게 한다.
- 위키·QA가 역사 자료와 현재 계약을 구분할 수 있는 명시적인 lifecycle 표지를 제공한다.
- 변경한 모든 사실 주장을 저장소의 파일, 마이그레이션, 테스트 또는 canonical spec으로 검증한다.

**Non-Goals:**

- 제품 동작, API, 데이터 모델 또는 OpenSpec 요구사항을 변경하지 않는다.
- 날짜가 붙은 `docs/ops/`, `docs/reviews/`, architecture snapshot을 현재 시점으로 다시 쓰지 않는다.
- 모든 구현 전 PRD를 사후 명세로 재작성하지 않는다. 이번 change는 활성 원장 충돌과 현재 reference의 명백한 사실 오류를 우선 정리한다.
- root checklist의 과거 task 상태를 완료 상태로 소급 변경하지 않는다.

## Decisions

### 1. 문서를 `current reference`, `historical snapshot`, `design baseline`으로 구분한다

- `.claude/CLAUDE.md`, `README.md`, `docs/reference/*`, `PRODUCT-INVARIANTS.md`, 무기한 `docs/architecture/index.html`은 현재 주장을 제공하므로 코드와 OpenSpec에 맞춘다.
- `checklists.json`과 `checklists_v2.json`에는 기계 판독 가능한 `document_status`를 추가해 `historical_snapshot`임을 표시하되 기존 task·decision·verification 데이터는 보존한다.
- 날짜가 붙은 증거·검토 문서는 작성 당시 사실을 보존한다.

대안으로 checklist를 이동하거나 삭제할 수 있지만, 기존 코드 주석과 역사 문서의 참조를 깨뜨리고 QA 근거를 잃으므로 채택하지 않는다.

### 2. 활성 원장은 기존 canonical workflow 계약을 인용한다

현재 작업 상태와 우선순위는 GitHub Issues + `kanziman` Project #1, 기능·workflow 계약은 `openspec/specs/`, change 단위 설계 결정은 해당 `design.md`를 정본으로 안내한다. `.claude/CLAUDE.md`와 `docs/reference/conventions.md`에 세부 규칙을 다시 복제하지 않고 governing spec 경로를 인용한다.

별도 delta spec은 만들지 않는다. 이 change는 이미 존재하는 workflow 요구사항을 문서에 반영할 뿐 요구사항을 바꾸지 않는다.

### 3. hand-written 문서는 surgical update만 허용한다

문서 업데이트 스킬의 보존 원칙에 따라 파일 전체 재생성, 목차 재구성, 문체 통일을 하지 않는다. 다음 manifest의 stale 주장과 직접 연결된 문장·표·상태 표지만 수정한다.

| 영역 | 대상 | 교정 내용 |
| --- | --- | --- |
| 원장 | `.claude/CLAUDE.md`, `docs/reference/conventions.md` | `HANDOFF.md`와 checklist 활성 원장 지시 제거, governing spec 인용 |
| 역사 표시 | `checklists.json`, `checklists_v2.json` | lifecycle·대체 출처 metadata 추가, 기존 기록 보존 |
| 현재 구조 | `docs/reference/architecture.md`, `docs/reference/stack.md` | migration `0017`, 13개 테이블, queue 함수와 문서 출처 정합화 |
| 제품 불변식 | `docs/design-systems/v2/PRODUCT-INVARIANTS.md` | slug·공개 공유 구현 상태, 테이블 수, 내부 UUID route 교정 |
| 현재 진입 문서 | `README.md`, `docs/architecture/index.html` | 중복 commit 계약 제거, 오래된 phase/checklist/HANDOFF 주장에 현재 출처 안내 |
| 디자인 상태 | `docs/design-systems/v2/nexuswiki-design-system.md` | 실제 미해결 TODO 개수와 요약 일치 |

### 4. 검증은 문서 유형별로 좁게 실행한다

- 두 checklist는 UTF-8 JSON parse를 검증한다.
- migration·테이블·함수·route·TODO 수는 `supabase/migrations/`, `apps/`, 문서 본문 검색 결과와 대조한다.
- 활성 문서에서 제거 대상인 `HANDOFF.md` 및 checklist 원장 지시가 남지 않았는지 검색한다.
- Markdown 상대 링크를 검사하고 `openspec validate reconcile-stale-project-documentation --strict`를 새로 실행한다.
- 제품 코드가 바뀌지 않으므로 전체 제품 test/typecheck/lint 대신 문서에 직접 관련된 검증만 실행한다.

## Risks / Trade-offs

- [역사 checklist의 `pending` 값이 검색 결과에 계속 노출될 수 있음] → root-level `document_status`와 현재 문서 안내에서 snapshot임을 명시하고 QA ingestion이 lifecycle을 우선하도록 한다.
- [구현 전 PRD 일부가 계속 과거 상태를 설명함] → 이번 change에서 이를 design baseline으로 분류하고, 현재 사실을 단정하는 상위 문서만 교정한다. 필요하면 후속 change에서 PRD별 lifecycle banner를 추가한다.
- [HTML architecture 문서를 전면 최신화하면 큰 diff와 새 오류가 생김] → 오래된 도표를 재작성하지 않고 상단에 snapshot 표지와 현재 canonical 링크를 추가하며 명백한 활성 원장 문구만 제거한다.
- [문서에 workflow 규칙을 재복제해 다시 어긋날 수 있음] → 설명은 최소화하고 canonical spec 경로를 직접 인용한다.

## Migration Plan

1. 활성 원장 참조와 checklist lifecycle metadata를 교정한다.
2. 코드로 확인되는 reference·제품 문서의 사실 오류를 교정한다.
3. JSON·경로·수치·링크·OpenSpec strict validation을 실행한다.
4. 검증된 task만 완료 처리하고, 문서 변경을 별도 PR로 발행한다.

Rollback은 이 change의 문서 commit을 revert하면 된다. 데이터나 런타임 migration은 없다.
