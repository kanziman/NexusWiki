# 넥서스위키(NexusWiki) - 구글 원클릭 로그인 & 회원가입 (OAuth) PRD

---

## 1. 개요 및 목적 (Overview)
* **화면 라우트**: `/login` (또는 `/auth`)
* **목적**:
  * 복잡한 이메일/비밀번호 입력 및 인증 절차를 전면 배제하고, **Google OAuth 2.0 원클릭 인증**으로 로그인과 회원가입을 단일화(Unification).
  * 엔지니어링 조직의 업무용 구글 계정(Google Workspace / Gmail)을 통한 즉각적인 보안 인증 및 온보딩 지원.
  * **신규 가입자**의 경우 가입 즉시 **"첫 번째 워크스페이스 개설"** 화면으로 매끄럽게 연결하여 이탈률 최소화.

---

## 2. 디자인 시스템 & 미니멀 원칙
* **100% Pure White 모드**: 배경색 `#FFFFFF`, 카드 컨테이너 `#FFFFFF`, hairline 테두리 `#E2E8F0`.
* **노 이모지(Zero Emoji)**: 모든 상태 및 안내 표시는 정밀한 Monochrome 벡터 SVG 아이콘만 사용 (구글 로고는 공식 멀티컬러 SVG 규격 준수).
* **극강의 미니멀리즘**: 불필요한 장식 요소를 배제하고 중앙 집중형 카드 레이아웃으로 집중도 극대화.

---

## 3. 핵심 사용자 흐름 (User Flows)

```
[1단계: 구글 원클릭 인증 화면 (/login)]
  │
  ├── [구글 계정으로 계속하기 (Continue with Google)] 클릭
  │    └── Supabase Auth: supabase.auth.signInWithOAuth({ provider: 'google' })
  │
  ▼
[2단계: 인증 완료 후 테넌트(워크스페이스) 판정 분기]
  │
  ├── Case A: 기존 소속 워크스페이스가 1개인 사용자
  │    └── 즉시 해당 워크스페이스 대시보드 (/w/[workspaceId])로 리다이렉트
  │
  ├── Case B: 기존 소속 워크스페이스가 2개 이상인 사용자
  │    └── 워크스페이스 선택 진입 화면 (/ -> WorkspaceEntryChooser)으로 이동
  │
        └── 메인 페이지(/)로 이동하여 "첫 번째 워크스페이스 만들기" 온보딩 뷰를 즉시 렌더링
            ├── 워크스페이스 명칭 (예: NexusDB Core)
            ├── URL 슬러그 식별자 (예: /w/nexusdb-core)
            └── [🚀 워크스페이스 생성 및 시작하기] 클릭 ➔ 생성 즉시 대시보드로 전환 (팀/지식구조 자유 구성)
```

---

## 4. 컴포넌트 구조 및 계약 (Component Contract)

### 4.1 `GoogleAuthCard`
* **타이틀**: `NexusWiki` + `팀의 살아있는 지식 베이스`
* **Google SSO CTA 버튼**:
  * 공식 Google 'G' 브랜드 아이콘 + `Google 계정으로 계속하기`
  * 호버/액티브 시 정밀한 마이크로 인터랙션 및 로딩 스피너 제공.
* **이용약관 및 개인정보 동의**:
  * 서비스 이용약관 및 개인정보 처리방침 링크.

### 4.2 `OnboardingWorkspaceCard` (신규 사용자 전용 - 고자유도 미니멀 폼)
* **프로필 환영 메시지**: Google 프로필에서 파싱된 이름 및 이메일 표시 (`김개발 님, 환영합니다!`).
* **워크스페이스 생성 폼**:
  * `워크스페이스 명칭 (name)`: 실시간 한글/영문 입력 지원.
  * `URL 슬러그 (slug)`: 입력된 명칭 기반으로 영문 슬러그 자동 생성 (`/w/[slug]`).
  * **자유도 중심 원칙**: 강제된 템플릿 추천 없이 순수 워크스페이스를 즉시 개설하고, 사용자가 필요한 팀 섹션과 지식 그룹을 자유롭게 만들어갈 수 있도록 구성.
* **자동 Owner 바인딩**: 생성 즉시 DB `workspace_members` 테이블에 `role='owner'`로 등록.

---

## 5. 백엔드 및 데이터베이스 트랜잭션 계약

1. **OAuth 콜백 처리 (`/auth/callback`)**:
   * Google 인증 완료 토큰을 Supabase Auth 세션 쿠키로 교환.
2. **신규 워크스페이스 개설 트랜잭션**:
   ```sql
   -- 1. 워크스페이스 레코드 생성
   INSERT INTO workspaces (id, name, created_at) VALUES (gen_random_uuid(), :name, now()) RETURNING id;
   -- 2. 생성자를 Owner로 즉시 등록
   INSERT INTO workspace_members (workspace_id, user_id, role, created_at)
   VALUES (:new_workspace_id, auth.uid(), 'owner', now());
   -- 3. 기본 프롬프트 템플릿(컴파일 1종 + Ask 4종) 상속 바인딩
   ```
