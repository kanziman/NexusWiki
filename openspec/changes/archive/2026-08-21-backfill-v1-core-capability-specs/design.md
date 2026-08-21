## Context

현재 canonical OpenSpec은 인증, 워크스페이스 진입, 최근 대시보드와 공개 공유 같은 후속 변경을 잘 설명하지만, v1.0에서 완성된 백엔드 핵심 계약은 GSD 아카이브에만 남아 있다. `checklists.json` revision 8의 phase 상태는 v1.0 완료 전 시점에서 멈췄고, Git commit `34fee23`의 `.planning/milestones/v1.0-REQUIREMENTS.md`와 phase verification은 73개 요구사항의 완료 근거를 보존한다.

이번 작업은 코드를 바꾸는 마이그레이션이 아니라 정본 계약의 백필이다. 따라서 과거 계획의 의도만으로 요구사항을 만들지 않고, 현재 코드·마이그레이션·테스트 또는 운영 기록과 교차 확인되는 동작만 추가한다.

## Goals / Non-Goals

**Goals:**

- 핵심 제품 경계를 QA 가능한 Given/When/Then 계약으로 복원한다.
- 기존 UI 중심 spec과 중복되지 않는 capability 소유권을 만든다.
- 이후 변경이 과거 GSD 문서를 다시 해석하지 않고 canonical spec을 수정하도록 한다.
- 역사적 결정 근거와 현재 규범 계약의 역할을 분리한다.

**Non-Goals:**

- 애플리케이션 코드, API, 데이터베이스 또는 배포 설정을 변경하지 않는다.
- GSD의 73개 task 및 구현 세부를 OpenSpec에 일대일로 복제하지 않는다.
- `checklists.json`의 오래된 상태 필드를 갱신하거나 GSD 산출물을 작업 트리에 복원하지 않는다.
- 향후 후보 기능, 배포 리전, 라이브러리 버전 및 벤치마크 수치를 제품 capability로 승격하지 않는다.

## Decisions

### Decision: 세 종류의 근거가 수렴하는 계약만 백필한다

계약 후보는 (1) v1.0 archived requirements와 verification, (2) `checklists.json`의 확정 결정, (3) 현재 코드·마이그레이션·테스트를 대조한다. 과거 문서와 현재 구현이 충돌하면 오래된 task 상태를 정본으로 간주하지 않고 현재 동작과 후속 OpenSpec 변경을 우선한다.

대안은 GSD 요구사항 73개를 그대로 복사하는 방식이다. 이 방식은 bootstrap task와 구현 선택까지 영구 제품 계약으로 만들고 현재 spec과 중복되므로 채택하지 않는다.

### Decision: 사용자 흐름이 아니라 안정된 책임 경계로 capability를 나눈다

수집, 컴파일, 잡, 검색, 답변, 품질, 격리, 비용 보호장치를 독립 capability로 둔다. 기존 `source-management-wiki`와 `backlog-ask`는 화면과 사용자 여정을 계속 소유하고, 신규 spec은 그 여정이 의존하는 백엔드 경계와 실패 동작을 소유한다.

대안은 `v1-core` 하나의 거대 spec이다. 변경 영향과 요구사항 소유권을 추적하기 어려워 채택하지 않는다.

### Decision: 역사와 수치를 spec 밖에 유지한다

왜 특정 기술을 골랐는지는 `checklists.json` decisions와 `docs/ops/`에 남기고, OpenSpec에는 사용자가 의존하거나 보안·신뢰성 검증이 필요한 결과 계약만 기록한다. 모델 ID, 리전, 특정 벤치마크 값처럼 변동 가능한 값은 capability 요구사항에 고정하지 않는다.

대안은 모든 결정과 검증 기록을 spec에 복제하는 방식이다. 이는 두 정본을 만들고 운영 수치가 바뀔 때 계약을 불필요하게 stale하게 하므로 채택하지 않는다.

## Risks / Trade-offs

- [기존 UI spec과 일부 용어가 겹칠 수 있음] → 신규 spec은 처리·보안 경계를 소유하고 기존 spec은 화면·내비게이션을 소유하도록 문구를 제한한다.
- [과거 계획을 현재 계약으로 잘못 승격할 수 있음] → archived 완료 표시만으로 채택하지 않고 현재 구현·테스트 근거와 교차검증한다.
- [한 change에 신규 spec이 많아 리뷰량이 커짐] → 하나의 v1.0 백필이라는 단일 목적을 유지하되 capability 파일을 독립적으로 검증 가능하게 분리한다.
- [Project #1 추적이 토큰 권한으로 누락될 수 있음] → 이슈 번호를 모든 산출물에 기록하고 권한이 복구되기 전에는 Project item 식별자를 추측하지 않는다.

## Migration Plan

1. 신규 capability delta spec 8개와 추적 가능한 문서 task를 strict validation한다.
2. apply 단계에서 동일 capability 경로를 canonical `openspec/specs/`에 반영한다.
3. canonical specs 전체를 strict validation하고 문서 외 변경이 없는지 확인한다.
4. 사용자 요청 범위가 apply까지이므로 change archive와 이슈 종료는 별도 후속 단계로 남긴다.

롤백이 필요한 경우 이번 change가 추가한 8개 canonical capability만 제거한다. 기존 spec과 코드에는 수정이 없으므로 별도 데이터 또는 API 롤백은 없다.
