## Why

작성 대기 백로그 화면은 결손 주제를 세고 정렬하지만, **그 주제가 무엇인지 정확히 말해 주지 못한다.**

표시 제목이 `target_slug`의 하이픈을 공백으로 되돌린 값이다. `slugify`는 되돌릴 수 없는 방식으로 lossy하다 — `normalize`가 casefold하고, `_DISALLOWED`가 `[0-9a-z가-힣-]` 밖의 문자를 전부 지우며, 충돌 시 `-2` 접미가 붙고, 허용 문자가 하나도 남지 않으면 `page-<sha256[:12]>`로 떨어진다. 마지막 경우 화면에는 `page a1b2c3d4e5f6`이 뜬다. 이것은 근사값이 아니라 오표시다.

원문 표기는 저장되지 않지만 **복원할 수 있다.** 링크를 품은 위키 본문에 `[[표기]]`가 그대로 남아 있기 때문이다. 같은 조회로 `backlog-management-prd.md` §3.3이 요구하는 인용 문맥 발췌도 함께 얻는다 — 그래서 두 결손을 하나의 change로 묶는다.

용어:
- **백로그 주제**: `to_wiki_id IS NULL`인 `wiki_links`를 `target_slug`로 접은 단위.
- **표기(display title)**: 인용 문서 본문의 `[[...]]` 안에 사람이 쓴 원문 문자열. `target_slug`와 달리 대소문자·문장부호를 보존한다.
- **인용 문맥(excerpt)**: 인용 문서 본문에서 `[[target]]` 주변을 잘라낸 스니펫. 저장하지 않고 조회 시점에 만든다.

## What Changes

- 백로그 목록의 표시 제목이 slug 역변환 대신 **인용 문서에서 복원한 원문 표기**를 쓴다. 표기를 찾지 못하면 기존 역변환으로 폴백한다.
- 백로그 행을 열면 **상세 패널**이 주제·최초 감지 시각·인용 중인 위키 목록·인용 문맥 발췌·소스 추가 동선을 보여준다.
- 발췌는 **서버에서** 만든다. 위키 본문 전체는 클라이언트로 내려가지 않는다.

## Capabilities

### Modified Capabilities

- `backlog-ask`: 백로그 집계가 주제마다 복원된 표기와 인용 문맥을 함께 제공한다. 목록은 여전히 인용 빈도 내림차순이며 쓰기 액션은 추가되지 않는다.

## Impact

- `apps/dashboard/app/w/[workspaceId]/backlog/page.tsx` — `wiki_pages.content`를 함께 읽고 표기·발췌를 서버에서 계산한다.
- `apps/dashboard/components/BacklogList.tsx` — 표시 제목 출처가 바뀌고 상세 패널이 붙는다.
- `docs/design-systems/v2/nexuswiki-design-system.css` 섹션 17 — 상세 패널 조판.
- `apps/dashboard/tests/BacklogList.test.tsx` — 표시 제목과 패널 계약.
- 스키마 변경 없음. 새 API 엔드포인트 없음.
