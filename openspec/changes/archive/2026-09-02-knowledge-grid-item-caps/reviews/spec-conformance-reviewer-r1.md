# Spec Conformance 리뷰 — knowledge-grid-item-caps r1

- 판정: pass
- 대상: `git diff origin/main` (작업 트리 미커밋 변경분, base `b274d46`)
- 일시: 2026-09-02T13:13:32Z
- 검토 범위: `apps/dashboard/components/KnowledgeGrid.tsx`, `apps/dashboard/tests/KnowledgeGrid.test.tsx`, `openspec/specs/workspace-home-dashboard/spec.md`

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Two-column knowledge grid / Populated wiki and backlog display | 충족 | 상한 `MAX_WIKI_PAGES = 5` · `MAX_BACKLOG_ITEMS = 4` `KnowledgeGrid.tsx:60-61`, 적용 `:76-77`. 카테고리 뱃지 `:114-117,139-141`, 검증 뱃지 `:121-127,143-156`, 인용 수 뱃지 `:128,157-165`. 백로그 인용 수 `:219,244-246`, 소스 연결 CTA `:248-254`. 테스트 `KnowledgeGrid.test.tsx:42-59`(뱃지·CTA), `:137-173`(5/4 상한) |
| Two-column knowledge grid / Empty state display | 충족 | 위키 빈 상태 `KnowledgeGrid.tsx:107-112`(카테고리 필터 문구 분기 포함), 백로그 빈 상태 `:212-215`, 상시 노출되는 원문 연결 콜아웃 `:262-282`(`소스 연결` → `/w/<id>/sources`). 테스트 `KnowledgeGrid.test.tsx:124-135` |
| Two-column knowledge grid / Member follows a backlog source-connection CTA | 충족 | `href={`${base}/sources?prefillTitle=${encodeURIComponent(displayTitle)}&tab=text`}` `KnowledgeGrid.tsx:248-250`. 테스트 `KnowledgeGrid.test.tsx:52-55`(`/w/ws-1/sources?prefillTitle=cache-layer-strategy&tab=text`), 모달 경로도 동일 계약 `:100-107` |
| Two-column knowledge grid / Workspace has more items than the home grid shows | 충족 | 상한 초과 시에도 `slice` 로만 자르고 `KnowledgeGrid.tsx:76-77`, 위키 열 전용 링크 `:96-103`(`${base}/wiki`, `data-od-id="view-all-documents"`), 백로그 열 전용 링크 `:201-208`(`${base}/backlog`, `data-od-id="view-all-backlog"`). **새 단언 존재** — `KnowledgeGrid.test.tsx:178-183` 이 두 링크의 `href` 를 15/12건 시나리오 안에서 직접 검사한다. 전용 화면은 별도 상한이 없어 나머지 항목에 실제로 도달 가능하다(`app/w/[workspaceId]/wiki/page.tsx` · `backlog/page.tsx` 에 `limit`·`slice`·`range` 없음) |
| 요구사항 본문 / 카테고리 라벨 매핑 | 충족 | `CATEGORY_LABELS` = `concepts 개념 · entities 엔티티 · guides 가이드 · maps 맵` `KnowledgeGrid.tsx:53-58`, 렌더 `:115-117,139-141`, 미분류 폴백 `:117`. 테스트 `KnowledgeGrid.test.tsx:44`(`개념`), 필터 동작 `:110-122` |
| 요구사항 본문 / 비대칭 데스크톱 위계(위키가 더 넓음) | 충족 | 루트에 `className="sections"` 유지 `KnowledgeGrid.tsx:80`, 그리드 정의 `docs/design-systems/v2/nexuswiki-design-system.css:996-1003`(`minmax(0,1.4fr) minmax(0,1fr)`). 카드형 리디자인이 이 클래스를 제거하지 않았다 |
| 정본 동기화 | 충족 | `openspec/specs/workspace-home-dashboard/spec.md:76-92` 가 delta 와 문자 단위로 일치(5/4 상한 + 전용 화면 링크 문장 + 신규 시나리오). `openspec validate --specs --strict` = 34 passed |

## 조치가 필요한 항목

없다. delta spec 시나리오 4개와 요구사항 본문 문장이 모두 코드·테스트 증거로 충족된다.

## 참고 관찰 (판정에 영향 없음, 후속 결정 대상)

1. **검증 뱃지 노출 게이트 제거** — 이전에는 `verified || disputed || expired` 일 때만 뱃지를 그렸으나(구 `KnowledgeGrid.tsx` 의 `{(verified || disputed || expired) && …}`), 리디자인 후 `KnowledgeGrid.tsx:143-156` 은 항상 `verificationLabel(page)` 을 렌더링한다. 즉 미검증 문서 행에 `검증 필요` 가 새로 보인다. 정본 요구사항은 "verification badge" 만 요구하므로 **스펙 위반은 아니며**, 오히려 문장의 문자적 독해에 더 가깝다. 다만 이는 이 change 의 delta 에 없는 사용자 관찰 가능 변화이고, `openspec/changes/archive/2026-08-21-dashboard-layout-density/design.md:66` 이 "PRD 를 고칠지 여기를 되돌릴지는 사람의 결정 사안으로 남긴다" 며 미결로 남겨 둔 항목과 맞닿는다. 함께 삭제된 해당 근거 주석의 결론은 이제 `docs/design-systems/v2/workspace-home-prd.md` §3.3 둘째 절과 전면 충돌한다 — PRD 문장을 갱신하거나 결정 기록을 어딘가에 남기는 편이 좋다(다음 change 의 문서 정리 범위로 충분하다).
2. **백로그 섹션 문구 변경** — 제목 `작성 대기 백로그` → `지식 공백 (작성 대기 백로그)` (`KnowledgeGrid.tsx:195`), 전용 화면 링크 라벨 `전체 보기` → `보완하기` (`:206`). 전용 화면 `BacklogList.tsx:72` 의 `h1` 은 `미완성 백로그` 라 세 이름이 공존한다. `dashboard-design-consistency` 스펙의 동일 라벨 요구는 "underlying status value" 에 걸린 것이라 내비게이션 라벨에는 직접 걸리지 않고, 이름 불일치 자체는 이 브랜치 이전부터 있었다. 이 change 의 판정 대상은 아니다.

## 판정 근거

delta spec 이 MODIFIED 한 요구사항의 네 시나리오 모두 구현·테스트 증거가 있다. 특히 이번에 추가된 `Workspace has more items than the home grid shows` 는 단언이 실제로 존재하며(`KnowledgeGrid.test.tsx:178-183`), 링크를 지우면 테스트가 깨지도록 `data-od-id` 로 고정돼 있어 "상한만 낮추고 도달 경로는 조용히 잃는" 회귀를 막는다. tasks.md 의 `- [x]` 주장도 모두 대응 증거가 있고, 재실행한 검증 — `pnpm vitest run`(381 passed / 0 failed), `pnpm typecheck`(무출력 성공), `pnpm lint`(No issues found), `openspec validate --specs --strict`(34 passed) — 이 전부 통과했다. 함께 들어온 카드형 리디자인은 요구사항이 규정한 뱃지·CTA·비대칭 그리드·카테고리 매핑을 모두 보존하므로 범위 축소나 계약 위반으로 볼 요소가 없다.
