# 🤝 Handoff Document

- **작성 일시**: 2026-08-16 (직전 작업 세션 기준)
- **작업 브랜치**: main

## 🎯 1. 작업 목표 & 현재 상태

- **목표**: Cairni 레퍼런스를 참고한 대시보드 정보 밀도 개선 논의에서 출발해, HHH-18(소스/위키 선택 레이아웃 불일치)·HHH-19(그래프 칩/캔버스 구분 안 됨)·HHH-20(Ask↔Wiki 통합 뷰) 세 건과, 구현 중 새로 발견한 HHH-21(primary 색상 빨강/검정 불일치)·HHH-22(그래프 메뉴 정리·Ask 화면 재점검)까지 총 5건을 AGENTS.md의 OpenSpec 워크플로우(propose→apply→verify→archive, Linear 연동)로 처리했다.
- **진행률**: 5건 전부 완료 — 구현·테스트·typecheck·lint·`pnpm build`·`openspec validate` 통과, archive 완료, Linear Done 갱신 완료, 커밋 5개(HHH-19/18/20/스크린샷 정리/HHH-21/HHH-22 — 정확히는 6커밋) 완료.
- **추가로**: 사용자 요청에 따라 `docs/design-systems/wiki-document-reader-prd.md` 및 연계 design-spec.md의 내부 모순(이모지 원칙 vs 이모지 표기, Midjourney 프롬프트 자체 모순)을 수정했다. 단, 이 두 파일은 **다른 세션이 동시에 편집 중**이라 커밋하지 않고 working tree에만 남겨뒀다.

## ✏️ 2. 주요 변경 사항 & 의사결정 (Why)

- **peer 세션 재작업 패턴 발견**: `366b90f` 커밋으로 archive된 `separate-graph-control-canvas`, `unify-source-wiki-selection-layout`, `unify-dashboard-design-system` change 3건이 전부 "완료"로 표시돼 있었지만, 실제 코드를 확인하니 요구사항이 충족되지 않았다(그래프 캔버스 배경 미적용, 소스/위키 선택 상호작용 모델 여전히 다름, primary 색상 빨강/검정 혼재). 기존 스펙은 재사용하고 "실제로 안 끝난 부분"만 마저 구현하는 후속 change로 처리했다(HHH-19, HHH-18, HHH-21).
- **`apps/dashboard/components/GraphCanvas.tsx`**: 캔버스 wrapper에 `--nw-canvas` 배경 부여(HHH-19) + 마인드맵 탭용 `layoutName`/`rootSlug` prop 추가(HHH-20, `wiki_links` 데이터 재사용해 `breadthfirst` 레이아웃).
- **`apps/dashboard/components/SourcesList.tsx` + 신규 `app/w/[workspaceId]/sources/[id]/page.tsx`**: 아코디언 인라인 펼치기를 `WikiLibrary`와 동일한 "행 → 실제 라우트" 패턴으로 통일(HHH-18).
- **`/ask` 통합 워크스페이스 뷰어(HHH-20)**: `AskConversation` + 신규 `ContentViewer`(위키 문서/원시 소스/2D 그래프/마인드맵 4탭, `?tab=&slug=&chunkId=&category=` 쿼리 파라미터가 상태)를 좌우로 배치. `/wiki/[slug]`, `/graph`는 `redirect()`로 흡수(존재 확인 로직은 그대로 유지 후 redirect). 위키 조회 로직은 `lib/wiki-lookup.ts`로 추출해 라우트와 뷰어가 공유. 인용 마커 클릭이 `CitationSidePanel` 오버레이 대신 뷰어 탭 전환으로 이어짐(컴포넌트는 삭제 안 함).
- **`apps/dashboard/app/globals.css`(HHH-21)**: `--color-primary` 등을 `.nw-action`(검정)으로 재배선. **중요 트러블슈팅**: 처음엔 `@theme` 블록 안에서 재배선했으나 컴파일된 CSS를 직접 확인해보니 효과가 없었다 — Tailwind v4의 `@theme`은 `@layer theme`으로 컴파일되고, CSS Cascade Layers 규칙상 레이어 없는(unlayered) 규칙이 항상 이겨서 `design-tokens.css`(Airbnb 파일)의 unlayered `:root`가 계속 이겼다. `globals.css`의 기존 plain `:root` 블록(`--font-family-base` 오버라이드가 쓰던 자리)으로 옮겨서 해결했다.
- **NavShell/AskConversation 정리(HHH-22)**: `/graph`가 리다이렉트만 하게 되면서 죽은 링크가 된 "그래프" 메뉴 제거, `handleMarkerClick`의 위키 조회에 `workspace_id` 스코프 추가, `ContentViewer` 탭에 `aria-controls`/`role="tabpanel"`/roving tabIndex/방향키 이동 구현.
- **또 다른 트러블슈팅(false alarm)**: HHH-22 조사 중 `ask/page.tsx`의 `h-[calc(100vh-var(--spacing-xxl)*2)]`가 이 코드베이스가 두 번 기록한 "WINDOWS #11"(커스텀 `--spacing-*` 토큰과 Tailwind 유틸리티 충돌) 위반이라 의심했으나, `.planning/STATE.md`의 원본 기록을 재확인하고 빌드된 CSS를 파싱해보니 그 버그는 **이름 있는** 유틸리티(`max-w-xl` 등)에만 해당하고 arbitrary-value 문법(`h-[...]`)은 무관함을 검증했다. 코드는 되돌렸다.
- **openspec CLI 재설치**: 이 머신에 `openspec`이 없어 `npm install -g @fission-ai/openspec@latest`로 설치했다(peer 세션이 CLI 없이 손으로 change를 작성했던 게 "완료 표시되었지만 검증 안 됨" 문제의 근본 원인으로 추정됨).

## 🧪 3. 검증 상태

- **완료된 검증** (5개 change 전부 동일 절차):
  - `apps/dashboard`: `pnpm test` — 최종 121 tests / 31 test files 전부 통과
  - `apps/dashboard`: `pnpm typecheck`, `pnpm lint` 클린
  - `apps/dashboard`: `pnpm build`(production build) 성공 — CSS cascade 문제(HHH-21)와 WINDOWS #11 false alarm(HHH-22)을 컴파일된 `.next/static/css/*.css`를 직접 파싱해 검증하는 데 사용
  - `openspec validate <change> --strict` 5건 전부 통과, `openspec validate --specs` 13개 스펙 전부 통과
  - Linear HHH-18/19/20/21/22 전부 Done 상태 갱신 확인(update_issue 응답으로 성공 확인)
- **미검증 항목**: 이번 세션 내내 **브라우저 실사용 검증을 못 했다** — 로컬 dev 서버(3000번)가 클라우드 Supabase(`dajhhwbkfdaqnuenulsb.supabase.co`)를 바라보는데 이 세션엔 로그인 자격 증명이 없었다. 사용자가 "정적 검증만으로 진행"을 승인해 테스트/빌드로 대체했지만, 실제 화면에서 그래프 배경 분리·소스 상세 라우트·통합 뷰어 4탭·primary 색상·탭 키보드 내비게이션을 육안으로 확인한 적은 없다.

## ⚠️ 4. 주의사항 & 남은 작업 (TODO)

- [ ] **자격 증명 확보 후 브라우저 E2E 확인** — 위 "미검증 항목" 전체를 실제 화면에서 확인.
- [ ] `docs/design-systems/wiki-document-reader-prd.md`/`wiki-document-reader-design-spec.md` 수정 사항(이모지 자리표시자 설명, Midjourney 프롬프트 이모지 제거) — **커밋 안 됨**. 동시 편집 중이던 다른 세션의 작업과 합쳐서 커밋할지 확인 필요.
- [ ] `openspec/changes/refine-knowledge-preview-hierarchy/`(워크스페이스 홈 미리보기 재구성) — 다른 세션이 만든 propose 단계 change로 보임, 이번 세션에서 손대지 않음. apply 전이라 아직 코드 변경 없음.
- [ ] `docs/design-systems/ask-conversation-*`, `workspace-home-*` 문서들도 wiki-document-reader와 같은 배치로 생성된 미래 비전 문서로 보이며 아직 검토 안 함.
- **주의사항 1**: 이 저장소는 동시에 다른 Claude 세션이 작업할 수 있다(`ListAgents`로 peer 세션 존재 확인됨). archive된 OpenSpec change가 "완료" 표시라고 실제로 구현이 끝났다고 믿지 말 것 — 이번 세션에서만 3건이 거짓 완료였다. 코드를 직접 재확인하는 습관이 필요하다.
- **주의사항 2**: `apps/dashboard/app/globals.css`에 `--color-*`(Airbnb `design-tokens.css` 유래)와 `--nw-*`(quiet editorial, 실제 소스) 두 토큰 체계가 병존한다. `--color-primary` 계열은 이번 세션에 `--nw-action`으로 재배선했지만, `--color-canvas`/`--color-ink`/`--color-muted` 등 나머지는 그대로다 — 새 UI를 짤 때 어느 쪽이 실제로 이기는지(unlayered `:root` 소스 순서) 컴파일된 CSS로 검증하는 버릇을 들일 것.
- **주의사항 3**: 로컬 `openspec` CLI는 `npm install -g @fission-ai/openspec@latest`로 이미 설치돼 있다(이 세션에서 설치함) — 다음 세션은 재설치 불필요, `openspec --version`으로 확인만 하면 됨.

## 🚀 5. 다음 세션 재개 안내

다음 세션 시작 시 `/catchup` 스킬을 실행하거나 아래 멘트를 입력하세요:
> "HANDOFF.md 확인하고 남은 작업부터 이어서 진행해줘."
