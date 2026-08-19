# Spec Conformance 리뷰 — add-backlog-topic-context r1

- 판정: pass
- 대상: `git diff main...HEAD` (범위 확인용으로는 `b1e1473~1..c256c64` 4커밋만 대조, HEAD `c256c64`)
- 일시: 2026-08-19T00:00:00+09:00

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Unresolved red-link backlog aggregation and sorting / Member views backlog list | 충족 | `apps/dashboard/app/w/[workspaceId]/backlog/page.tsx:67-183`(집계·impact·first_detected_at·referencing_pages 계산) · `apps/dashboard/components/BacklogList.tsx:199-211`(impact·최초 감지 렌더), `:180-197`(doc-chips) · 테스트 `apps/dashboard/tests/BacklogList.test.tsx:18-86` |
| Unresolved red-link backlog aggregation and sorting / Referencing bodies spell a topic differently | 충족 | `resolveDisplayTitle`(`page.tsx:21-43`)이 페이지를 제목 오름차순(`page.tsx:152-154`, `localeCompare("ko")`)으로 순회해 페이지당 첫 표기를 모으고, 최빈값을 구한 뒤 `spellings.find`로 배열(=제목 오름차순) 상 첫 등장을 반환 — 동수 tie-break가 "제목이 가장 앞선 문서의 표기"와 정확히 일치. 테스트로 최빈값 케이스(`tests/backlog-page-route.test.tsx:154-192`)와 동수 tie-break 케이스(`:194-226`, 대소문자만 다른 "Auth Flow" vs "AUTH FLOW")를 모두 검증 |
| Unresolved red-link backlog aggregation and sorting / No original spelling survives in any referencing body | 충족 | `page.tsx:155-157`(`resolveDisplayTitle` null이면 `deslugify` 폴백) · `BacklogList.tsx:176`(`target_slug` 보조 줄에 항상 병기, 표기 유무와 무관) · 테스트 `tests/backlog-page-route.test.tsx:228-246`, `tests/BacklogList.test.tsx:166-183` |
| Backlog topic detail panel / Member opens a backlog topic | 충족 | `BacklogList.tsx:169-177`(행 트리거) → `240-313`(Radix Dialog에 display_title·target_slug·first_detected_at·referencing_pages·excerpt 렌더) · 테스트 `tests/BacklogList.test.tsx:209-237` |
| Backlog topic detail panel / Detail panel renders reference markup | 충족 | `lib/wiki-links.ts:177-218`(`firstWikiLinkExcerpt`가 본문을 완전 평문으로 펼친 뒤 window를 자름 — 브래킷이 새 나갈 수 없는 구조) · `firstWikiLinkSpelling`(`:145-156`)도 정규식 캡처 그룹만 반환해 브래킷 미포함 · 테스트 `tests/wiki-links.test.ts:184-193`(window 안 다른 `[[...]]` 섞여도 브래킷 없음), `tests/backlog-page-route.test.tsx:248-271`(`toContain`/`not.toContain("[[")`) |
| Backlog topic detail panel / Member requests source ingestion from the detail panel | 충족 | `BacklogList.tsx:300-307`(패널 소스 추가 링크가 목록 행 `218-225`와 동일한 URL 패턴) · 테스트 `tests/BacklogList.test.tsx:232-236` |

## 부가 확인 (요청 항목 3 — 본문 비전달)

- `page.tsx:159-176` 주석과 실제 코드가 일치: `contentByPageId`(원문 본문)는 서버 함수 내부에서만 소비되고, `BacklogItem`/`BacklogReferencingPage`(`BacklogList.tsx:11-27`)에는 `display_title`·`excerpt` 같은 계산된 문자열만 있다. `content` 필드 자체가 타입에 없음.
- 테스트 `tests/backlog-page-route.test.tsx:292-314`가 `JSON.stringify(props)`에 원문 전체(`fullBody`)와 `"content"` 문자열이 없음을 직접 확인 — "서버가 만든 스니펫만 내려간다" 요구를 코드가 아니라 실제 직렬화 결과로 검증하고 있어 증거 강도가 높음.
- `page.tsx:95-101`이 `referringPageIds.length`가 0이면 `content` 조회 쿼리를 아예 내보내지 않음 — task 1.2의 "백로그가 비어 있으면 본문 조회가 발생하지 않는다"와 일치. 테스트 `tests/backlog-page-route.test.tsx:123-132`로 확인.
- `page.tsx:64`가 `createClient`(`@/lib/supabase/server`, 요청자 쿠키 세션)를 쓰고 `service_client`를 쓰지 않음 — `lib/supabase/server.ts:23-42` 확인.

## 실행 검증 (새로 실행, 재사용 안 함)

- `pnpm vitest run` — 46개 테스트 파일, 188개 테스트 전부 통과 (백로그 관련 3개 파일 포함)
- `pnpm typecheck` — 통과
- `pnpm lint` — 통과
- `openspec validate add-backlog-topic-context --strict` — valid
- `git diff b1e1473~1..c256c64 --stat`로 이 change의 실제 변경 범위가 proposal.md의 Impact 섹션과 정확히 일치함을 확인 (`page.tsx`, `BacklogList.tsx`, `wiki-links.ts`, 3개 테스트 파일, CSS 섹션 17, `tasks.md`, `openspec/specs/backlog-ask/spec.md`) — 스펙 밖 파일 변경 없음
- `openspec/specs/backlog-ask/spec.md`(정본) 동기화 diff가 delta spec(`openspec/changes/.../specs/backlog-ask/spec.md`)과 문자 그대로 일치 — sync 커밋이 요구사항을 누락·왜곡하지 않음

## 조치가 필요한 항목

없음.

## 판정 근거

델타 스펙의 두 Requirement, 다섯 Scenario 전부를 파일·줄 단위로 대조했고 각각에 대응하는 테스트가 있으며 전체 테스트 스위트가 새로 실행한 결과로 통과했다. 표기 결정 규칙(최빈값 → 위키 제목 오름차순 tie-break)은 `resolveDisplayTitle`의 배열 순회·`.find` 조합이 tie-break 정의와 정확히 일치하고, 동수 케이스를 별도로 시험하는 테스트(`tests/backlog-page-route.test.tsx:194-226`)가 존재해 "구현된 것 같다" 수준을 넘어선다. 상세 패널은 스펙이 요구하는 네 항목(표기·최초 감지 시각·인용 위키 목록·소스 추가 동선)을 전부 렌더하고, 발췌 로직은 브래킷을 원천적으로 만들 수 없는 구조(평문 재구성 후 window 절단)라 스펙이 우려하는 실패 모드(브래킷 노출·본문 전량 전달)가 구조적으로 차단돼 있다. tasks.md의 4개 완료 표시 모두 대응 코드와 테스트가 실재하며, 조용한 범위 축소나 스펙 밖 동작도 발견되지 않았다.
