## 1. OpenSpec 기획 계약

- [x] 1.1 [GitHub #5](https://github.com/kanziman/NexusWiki/issues/5) OpenSpec artifact 규칙과 feature-planning/autonomous workflow 계약을 추가한다. **AC:** Given 신규 기능 proposal을 작성할 때, When 요구사항·기술 선택·작업 분해가 진행되면, Then 기존 artifact 경로 안에서 용어·조건부 3안 ADR·Non-Goals·Given-When-Then 수직 슬라이스가 검증 가능하게 남는다.

## 2. GitHub 추적 lifecycle

- [x] 2.1 [GitHub #6](https://github.com/kanziman/NexusWiki/issues/6) `AGENTS.md`와 Claude 공통 지침을 GitHub umbrella/sub-issue 및 Project #1 lifecycle로 전환한다. **AC:** Given change와 승인된 수직 슬라이스가 있을 때, When agent가 외부 상태를 갱신하면, Then 반환된 식별자를 확인해 parent/sub-issue와 Todo/In Progress/Done을 연결하고 archive 전에는 umbrella issue를 닫지 않는다.

## 3. 공통 propose 진입점

- [x] 3.1 [GitHub #7](https://github.com/kanziman/NexusWiki/issues/7) 프로젝트 로컬 `openspec-propose`를 canonical workflow로 추적하고 Claude command를 같은 계약의 thin adapter로 전환한다. **AC:** Given Codex 또는 Claude가 기존 propose 진입점을 사용할 때, When feature planning을 시작하면, Then 동일한 단일 질문 인터뷰·네 게이트·strict validation·GitHub 등록 규칙을 적용하며 별도 feature 문서나 새 command를 요구하지 않는다.

## 4. 회귀 검증

- [x] 4.1 [GitHub #8](https://github.com/kanziman/NexusWiki/issues/8) 변경 전 baseline과 변경 후 Codex/Claude pressure scenarios를 비교하고 skill 형식, strict OpenSpec validation, GitHub issue/Project 연결을 새로 검증한다. **AC:** Given 단순 변경·중대한 아키텍처 변경·연속 진행·외부 갱신 실패 시나리오, When 강화된 workflow를 평가하면, Then 비례적 계획과 승인 예외가 일관되고 실패한 외부 상태를 완료로 보고하지 않는다.
