# 넥서스위키(NexusWiki) 워크스페이스 홈 & 지식 그룹 허브 PRD (Product Requirements Document)

> **문서 상태**: 확정 (Validated)  
> **기능 영역**: 워크스페이스 홈 대시보드, 지식 그룹 허브 및 신규 온보딩 (`/w/[workspace_slug]/[project_slug]/[group_slug]`, `/`)  
> **연계 프로토타입 시안**: [`docs/design-systems/workspace-home-preview.html`](file:///Users/zorba/projects/NexusWiki/docs/design-systems/workspace-home-preview.html)  
> **상위 불변 규칙 문서**: [`docs/design-systems/PRODUCT-INVARIANTS.md`](file:///Users/zorba/projects/NexusWiki/docs/design-systems/PRODUCT-INVARIANTS.md)

---

## 1. 개요 및 목적 (Overview & Goals)

### 1.1. 배경
* 넥서스위키의 메인 홈 대시보드는 팀이 연결한 원본 소스와 AI가 컴파일한 위키 문서들이 집결되는 **"살아있는 지식 베이스의 메인 관제탑(Hub)"**입니다.
* 사용자는 워크스페이스 진입 시 복잡한 메뉴를 헤맬 필요 없이, **중앙의 직관적인 AI 질문창을 통해 지식을 탐색**하거나 **검증 완료된 위키 문서 목록**과 **작성이 필요한 백로그(레드링크)**를 한눈에 파악할 수 있어야 합니다.
* 또한 소속된 워크스페이스가 없는 신규 사용자(New User)에게는 불필요한 추천 템플릿 강요 없이, **자유도 높은 초경량 워크스페이스 개설 캔버스**를 제공하여 즉각적인 가치(Time-To-Value)를 경험하게 합니다.

### 1.2. 핵심 목적
1. **중앙 집중형 AI 지식 질의응답 (Central Ask Box)**: 범위 선택(현재 그룹 / 프로젝트 전체 / 워크스페이스 전체)이 가능한 대형 질문창을 중앙에 배치하여 지식 접근성 극대화.
2. **지식 그룹 현황 및 렌즈 분류 가시화**: 컴파일된 위키 문서의 메타데이터(연결 소스 수, 업데이트 시점, 검증 상태) 및 카테고리 렌즈(`CONCEPTS`, `GUIDE`, `ARCHITECTURE`) 카드 뷰 제공.
3. **미완성 지식 백로그(레드링크)의 투명한 노출**: 원본 소스가 부족하거나 추가 작성이 필요한 결손 지식을 홈에서 즉시 식별하고 `[자료 연결]`로 유도.
4. **고자유도 신규 유저 온보딩 (Zero State Onboarding)**: 워크스페이스가 없는 사용자에게 이름과 URL 식별자 입력만으로 즉시 시작할 수 있는 미니멀 개설 경험 제공.

---

## 2. 사용자 페르소나 및 유저 스토리 (User Stories)

* **테크 리드 / 아키텍트 (User A)**: "출근 후 메인 화면에서 현재 엔지니어링 코어 지식베이스의 컴파일 상태와 작성 대기 중인 아키텍처 백로그를 한눈에 파악하고 싶다."
* **신규 입사 엔지니어 (User B)**: "중앙 질문창에 검색 범위를 '데이터베이스 & RLS'로 지정하고 추천 질문 칩을 클릭하여 RLS 격리 규칙을 1초 만에 확인하고 싶다."
* **신규 가입 관리자 (User C)**: "가입 직후 강제된 템플릿에 구애받지 않고, 우리 팀만의 이름으로 워크스페이스를 즉시 개설하여 자유롭게 팀 프로젝트를 만들어가고 싶다."

---

## 3. 핵심 기능 및 화면 요구사항 (Functional Requirements)

### 3.1. 좌측 내비게이션 바 (LNB / Primary Navigation)
* **워크스페이스 스위처 (Workspace Switcher)**:
  * 최상단에 현재 워크스페이스 명칭(`NexusDB Core`) 및 이니셜 아바타 표시.
  * 클릭 시 워크스페이스 전환 팝오버 오픈:
    * 소속 워크스페이스 목록 (현재 선택 체크마크 표시)
    * 하단 `[+ 새 워크스페이스 생성]` 버튼 (클릭 시 생성 모달 트리거)
* **시스템 뷰 바로가기**:
  * `⭐ 즐겨찾기`: 사용자가 즐겨찾기한 위키 문서 모음 (카운트 뱃지).
  * `🕒 최근 본 위키`: 최근 열람 이력 목록.
  * `❗ 미완성 백로그`: 원본 소스가 누락된 레드링크 모음 (카운트 뱃지: 7).
  * `↥ 원문 소스`: 연결된 소스 파일 관리 및 인덱싱 상태 (카운트: 18).
  * `📄 템플릿 관리`: 위키 문서 표준 템플릿 관리.
* **계층형 팀 프로젝트 & 위키 그룹 트리 (Tree Hierarchy)**:
  * 프로젝트 섹션별 펼침/접힘(`⌄`/`›`) 토글 지원.
  * 프로젝트(예: `엔지니어링 코어`) 하위에 속한 위키 그룹 목록 노출:
    * `백엔드 아키텍처 (12)`
    * `데이터베이스 & RLS (18)` — *현재 선택 활성(Selected) 상태*
    * `5채널 하이브리드 검색 (8)`
    * `잡 큐 & 워커 풀 (4)`
    * `[+ 위키 추가]`
  * 하위 프로젝트(예: `제품 기획 (PRD) (2)`) 접이식 메뉴.
* **팀 관리 및 하단 프로필**:
  * `팀원 & 역할 관리 (8명)`, `새 팀원 초대하기` 링크.
  * 하단 사용자 프로필(`김개발 (Owner)`) 및 설정/로그아웃 트리거.

### 3.2. 상단 바 (Top Navigation Bar)
* **브레드크럼 (Breadcrumb)**: `엔지니어링 코어 / 데이터베이스 & RLS`
* **시뮬레이션 모드 스위처 (개발/데모용)**:
  * `[대시보드 모드]`: 기존 멤버의 완성된 지식 홈 대시보드 뷰 (`#home-member-view`).
  * `[신규 온보딩 모드]`: 워크스페이스가 없는 신규 사용자의 최초 개설 뷰 (`#home-onboard-view`).
* **우측 글로벌 액션**:
  * `[로그인]`: Google SSO 인증 화면(`/login`) 바로가기.
  * `[+ 소스 추가]`: 원본 소스 업로드 모달 트리거.

### 3.3. 중앙 지식 대시보드 캔버스 (`#home-member-view`)
* **지식 그룹 히어로 헤더 (Hero Header)**:
  * 대제목: `데이터베이스 & RLS` + `☆` 즐겨찾기 토글 버튼.
  * 태그 알약: `지식 그룹`, `백엔드`, `데이터`, `보안`, `운영`.
  * 메타 통계 행:
    * 📄 컴파일된 위키 문서: **18**
    * 🗄️ 연결된 소스: **42**
    * 🕒 최종 업데이트: **1시간 전**
* **중앙 대형 AI 질문창 (Central Large Ask Box)**:
  * 다중 라인 자동 리사이즈 텍스트에어리어.
  * **지식 탐색 스코프 셀렉터 (Interactive Scope Selector)**:
    * `데이터베이스 & RLS (현재 그룹)` — 기본값
    * `엔지니어링 코어 (프로젝트 전체)`
    * `넥서스 SaaS 팀 (워크스페이스 전체)`
  * `[질문하기 ↗]` CTA 버튼 (클릭 시 AI 질의응답 화면 `/ask`로 자연스러운 전환).
* **추천 스타터 질문 칩 (Starter Chips)**:
  * `[PostgreSQL RLS 격리 규칙 요약]`, `[HNSW iterative_scan 튜닝 방법]`, `[누락된 캐시 계층 전략 백로그]`.
  * 클릭 시 질문창에 해당 문구가 자동 채워지며 즉시 포커스.
* **2-Column 지식 영역 (`knowledge-sub-grid`)**:
  * **Col 1: 컴파일된 위키 문서 (Compiled Wikis)**:
    * 상단: 문서 수 뱃지(`18`) 및 `[전체 보기 >]` 버튼.
    * 카드 구성:
      * 카테고리 렌즈 뱃지 (`CONCEPTS` 보라, `GUIDE` 파랑, `ARCHITECTURE` 초록)
      * 위키 제목 링크 (클릭 시 `/wiki/[slug]` 상세 뷰어 이동)
      * 원문 인용 수 및 갱신 시점 메타데이터
      * 초록색 `[✔ 검증 완료]` 뱃지
  * **Col 2: 미완성 백로그 (Redlink Backlog)**:
    * 상단: 로즈 컬러 뱃지(`7`) 및 `[전체 보기 >]` 버튼.
    * 카드 구성:
      * 좌측 로즈 포인트 보더 및 `작성 대기 · [주제명]` 태그
      * 인용 횟수 및 결손 사유 메타 텍스트
      * `[자료 연결]` 액션 버튼 (클릭 시 소스 추가 모달 연동)

### 3.4. 신규 유저 온보딩 캔버스 (`#home-onboard-view`)
* **노출 조건**: 사용자가 소속된 워크스페이스가 0개인 신규 가입자(Case C) 진입 시 메인 홈에 즉시 렌더링.
* **고자유도 미니멀 개설 폼**:
  * `워크스페이스 이름 *`: 실시간 한글/영문 입력 지원 (예: `NexusDB Core`).
  * `고유 URL 슬러그`: 입력된 이름에 맞춰 실시간 영문 소문자 슬러그 자동 생성 (`https://nexuswiki.io/w/[slug]`).
  * `[🚀 워크스페이스 생성 및 시작하기]` CTA 버튼.
  * **자유도 중심 원칙**: 강제된 추천 템플릿 팩이나 고정 프리셋을 요구하지 않으며, 개설 완료 즉시 대시보드로 진입하여 사용자가 LNB의 `[+]`를 통해 원하는 팀 구조를 자유롭게 만들어가도록 지원.

### 3.5. 워크스페이스 추가 생성 모달 (`#create-ws-modal`)
* 스위처 팝오버의 `[+ 새 워크스페이스 생성]` 클릭 시 트리거.
* 필드: 워크스페이스 명칭, URL 슬러그 식별자, 프로젝트 도메인/설명(선택).
* 생성자는 자동으로 `role='owner'`로 등록.

---

## 4. 디자인 시스템 및 불변 규칙 준수 (Design Invariants)

1. **100% Pure White & Flat Minimalist Aesthetic**:
   * 배경색 `#FFFFFF`, 사이드바 `#F8FAFC`, 보더 `#E2E8F0`, 텍스트 `#0F172A`.
   * 불필요한 그라디언트나 블러를 배제하고 명확한 1.5px 보더와 정밀한 타이포그래피 계층 사용.
2. **Zero Emoji Invariant**:
   * 모든 UI 아이콘은 시스템 이모지 대신 단색 라인 SVG 아이콘(Monochrome SVG)만을 사용.
3. **공개 URL 격리 불변 규칙**:
   * 모든 공개 페이지 라우팅은 `/p/[workspace_slug]/[page_slug]` 형식을 준수하여 워크스페이스 간 네임스페이스 충돌을 원천 차단.

---

## 5. 데이터베이스 스키마 및 트랜잭션 계약 (Database Contract)

### 5.1. 온보딩 워크스페이스 생성 트랜잭션
```sql
BEGIN;

-- 1. 신규 워크스페이스 생성
INSERT INTO workspaces (id, name, created_at, updated_at)
VALUES (gen_random_uuid(), :workspace_name, now(), now())
RETURNING id;

-- 2. 공개 설정 1:1 사이드카 기본 생성 (기본 비공개)
INSERT INTO workspace_public_settings (workspace_id, public_workspace_slug, allow_public_sharing, public_display_name)
VALUES (:workspace_id, :workspace_slug, false, :workspace_name);

-- 3. 생성자를 워크스페이스 Owner로 등록
INSERT INTO workspace_members (workspace_id, user_id, role, created_at)
VALUES (:workspace_id, auth.uid(), 'owner', now());

COMMIT;
```

### 5.2. 지식 그룹 홈 렌더링 쿼리
```sql
-- 선택된 지식 그룹의 위키 문서 목록 조회 (RLS 적용)
SELECT wp.id, wp.slug, wp.title, wp.category_lens, wp.verification_status, wp.updated_at,
       COUNT(DISTINCT wpc.raw_source_id) AS cited_sources_count
FROM wiki_pages wp
LEFT JOIN wiki_page_citations wpc ON wpc.wiki_page_id = wp.id AND wpc.workspace_id = wp.workspace_id
WHERE wp.workspace_id = :workspace_id
  AND wp.project_id = :project_id
  AND wp.group_id = :group_id
  AND wp.archived_at IS NULL
GROUP BY wp.id
ORDER BY wp.updated_at DESC;
```

---

## 6. 마일스톤 및 검증 계획 (Verification Plan)

| 단계 | 항목 | 검증 기준 |
| :--- | :--- | :--- |
| **Phase 1** | LNB 계층 트리 & 워크스페이스 스위처 | 스위처 클릭 시 팝오버 열림 및 워크스페이스 간 전환 정상 동작 |
| **Phase 2** | 중앙 질문창 & 스타터 칩 | 질문 입력 및 칩 클릭 시 텍스트 입력창 자동 채움 및 `/ask` 라우팅 연동 |
| **Phase 3** | 2-Column 위키 및 백로그 그리드 | 카테고리 렌즈 뱃지 정밀 스타일 및 각 카드 클릭 시 상세 페이지 연결 |
| **Phase 4** | 신규 온보딩 뷰 (Zero State) | 슬러그 실시간 자동 생성 및 `[시작하기]` 클릭 시 Owner 바인딩 트랜잭션 완료 |
