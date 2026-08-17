# Design: public-sharing

## Architecture & Invariants

1. **사이드카 분리 (불변식 §5.2, §5.3)**:
   - `workspaces` 정본 테이블은 anon 정책이 없으므로, anon 조회를 위한 `workspace_public_settings` 및 `wiki_page_publications` 사이드카 테이블을 사용한다.
   - 킬스위치는 `exists (select 1 from workspace_public_settings s where s.workspace_id = ... and s.allow_public_sharing = true)`로 DB 레벨에서 RLS로 강제된다.
2. **검증 완료 게이트 (불변식 §3)**:
   - `enforce_publication_verified()` 트리거를 통해 `wiki_pages.verification_status = 'verified'`인 문서만 `wiki_page_publications`에 등록/갱신될 수 있다.
3. **공개 라우트 `/p/[slug]/[page]`**:
   - `anon` Supabase 클라이언트를 사용하여 `workspace_public_settings`와 `wiki_page_publications`를 조회한다.
   - 킬스위치 OFF이거나 발행본이 없으면 즉시 `notFound()`를 반환한다.

## Components & Props

- `PublicSharingSettingsProps`:
  ```typescript
  export type PublicSharingSettingsProps = {
    workspaceId: string;
    isOwner: boolean;
    initialAllowPublicSharing?: boolean;
    initialDisplayName?: string;
    initialDescription?: string;
  };
  ```
