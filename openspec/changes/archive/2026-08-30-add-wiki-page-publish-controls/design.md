## Context

공개 공유 사이드카·킬스위치·`/p/` 뷰어는 `openspec/specs/public-sharing/spec.md`가 이미 계약한다. 이 change는 그 발행본을 위키 리더에서 만들고 지우는 멤버 표면만 추가한다. 동기는 proposal.md를 본다.

검증 전이(`PATCH .../verify`)는 FastAPI `UserDb` 경로다. 발행 쓰기는 같은 사이드카를 설정 화면이 쓰듯이 요청자 세션 Supabase 클라이언트로 한다. 대시보드의 `NEXT_PUBLIC_API_URL`은 배포된 Railway API라, 미배포 FastAPI 라우트에 의존하면 리더 버튼이 404로 죽는다.

## Goals / Non-Goals

**Goals:**
- 위키 리더 한 곳에서 발행·링크 복사·발행 취소를 제공한다
- 쓰기는 요청자 JWT와 RLS만 사용하고, `published_by`는 클라이언트가 고르지 않는다
- 인용은 발행 시점 스냅샷으로만 저장한다. 공개 뷰어는 원문을 다시 조회하지 않는다

**Non-Goals:**
- 인용 스니펫 육안 검토 UI (PRD §4.2는 후속)
- `wiki_pages.updated_at > published_at` 재발행 배너
- 킬스위치 설정 UI·공개 셸(`.public-topbar`) 재설계. 본문 조판은 내부 리더와 같은 렌더러를 쓴다.
- 새 마이그레이션. `enforce_publication_verified`와 editor RLS가 이미 게이트다

## Decisions

### 1. 발행 쓰기는 대시보드 세션 클라이언트, FastAPI 라우트는 배포 계약
- **결정**: 리더는 `PublicSharingSettings`와 같이 요청자 세션으로 `wiki_page_publications`를 upsert/delete한다. `published_by`는 `auth.getUser().id`다. FastAPI `PUT`/`DELETE .../publication`은 격리 테스트와 이후 배포용으로 남긴다.
- **대안**: 리더가 FastAPI만 호출 → 로컬 UI가 프로덕션 API를 가리키는 현재 구성에서 미배포 라우트가 404가 된다.
- **대안**: Next.js server action → 같은 세션 쓰기인데 설정 화면 사이드카 경로와 갈린다.

### 2. 발행은 upsert, 취소는 해당 행 삭제
- **결정**: PUT은 기존 행이 있으면 스냅샷을 덮어쓰고, 없으면 insert한다. DELETE는 `wiki_page_id`+`workspace_id`로 한 행만 지운다. 리더는 발행 후 복사·취소만 보여 재발행 CTA는 두지 않는다.
- **대안**: POST insert-only → 중복 클릭이 23505로 떨어지며 소스 수집 duplicate 매핑과 섞인다.

### 3. `published_by`는 세션 사용자, 인용은 `wiki_pages.sources` 스냅샷
- **결정**: 폼에서 감사 필드를 받지 않는다. `auth.getUser().id`를 `published_by`로 넣는다. 인용은 같은 워크스페이스 `raw_sources.title`과 첫 청크 본문 앞부분을 `{anchor, source_title, snippet}`로 펼친다.
- **대안**: `published_by default auth.uid()` 마이그레이션 → 이 change 범위 밖의 스키마 변경이다.
- **대안**: 빈 `published_citations` → 공개 뷰어의 인용 섹션이 항상 비어 스펙의 "citation sources"를 충족하지 못한다.

### 4. 컨트롤은 `WikiPageContent` 한 곳
- **결정**: 독립 리더(`/w/.../wiki/[slug]`)와 Ask 인스펙터(`ContentViewer`)가 같은 컴포넌트를 쓰므로 헤더 컨트롤을 여기에만 둔다. 권한은 기존 `canVerify`(editor 이상)를 재사용한다.
- **대안**: 독립 리더에만 노출 → 인스펙터에서 같은 문서를 발행할 수 없다.

### 5. 공개 본문은 내부 리더와 같은 `WikiDocumentBody`
- **결정**: `/p/` 본문은 줄 단위 `<p>` 가 아니라 내부 리더와 같은 마크다운 렌더러를 쓰고, `linkMode: "public"` 에서 `[[WikiLink]]` 를 평문으로만 펼친다. 끝의 `## 관련 문서` 구간은 내부와 같이 제거한다. 인용 스니펫은 표시·저장 때 마크다운 문법을 접는다.
- **대안**: 공개 전용 간이 렌더러 유지 → 볼드·리스트가 원문으로 남아 두 리더가 다른 문서처럼 보인다.

## Risks / Trade-offs

- [Risk] 킬스위치가 꺼져 있어도 발행 행은 생긴다 → Mitigation: 기존 계약이다. 공개 URL은 RLS가 404로 막는다. 이 change는 경고 배너를 추가하지 않는다.
- [Risk] 클라이언트가 `published_by`를 실어 보낸다 → Mitigation: 값은 세션 `getUser()`에서만 오고, INSERT는 editor RLS `with check`와 검증 트리거를 통과해야 한다.
- [Risk] 첫 청크 스니펫이 원문 일부를 공개 스냅샷에 넣는다 → Mitigation: 발행은 editor 명시 동작이며, 공개 뷰어는 사이드카만 읽는다. 스니펫 육안 검토는 Non-Goal로 남긴다.
