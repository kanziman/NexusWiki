## Context

PostgreSQL RLS 정책 `wiki_pages_delete_owner`와 DB 외래키(FK) CASCADE 제약이 이미 마이그레이션(`0002`, `0004`, `0016`, `0017`)에 설정되어 있어, 소유자 권한으로 `wiki_pages` 레코드를 삭제하면 연관 청크(`wiki_chunks`), 그래프 엣지(`wiki_graph_edges`), 발행 스냅샷(`wiki_page_publications`), 북마크(`user_wiki_bookmarks`)가 자동으로 함께 정리된다.

## Goals / Non-Goals

**Goals:**
- 백엔드 `DELETE /workspaces/{workspace_id}/wiki/{wiki_id}` 엔드포인트를 제공하고 소유자 권한 RLS로 보호.
- 프론트엔드 위키 상세 리더(`WikiPageContent.tsx`)와 위키 라이브러리(`WikiLibrary.tsx`)에 소유자 전용 삭제 버튼 및 확인 모달을 제공.
- 삭제 완료 후 사용자에게 피드백을 제공하고 위키 라이브러리로 안전하게 리다이렉트.

**Non-Goals:**
- 컴파일러 파이프라인의 원본 소스로부터의 역추적 자동 복구(삭제된 위키 문서는 사용자의 명시적 삭제로 영구 삭제됨).
- 소프트 삭제(휴지통) 기능.

## Decisions

1. **소유자(Owner) 전용 권한 제한**:
   - 위키 문서는 지식 베이스의 핵심 자산이므로, 에디터나 뷰어에게는 삭제 권한을 부여하지 않고 소유자에게만 삭제 버튼을 노출하고 백엔드에서 403 Forbidden을 검증한다.
2. **확인 모달 필수화**:
   - 실수로 인한 즉시 삭제를 방지하기 위해, 제목과 함께 영구 삭제 경고 및 되돌릴 수 없음을 명시하는 확인 다이얼로그(`Dialog`)를 노출한다.

## Risks / Trade-offs

- [Risk] 삭제된 위키를 참조하는 다른 위키의 인라인 브래킷 링크(`[[deleted-slug]]`)가 깨질 수 있음.
  → 이미 존재하는 빨간색 링크(Red Link) 컴파일 및 미완성 백로그 시스템이 이를 감지하여 "누락된 링크" 상태로 정상 처리함.
