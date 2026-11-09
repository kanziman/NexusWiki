## 1. 실제 합성 답변을 PR에서 재채점한다

Umbrella: https://github.com/kanziman/NexusWiki/issues/245
하위 작업: https://github.com/kanziman/NexusWiki/issues/246
예상 반나절. 유료 호출 없음. 선행: 기존 Ask 판정 함수와 보존된 실제 합성 결과.

- [x] 1.1 허용 필드 fixture와 출처 해시, CLI, 누락·중복·개인 필드·판정 차이 실패 검증을 구현하고 CI에 연결한다. Given 저장된 실제 합성 결과와 기대 판정, When PR 관문 실행, Then 모든 문항이 일치할 때만 성공하며 네트워크와 자격증명 없이 동작한다. 의도적으로 인용·거절 입력을 바꾸거나 문항을 제거하면 실패한다.
- [x] 1.2 평가 지도에 관문의 범위·한계를 기록하고 관련 테스트·lint·strict 검증과 명세 리뷰를 수행한다. Given 검증된 CLI와 CI 단계, When 최종 검증, Then 실제 fixture 성공과 변조 실패가 입증되고 새 모델 출력 품질은 검증하지 못함이 명시된다.
- [x] 1.3 delta를 정본에 동기화하고 specs strict 검증 후 아카이브·한국어 커밋한다. Given 모든 구현·리뷰 완료, When 정리, Then 미완료 항목 없이 정본과 코드가 일치한다.

사용자가 권장안에 따른 계획 게이트와 구현 진행을 승인했다. 테넌트 리뷰는 사용자 요청으로 생략하며 관련 격리 테스트는 유지한다.
