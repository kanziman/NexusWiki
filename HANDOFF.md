# 🤝 Handoff Document

- **작성 일시**: 2026-08-16 (이번 세션 종료 시점)
- **작업 브랜치**: main

## 🎯 1. 작업 목표 & 현재 상태

- **목표**: "마일스톤 2" 대시보드 재설계를 위해 `docs/design-systems/`에 쌓이는 페이지별 PRD/시안을 리뷰하며 스코프를 좁히는 세션. 이번 세션에서 상세 리뷰한 문서: `source-management-prd.md`, `wiki-document-reader-prd.md`(더보기 메뉴), `backlog-management-prd.md`, `templates-management-prd.md`, `workspace-settings-prd.md`, 그리고 신규 기능으로 새로 설계한 `public-sharing-prd.md`(공개 위키 공유, 8라운드 이상 반복 설계).
- **진행률**: 순수 리뷰/설계 논의. 코드 변경 없음. 유일한 커밋은 세션 시작 시 이전 세션 HANDOFF 갱신(`4d947ae`, docs 전용).
- **⚠️ 중요 발견**: 세션 도중 동시 편집 중인 peer 세션(`nexuswiki-7e`)이 `docs/design-systems/PRODUCT-INVARIANTS.md`를 새로 만들었다. 이 문서가 **"재컴파일 수동 버튼 없음"**, **"공개 URL 네임스페이스 충돌 방지"** 등 이번 세션에서 반복적으로 지적했던 결정들을 정확히 담고 있다 — 즉 peer 세션이 이 대화의 결론과 수렴 중이거나 이미 같은 결론에 도달해 있다. **다음 세션은 개별 PRD를 다시 훑기 전에 `PRODUCT-INVARIANTS.md`부터 읽을 것** — 이제 이게 단일 진실 공급원 역할을 하는 것으로 보인다. `docs/design-systems/v2/`에 통합 mockup 6개(HTML, ask-conversation/google-auth/source-management/wiki-document-reader/workspace-home/workspace-settings)도 새로 생겼다 — 실제 "v2" 화면 작업이 여기서 진행 중인 것으로 보인다.
- **🔴 저장소 상태 경고**: `.planning/` 디렉토리 하위 **227개 파일이 working tree에서 삭제된 상태**(`git status`상 `D`, 아직 스테이징 안 됨)다. 이 세션에서 내가 지운 적 없음 — peer 세션 또는 사용자가 외부에서 한 작업으로 추정. 사용자가 세션 초반에 "되돌리고 마일스톤2로 새롭게 구성할거야"라고 한 것과 시점이 맞아떨어지고, `PRODUCT-INVARIANTS.md`/`v2/` 신설과 함께 보면 **의도적인 마일스톤1 계획 문서 정리로 추정**되지만 확실친 않다. 다음 세션은 `git status`로 재확인 후, 의도된 게 맞는지 사용자에게 확인하고 나서 커밋(또는 복구)할 것 — 임의로 커밋하거나 되돌리지 말 것.

## ✏️ 2. 주요 변경 사항 & 의사결정 (Why)

### 공개 위키 공유 기능 (`public-sharing-prd.md`) — 이번 세션 핵심 작업, 8라운드 이상 반복 설계로 수렴

최초 제안(3단계 공개 범위 + 비로그인 권한표)부터 시작해 다음 순서로 문제를 하나씩 좁혀갔다:
1. **anon RLS 아키텍처 자체가 빠져있음** 지적 → 이 프로젝트는 원래 `anon`이 전 정책 차단 상태라, "공개"는 UI 토글이 아니라 새 RLS 설계가 필요하다는 걸 못박음.
2. **공개 Ask 차단** — 워크스페이스 기본 예산이 `monthly_budget_micros` 기본 $5/월임을 확인(`0009_pipeline_ops.sql`), 비로그인 Ask는 예산 남용 벡터라 전면 차단으로 확정.
3. **이중 Citation 딜레마** — `source_chunks`를 통째로 열면 비공개 소스 유출, 막으면 공개 위키 인용이 빈 껍데기. → **"승인 인용 스냅샷" 모델**로 해결: 컴파일 시점 인용 스니펫만 별도 저장, 원본 테이블은 절대 열지 않음.
4. **스냅샷 생명주기** — 재인덱싱/소스삭제로 원본이 바뀌어도 공개 스냅샷은 안 바뀌어야 함(그렇지 않으면 인용 드리프트가 공개된 채로 발생) → 재컴파일 시 자동 교체 안 하고 "stale 배너 + 재검토 유도"로 설계.
5. **인간 검토 게이트** — LLM이 고른 인용 구간(호스트명/시크릿 등)이 사람 확인 없이 공개되는 걸 막기 위해, 최초 발행/재발행 모두 **스니펫 단위 [✅ 승인/❌ 제외] 모달 필수** 확정. "재발행"이 블라인드 원클릭이 되지 않도록 명시.
6. **verification_status 오염 방지** — "공개 승인" 클릭이 내부 `verified` 배지를 자동으로 켜거나(신뢰 배지 희석) `stale`로 되돌리면(`compile.py`가 명시적으로 보호하는 불변식과 충돌) 안 됨 → `verified`는 공개 신청의 **사전 게이트로만** 쓰고, 재검토 필요 여부는 `wiki_pages.updated_at > wiki_page_publications.published_at` 비교(기존 트리거 재사용)로 판정 — 새 컬럼/enum 값 없이 해결.
7. **테넌트 격리** — `wiki_page_publications`는 이 프로젝트의 복합 FK 관행(`FOREIGN KEY (wiki_page_id, workspace_id) REFERENCES wiki_pages(id, workspace_id)`)을 정확히 따르도록 수정.
8. **RLS 킬스위치의 실제 작동 문제** — `EXISTS (SELECT 1 FROM workspaces ...)` 서브쿼리는 `anon`이 `workspaces`에 아무 정책도 없어서 **항상 0행을 반환**한다는 걸 실제 PostgreSQL RLS 의미론으로 짚어냄(교차 테이블 서브쿼리도 조회 주체의 RLS를 그대로 받음). SECURITY DEFINER 함수 대안 제시(EXECUTE grant 필요 지적 포함) → 사용자가 "테이블 분리는 어떤가" 역제안 → **`workspace_public_settings` 사이드카 테이블**(민감 컬럼과 물리적으로 분리, `anon`이 이 테이블 전체를 봐도 안전)로 최종 확정. 이게 `wiki_page_publications`와 같은 1:1 사이드카 패턴이라 구조적으로 일관됨.
9. **최종 산출물**: `docs/design-systems/public-sharing-prd.md` — 위 모든 수정사항이 정확히 반영된 상태로 확인함. 남은 것: (a) 권한 매트릭스에 "재컴파일 트리거"가 여전히 4번째로 잘못 남아있음(→ `PRODUCT-INVARIANTS.md`로 이미 정정된 걸로 보임, 재확인 필요), (b) editor 레벨에서 공개 승인 가능한 게 의도된 신뢰 위임인지 미확인(owner만 킬스위치를 켤 수 있는 것과 비대칭), (c) URL 충돌(`/p/[slug]` 전역 vs 워크스페이스 스코프)과 공개 그래프 뷰어 정보 유출 문제는 이 DB 중심 문서 스코프 밖 — UX PRD 쪽에 아직 반영 안 됨(다만 `PRODUCT-INVARIANTS.md` 2절이 이미 URL 네임스페이스 충돌 방지를 다루고 있어 보임, 확인 필요).

### 그 외 PRD별 결정 (자세한 내용은 대화 기록 참고, 요지만)

- **source-management**: 재컴파일 버튼 삭제(기존 `JobStepper` dead-job 재시도와 중복), 재인덱싱은 `···` 메뉴로 격하, 소스 삭제 시 영향 위키에 **자동으로**(사용자 버튼 아님) compile job 재큐잉.
- **wiki-document-reader**: 위키 삭제는 기존 `wiki_links` red-link 메커니즘이 실제로 뒷받침(안전), "아카이브/삭제" 문구 정리 필요, 버전 이력은 스코프 큼(→ 결국 공개 기능의 `wiki_page_publications`가 "발행본" 개념으로 부분적으로 흡수).
- **backlog-management**: 소스삭제→백로그 전이는 source-management의 auto-recompile에 의존(구현 순서 있음), 커버리지 트렌드(%)는 시계열 스냅샷 없이 불가능.
- **templates-management**: Tab1(구조 템플릿) 삭제, compile 프롬프트 편집 기능은 보류, "100% 정합" 주장이 3개 항목 전부 거짓으로 판명(템플릿 키/model·temp·max_tokens 컬럼/on-prem 주장), **화면 전체를 이번 마일스톤에서 빼는 걸 권고**함(Supabase Studio로 충분) — 이후 실제로 파일이 디렉토리에서 사라짐(확인 필요, 우연일 수도 있음).
- **workspace-settings**: `SettingsMembersPanel.tsx`/`OperationsPanel.tsx`는 실재(이 계열 문서 중 처음으로 "100% 정합" 주장이 부분적으로 사실). RLS 정책 수는 38개 아니라 실제 27개. 예산 진행바는 API가 `authoritative: false`로 이미 표시 중. 워크스페이스 삭제 정책은 실재하나 확인 절차 언급 없음.
- **ask 프롬프트 4종(기존 기능)**: 손 안 댐 — 이미 실서비스에 구현되어 정상 동작 중. 외부에서 온 설명(`.replace()` 체이닝)이 실제 구현(정규식 단일 스캔, 프롬프트 인젝션 방어용)과 다르다는 것만 정정함.

### 반복적으로 발견된 패턴 (다음 세션이 새 PRD를 볼 때 계속 적용할 것)

1. **"확정(Validated)" 라벨은 신뢰할 수 없다** — 검증 가능한 구체적 주장(스키마 컬럼, 정책 개수, 파일 경로)은 매번 실제 코드/DB와 대조해야 함. 지금까지 3개 문서(source-management, templates-management, workspace-settings)에서 구체적 수치·이름이 틀렸음.
2. **Zero Emoji 원칙이 프로즈에서 반복적으로 깨짐** — `templates-management`, `source-management`, `wiki-document-reader`, `backlog-management`의 실제 preview.html까지 이모지 있었음. 반면 `workspace-home`, `workspace-settings`는 실제 mockup은 깨끗함(SVG 아이콘 사용, 프로즈만 이모지). 확인은 python3 정규식으로(`grep -P`는 이 머신 BSD grep에서 작동 안 함).
3. **"재컴파일 트리거"가 사용자 액션인 것처럼 4개 문서에 좀비처럼 계속 등장** — `PRODUCT-INVARIANTS.md`가 이제 이걸 명시적으로 금지 조항으로 박아둔 걸로 보임, 다음 세션에서 실제로 다 정리됐는지 확인.

## 🧪 3. 검증 상태

- 이번 세션은 리뷰/설계 논의 전용 — `pnpm test`/`typecheck`/`lint`/`build` 등 실행하지 않음.
- **미검증**: `workspace-home-preview.html`(이모지 없음만 확인, 상세 리뷰 안 함), `ask-conversation-preview.html`, `auth-google-prd.md`/`preview.html`, `public-wiki-reader-preview.html`, `docs/design-systems/v2/` 산하 6개 통합 mockup, `PRODUCT-INVARIANTS.md` 전문(2절 이후 못 읽음) — 전부 미검토.

## ⚠️ 4. 주의사항 & 남은 작업 (TODO)

- [ ] **`.planning/` 227개 파일 삭제가 의도된 것인지 확인** — 커밋도, 복구도 하지 말고 먼저 확인.
- [ ] `PRODUCT-INVARIANTS.md` 전문을 읽고, 이번 세션에서 지적한 "좀비 재컴파일 참조"와 "URL 네임스페이스 충돌"이 실제로 다 커버됐는지 대조.
- [ ] `public-sharing-prd.md`의 권한 매트릭스에서 "재컴파일 트리거" 문구 정리, editor의 공개 승인 권한이 owner 승인 없이 가능한 게 의도인지 확인.
- [ ] 지난 세션부터 이어진 핵심 질문 2개 여전히 미해결: **HHH-20(ContentViewer 통합) 되돌리기 여부**, **primary 색상 확정**(빨강→검정→새 시안 파랑) — `v2/` mockup들이 어떤 색을 쓰는지 다음 세션에서 확인.
- [ ] `docs/design-systems/v2/` 통합 mockup 6개, `auth-google-*`, `public-wiki-reader-preview.html` 아직 리뷰 안 함.
- [ ] `templates-management-prd.md`/`preview.html`이 실제로 삭제됐는지, 의도적인지 확인(디렉토리에서 사라진 걸 확인했으나 이유는 미확인).
- **주의사항**: `docs/design-systems/`는 계속 다른 세션이 동시 편집 중이다 — 이 문서에 적힌 파일 목록/내용은 스냅샷일 뿐, 다음 세션은 `ls docs/design-systems/`부터 다시 확인할 것.

## 🚀 5. 다음 세션 재개 안내

다음 세션 시작 시 `/catchup` 스킬을 실행하거나 아래 멘트를 입력하세요:
> "HANDOFF.md 확인하고, `.planning/` 삭제 상태랑 `PRODUCT-INVARIANTS.md` 먼저 확인한 다음 남은 작업 이어서 진행해줘."
