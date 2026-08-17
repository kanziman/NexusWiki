# Design: source-management-wiki

## Architecture & Invariants

1. **불변 소스 파이프라인 (Insert-Only)**:
   - `raw_sources`와 `source_chunks`는 Insert-only.
   - 소스 목록은 파이프라인 상태(`JobStepper`)만 추적하며, `verification_status`는 위키 문서의 고유 속성이다.
2. **MIME 필터 축 (`SourcesList`)**:
   - `all`: 전체 소스
   - `pdf`: `mime_type === "application/pdf"`
   - `text_md`: `mime_type === "text/plain" || mime_type === "text/markdown"`
3. **이중 Citation 및 WikiLink**:
   - `WikiPageContent`: `[[WikiLink]]` 파싱 → `resolveWikiLinks` → `RedLinkCta`
   - `ContentViewer`: `[[wiki:wN]]` / `[[src:sN]]` 인라인 칩 및 `CitationSidePanel`

## Data Model & Props

- `SourceRow`: `{ id, title, source_type, mime_type, created_at, content_hash }`
- `WikiPage`: `{ id, title, content, category, verification_status, verified_by, verified_at, expires_at, disputed }`
- `WikiLink`: `{ target_slug, resolved }`
