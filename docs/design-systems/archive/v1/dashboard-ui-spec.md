# Dashboard UI Specification

## Product register

NexusWiki dashboard는 밝은 중립 캔버스 위에서 빠른 탐색과 신뢰 가능한 읽기를 지원하는 quiet editorial knowledge workspace다. 장식보다 정보 위계, 상태의 명확성, 키보드 접근성을 우선한다.

## Layout

- workspace route는 `max-w-6xl` 이내의 일관된 content frame을 사용한다.
- 읽기·대화 화면은 `max-w-4xl` 또는 본문 72ch 이내로 제한한다.
- page header는 제목, 한 줄 설명, 최대 하나의 primary action group을 가진다.
- library와 operations 화면은 카드 그리드보다 divider 기반 문서 행을 우선한다.

## Type and spacing

- page title: 30–36px, 600 weight; section title: 18px, 600 weight; body: 16px/1.5 이상.
- route 간 수직 리듬은 16/24/32/48px 토큰만 사용한다.
- 제목·긴 한국어 문구는 줄바꿈을 허용하며 viewport overflow를 만들지 않는다.

## Controls and states

- primary action은 `nw-action`, secondary action은 hairline outline, 모든 조작 요소는 `nw-focus-ring`을 사용한다.
- 상태는 `StatusBadge`와 설명 텍스트를 함께 제공한다. 색상만으로 성공·경고·오류를 표현하지 않는다.
- empty/no-results/error는 제목, 이유, 가능한 다음 행동을 제공하되 페이지 당 primary action은 중복하지 않는다.

## Responsive behavior

- 좁은 viewport에서 header action과 filter는 wrap한다.
- document body는 읽기 폭을 유지하고, 보조 탐색은 본문 위·아래의 inline 영역으로 이동한다.
- target은 최소 44px 높이 또는 동등한 padding을 확보한다.
