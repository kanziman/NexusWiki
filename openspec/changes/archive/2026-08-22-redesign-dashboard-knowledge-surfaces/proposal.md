## Why

대시보드의 소스·백로그·위키·질문 화면이 서로 다른 밀도와 문서 표현을 사용해 같은 지식 객체를 화면마다 다시 해석해야 한다. 특히 소스 상세는 메타데이터만 보여주고, 위키와 답변의 마크다운 구조가 충분히 보존되지 않아 원문→청크→위키→답변의 추적 흐름이 UI에서 끊긴다.

## What Changes

- 공통 사이드바, 입력 포커스, 목록 툴바, 상태·형식 배지, 빈 상태와 업로드 모달을 하나의 조밀한 정보 위계로 정비한다.
- 소스 목록의 제목을 상세 경로와 직접 연결하고, 상세 화면에서 요청자 권한 범위의 원문·청크 좌표·처리 상태·인용 위키 문서를 함께 탐색하게 한다.
- 위키 라이브러리의 발췌문에서 내부 마크업을 제거하고 카테고리·검증 상태를 명확히 구분한다.
- 위키 리더에서 제목, 목록, 표, 인용문, 코드 블록과 WikiLink를 구조적으로 렌더링하고 현재 읽는 절을 목차에 표시한다.
- Ask 답변에서도 마크다운 블록 구조를 보존하면서 인용 마커의 순서와 클릭 동작을 유지하고, 원문 소스와 위키 문서 인용을 범례로 구분한다.
- 백로그 목록과 상세 패널의 검색·행 위계·소스 추가 동선을 다른 라이브러리 화면과 일치시킨다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `dashboard-design-consistency`: 공통 사이드바·포커스·목록·모달의 접근 가능한 시각 위계와 축소 상태 동작을 구체화한다.
- `library-selection-layout`: 소스 상세가 원문, 청크 좌표, 처리 상태와 인용 위키 관계를 함께 제공하도록 확장한다.
- `source-management-wiki`: 요청자 세션으로 조회한 원문·청크·인용 관계를 소스 상세에서 탐색하는 계약을 추가한다.
- `wiki-library-navigation`: 라이브러리 발췌 정제와 문서 리더의 구조적 마크다운·활성 목차 동작을 추가한다.
- `wiki-page-routing`: 목차가 현재 절을 추적하고 부드러운 절 이동 뒤 URL 앵커를 유지하도록 확장한다.
- `backlog-ask`: 백로그의 문서형 목록 위계와 Ask 답변의 리치 마크다운·이중 인용 범례를 추가한다.

## Impact

- Dashboard: `apps/dashboard/app/w/[workspaceId]/sources/[id]`, 소스·백로그·위키·Ask·사이드바·업로드 관련 컴포넌트와 테스트
- 디자인 정본: `docs/design-systems/v2/nexuswiki-design-system.css`
- 데이터 접근: 기존 요청자 Supabase client와 RLS를 그대로 사용하며 `raw_sources`, `source_chunks`, `wiki_pages`의 읽기 범위만 상세 화면에 조합한다.
- API, 데이터베이스 스키마, RLS 정책, 외부 의존성 변경 없음
- GitHub 추적: umbrella #68, vertical slices #69·#70·#71·#72
