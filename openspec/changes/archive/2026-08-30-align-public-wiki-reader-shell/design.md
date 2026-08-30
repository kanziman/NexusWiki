## Context

공개 라우트·사이드카·킬스위치는 `openspec/specs/public-sharing/spec.md`가 이미 계약한다. 본문 조판은 `add-wiki-page-publish-controls`가 내부 리더와 같은 `WikiDocumentBody`로 맞췄다. 이 change는 공개 셸과 사이드카 탐색만 다룬다. 동기는 proposal.md를 본다.

불변식: 공개 경로는 `createPublicClient()`(anon, 세션 쿠키 미사용)로 사이드카 두 테이블만 본다. `wiki_pages.category`와 `published_by` 표시명은 그 경로에서 조회할 수 없다.

## Goals / Non-Goals

**Goals:**
- 헤더와 본문이 같은 3단 트랙을 공유하는 공개 셸
- 같은 워크스페이스의 다른 발행본을 `/p/` 링크로만 탐색
- 워크스페이스 공개 메타와 발행 스냅샷으로 신뢰 카드·인용·가입 CTA를 구성

**Non-Goals:**
- `published_category` 컬럼 추가와 4대 카테고리 LNB 그룹핑. 카테고리는 `wiki_pages`에만 있고 공개 스냅샷에 없다.
- `published_by` → 표시명 조회, 개인 아바타, "100% 원문 검증됨" 카피
- 인용 스니펫 육안 검토 UI, 본문 타이포 분기(15px 전용 `.article-body`)
- 로그인 리디자인 파일, Ask 공개 노출, 새 마이그레이션

## Decisions

### 1. 공개 LNB는 평면 발행 목록이다
- **결정**: `wiki_page_publications`의 `published_slug`·`published_title`만 나열하고 현재 문서를 강조한다. 그룹 헤더는 "공개 문서" 하나다.
- **대안**: 4대 카테고리로 묶기 → `wiki_pages.category` 조인이 필요하고 `anon`은 그 테이블에 정책이 없다.
- **대안**: 지금 마이그레이션으로 `published_category`를 스냅샷 → 이 change의 시각 정렬보다 스키마 작업이 커진다. 후속으로 남긴다.

### 2. 신뢰 카드는 워크스페이스 공개 신원이다
- **결정**: `public_display_name`, 발행일, 읽기 시간(본문 길이), 검증 배지, 인용 스냅샷의 원문 제목을 쓴다. 색은 `--good`·`--avatar-bg` 토큰만 쓴다.
- **대안**: `published_by`로 개인 크리에이터 카드 → `auth.users` 조회가 필요하고 게스트에게 계정 식별자가 샌다.

### 3. 셸 클래스는 `.public-*`, 본문은 `.reader` / `.article`
- **결정**: 3단 그리드는 `.public-header-grid`와 `.public-layout`이 공유한다. 본문 조판 클래스를 공개 전용으로 복제하지 않는다.
- **대안**: 시안의 `.article-body` 15px를 공개에만 쓰기 → 내부 리더와 다른 문서로 보인다.

### 4. 연관 문서와 가입 CTA는 사이드카·공개 라우트만
- **결정**: 연관 카드는 같은 `workspace_id`의 다른 발행본이고 href는 `/p/...`다. CTA는 `/signup`이다. 복사 버튼만 클라이언트 섬이다.
- **대안**: 본문 `[[WikiLink]]`를 다시 링크로 만들기 → 대상이 미발행이면 404가 되고, 실수로 `/w/`를 그리면 테넌트 식별자가 샌다.

## Risks / Trade-offs

- [Risk] 시안 LNB의 4대 카테고리와 구현의 평면 목록이 어긋난다 → Mitigation: 시안도 평면 "공개 문서" 그룹으로 맞추고, 카테고리 스냅샷은 후속 change로 명시한다.
- [Risk] 발행본이 많으면 LNB가 길어진다 → Mitigation: 제목 ellipsis와 사이드바 스크롤. 페이지네이션은 이 change에 넣지 않는다.
- [Risk] 연관 카드 설명이 스냅샷에 없다 → Mitigation: 본문 앞부분을 평문으로 잘라 쓰고, 없으면 제목만 둔다.
