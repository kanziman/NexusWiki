# 넥서스위키(NexusWiki) 워크스페이스 설정 & 멤버 권한 관리 PRD

> **문서 상태**: 확정 (Validated)  
> **기능 영역**: 워크스페이스 멤버 초대/역할 관리 및 백그라운드 운영 지표 대시보드 (`/settings`)  
> **연계 프로토타입 시안**: [`docs/design-systems/workspace-settings-preview.html`](file:///Users/zorba/projects/NexusWiki/docs/design-systems/workspace-settings-preview.html)

---

## 1. 개요 및 목적 (Overview & Goals)

### 1.1. 배경
* 넥서스위키는 다중 테넌트(Multi-tenant) SaaS로서, 모든 데이터 격리와 권한 제어는 애플리케이션 계층이 아닌 **PostgreSQL 17 Row Level Security(RLS)**가 강제합니다.
* 워크스페이스 관리자(Owner/Editor)는 팀원을 초대하고 3단계 역할(`owner`, `editor`, `viewer`)을 부여할 수 있어야 하며,
* 백그라운드 비동기 컴파일 파이프라인 잡 상태 및 LLM/스토리지 운영 예산을 실시간으로 모니터링할 수 있어야 합니다.

### 1.2. 핵심 목적
1. **역할 기반 접근 제어(RBAC) 및 멤버 관리**:
   * `owner`: 워크스페이스 삭제, 멤버 권한 승격/강등/퇴장, 운영 현황 전체 제어.
   * `editor`: 원문 소스 업로드/삭제(백그라운드 자동 컴파일), 실패 잡 재시도(JobStepper Retry), 프롬프트 오버라이드, 운영 현황 조회.
   * `viewer`: 위키 문서 열람, AI 질문(Ask), 지식 그래프 탐색.
2. **멤버 초대 및 가입 승인 파이프라인**: 이메일 및 초기 역할 지정을 통한 즉시 초대.
3. **비동기 파이프라인 및 LLM 예산 모니터링 (`/operations`)**:
   * 소스 수집 / 위키 컴파일 / 임베딩 파이프라인의 큐(Queued), 실행 중(Running), 실패(Dead) 작업 수치 집계.
   * 월별 LLM API 사용 예산 한도 대비 소진율(%) 및 잔여 예산 추적.
   * PostgreSQL 17 RLS 38개 보안 정책 무결성 확인.

---

## 2. 사용자 페르소나 및 유저 스토리 (User Stories)

* **워크스페이스 관리자 (User A)**: "신규 프로젝트 엔지니어를 `editor` 권한으로 초대하여 소스 코드를 업로드하고 위키 컴파일을 진행할 수 있게 하고 싶다."
* **테크 리드 (User B)**: "현재 백그라운드에서 실행 중인 위키 컴파일 잡에 실패(Dead)가 발생했는지 운영 현황 탭에서 즉시 확인하고 싶다."
* **일반 뷰어 (User C)**: "내 역할(`viewer`)과 워크스페이스 기본 정보를 확인하고 싶다."

---

## 3. 핵심 기능 요구사항 (Functional Requirements)

### 3.1. 상단 헤더 및 2-Tab 세그먼트 네비게이션
* **브레드크럼 경로**: `엔지니어링 코어 / 워크스페이스 설정`
* **타이틀 & 설명**: `워크스페이스 설정 (Workspace Settings)` + 1줄 요약.
* **2대 설정 탭**:
  1. **`👥 멤버 관리 (Members)`** (모든 멤버 접근 가능)
  2. **`⚡ 운영 현황 (Operations)`** (Owner / Editor 전용 노출)

### 3.2. [Tab 1] 멤버 관리 뷰 (Members Tab)
1. **멤버 로스터 테이블 (`MembersList`)**:
   * 컬럼: 멤버 프로필(이름, 이메일), 역할 뱃지(`owner`, `editor`, `viewer`), 가입 일시, '나(You)' 인디케이터.
   * 액션 드롭다운: 역할 변경 (`viewer` ➔ `editor` 승격 등), 워크스페이스 퇴장 처리.
2. **신규 멤버 초대 폼 (`InviteForm`)**:
   * 이메일 입력 필드 (`colleague@company.com`).
   * 부여할 초기 역할 드롭다운 선택 (`editor` / `viewer`).
   * `[+ 멤버 초대장 발송]` CTA 버튼 및 즉시 테이블 리마운트(Refetch) 연동.

### 3.3. [Tab 2] 운영 현황 뷰 (Operations Tab - Owner/Editor 전용)
1. **월별 LLM 추론 예산 (`Budget Snapshot`)**:
   * 이번 달 한도($100.00), 사용액($34.20), 잔여 예산($65.80), 실시간 프로그레스 바(34.2%).
2. **3대 비동기 파이프라인 큐 모니터링 (`Pipeline Status`)**:
   * ① **원문 소스 수집 & 청킹**: 대기 0건 | 실행 1건 | 실패 0건
   * ② **위키 자동 컴파일러**: 대기 2건 | 실행 1건 | 실패 0건
   * ③ **벡터 임베딩 생성**: 대기 0건 | 실행 0건 | 실패 0건
3. **Postgres 17 테넌트 격리 무결성 (`RLS Status`)**:
   * RLS 정책 활성 (`● 100% 격리 정상`).

### 3.4. 외부 웹 공개 마스터 킬스위치 (`workspace_public_settings` 사이드카 - Owner 전용)
1. **마스터 킬스위치 (Allow Public Sharing)**:
   * 1:1 사이드카 테이블 `workspace_public_settings`에 바인딩된 워크스페이스 레벨 공개 스위치.
   * `ON`: 사람이 검토 승인한 개별 공개 위키(`/p/[workspace_slug]/[page_slug]`)가 외부에 안전하게 열림.
   * `OFF`: 즉시 모든 외부 공개 요청이 PostgreSQL RLS 엔진 레벨에서 0건으로 차단되어 404 응답 (물리적 킬스위치).
2. **사이드카 확장성**:
   * 향후 워크스페이스 전체 공개(Docs 사이트 모드)를 위한 `public_display_name`, `public_description` 필드를 핵심 `workspaces` 테이블 오염 없이 안전하게 수용.

---

## 4. 비기능 요구사항 및 디자인 원칙 (Non-Functional Requirements)

1. **100% Pure Crisp White Mode**: 순백색(`#FFFFFF`), 쿨 슬레이트(`#F8FAFC`), `#E2E8F0` 헤어라인 보더.
2. **Zero Emojis**: 2.0~2.2px 단색 SVG 라인 아이콘만 적용.
3. **엄격한 RBAC 보안**: Viewer 역할 로그인 시 운영 현황 탭 자동 숨김 및 권한 변경 비활성화.
4. **실제 프론트/백엔드 계약 정합**: `SettingsMembersPanel.tsx` 및 `OperationsPanel.tsx`의 실측 스펙과 100% 일치.
