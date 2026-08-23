## Why

워크스페이스 유형(개인/팀) 설정 및 전환 제어, 대시보드 스켈레톤 UI, 피드 수량 제한, 페이지네이션, 위키 상세 리더 중복 관련 문서 정제 및 홈 질문 자동 제출 연동 등 실제 제품 사용성과 인터랙션 계약을 보강합니다.

## What Changes

- **워크스페이스 설정 (`workspace-settings`)**:
  - 기본 정보 탭에서 개인/팀 워크스페이스 유형(`kind`) 라디오 선택 제공
  - 팀 워크스페이스를 개인 워크스페이스로 전환 시, 다른 멤버가 참여 중이면 전환 차단 및 안내 문구 노출
  - 개인 워크스페이스 상태에서는 멤버 초대 폼을 비활성화하고 안내 표시
  - 워크스페이스 유형 변경 시 LNB 및 전체 레이아웃의 워크스페이스 데이터를 즉시 동기화
- **홈 대시보드 (`workspace-home-dashboard`)**:
  - AskHero에서 질문 입력 후 제출 시 `/ask?q=...`로 전달되어 질문 대화가 즉시 자동 시작
  - 홈 대시보드 최근 위키 피드 최대 10개, 미완성 백로그 피드 최대 8개로 제한하여 컴팩트 유지
- **위키 라이브러리 및 상세 리더 (`wiki-library-navigation`)**:
  - 위키 상세 리더 렌더링 시 본문 끝의 중복 `## 관련 문서` 텍스트를 정제하고 목차(TOC)에서 제외
  - 하단 관련 문서 섹션을 2열 인터랙티브 지식 카드 그리드 UI로 단일화
  - 위키 상세 리더 상단에 '← 위키 목록' 뒤로가기 네비게이션 제공

## Capabilities

### Modified Capabilities
- `workspace-settings`: 워크스페이스 유형(개인/팀) 설정, 팀->개인 전환 시 멤버 체크 차단, 개인 모드 초대 비활성화 요구사항 추가
- `workspace-home-dashboard`: AskHero 질문 제출 시 ask 화면 자동 대화 시작 및 피드 노출 제한 요구사항 추가
- `wiki-library-navigation`: 위키 상세 리더 중복 관련문서 정제 및 상단 뒤로가기 네비게이션 요구사항 추가

## Impact

- `apps/dashboard`: `WorkspaceGeneralSettings`, `SettingsMembersPanel`, `InviteForm`, `AskConversation`, `WikiPageContent`, `KnowledgeGrid` 등 컴포넌트 및 테스트
