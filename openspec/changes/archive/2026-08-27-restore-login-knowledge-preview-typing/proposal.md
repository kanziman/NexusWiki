## Why

현재 로그인 화면의 지식 미리보기는 시나리오만 일정 시간마다 교체해, 승인된 split
v3 템플릿이 의도한 질문·답변의 생성 흐름을 전달하지 못한다. 좌측 헤드라인도
정적인 문장으로 끝나므로, 제품이 지식을 답으로 연결하는 순간을 자연스럽게
강조할 모션이 필요하다.

## What Changes

- 로그인 지식 미리보기에 질문 입력, 답변 생성, 근거 표시 순서의 타이핑 효과를
  복원한다.
- 헤드라인의 “답으로 연결하다.”에 accent 밑줄이 그려지는 강조 효과를 추가한다.
- 감소 모션 설정 또는 비가시 탭에서는 즉시 완성된 정적 상태를 제공해 움직임을
  강제하지 않는다.

## Capabilities

### New Capabilities

- 없음.

### Modified Capabilities

- `google-authentication`: 로그인 화면의 지식 미리보기와 제품 메시지 강조가
  접근 가능한 모션 상태를 제공하도록 표시 계약을 보강한다.

## Impact

- `apps/dashboard/components/LoginKnowledgePreview.tsx`
- `apps/dashboard/app/(auth)/login/page.tsx`
- `apps/dashboard/app/globals.css`
- 로그인 화면 렌더링 및 모션 단위 테스트
