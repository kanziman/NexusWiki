## MODIFIED Requirements

### Requirement: Router 결정의 shadow 기록
시스템은 Ask 턴과 컴파일 잡마다 Router 결정과 사유 코드를 SHALL 기록한다. Ask 턴에서는 근거 0건(`NO_EVIDENCE`) 단락만 실행하고 나머지 결정(`LOOKUP`, `SINGLE_KIND`, `STANDARD`)은 기록만 하며 LLM 호출 여부를 바꾸지 않는다. 컴파일 잡에서는 입력 지문(`content_hash`, `template_id`, `model`)이 직전 성공 컴파일과 같고 해당 원문에서 생성된 위키 페이지가 워크스페이스에 이미 존재할 때(`SKIP_UNCHANGED`) 공급자 LLM 호출을 MUST 생략하고 후속 체인(`link_sync`)으로 진행해야 한다. 지문 조회 실패나 기존 위키 페이지 부재 시에는 LLM 호출을 생략하지 않고 `STANDARD` 또는 `TRUNCATED`로 실행한다.

#### Scenario: 제목과 정확히 일치하는 질문
- **WHEN** Router가 `LOOKUP` 경로로 판정한다
- **THEN** 판정이 기록되고 실제 처리는 기존 LLM 경로로 진행된다

#### Scenario: 근거가 없는 질문
- **WHEN** 검색 결과가 없다
- **THEN** 결정이 `NO_EVIDENCE`로 기록되고 LLM을 호출하지 않는다

#### Scenario: 내용이 같은 원문의 재컴파일
- **WHEN** 입력 지문이 직전 성공과 같고 해당 원문의 위키 페이지가 이미 존재하는 컴파일 잡이 실행된다
- **THEN** 결정이 `SKIP_UNCHANGED`로 기록되고 공급자 LLM 호출 없이 후속 `link_sync` 잡으로 체인이 이어진다

#### Scenario: 지문이 같아도 기존 위키 페이지가 없을 때
- **WHEN** 입력 지문이 직전 성공과 같지만 해당 원문의 위키 페이지가 존재하지 않는다
- **THEN** LLM 호출을 생략하지 않고 컴파일을 실행한다
