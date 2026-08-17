## Why

대시보드는 기능별 화면이 개별적으로 개선되어 여백, 정보 밀도, 상태 표현, 컴포넌트 형태가 일관되지 않다. 사용자가 화면을 전환해도 하나의 신뢰할 수 있는 지식 작업공간처럼 느끼도록 공통 시각·상호작용 계약을 정립한다.

## What Changes

- 모든 workspace 화면에 공통 페이지 프레임, 헤더, 섹션 위계, 상태·빈 화면 표현을 적용한다.
- 버튼·입력·필터·문서 행·상태 배지를 재사용 가능한 디자인 시스템 구성요소로 통일한다.
- Sources, Ask, Wiki, Graph, Settings, Home의 정보 밀도와 반응형 우선순위를 정렬한다.

## Capabilities

### New Capabilities

- `dashboard-design-consistency`: workspace dashboard 전반의 공통 레이아웃·상태·접근성 시각 계약

### Modified Capabilities

- 없음.

## Impact

- dashboard routes, shared components, `globals.css`, design tokens, component/route tests
- API, database, RLS, background processing contracts are unchanged
