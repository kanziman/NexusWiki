# wiki-compilation Specification

## Purpose

수집된 원문을 검증 가능한 읽기 전용 위키 페이지와 검색 자산으로 반복 생성하면서 링크, 식별자 및 재처리 결과의 일관성을 보장한다.

## Requirements

### Requirement: Validated structured compilation
The system SHALL compile extracted source content into structured wiki pages, MUST validate the generated structure before persistence, and SHALL retry recoverable validation failures with the failure details up to the configured attempt limit.

#### Scenario: First generated result violates the schema
- **WHEN** a compilation provider returns a structurally invalid result
- **THEN** the system feeds the validation errors into a bounded retry and persists only a valid result

#### Scenario: All compilation attempts fail validation
- **WHEN** every bounded compilation attempt remains invalid
- **THEN** the system persists no invalid wiki page and records a safe terminal job failure

### Requirement: Deterministic wiki identity
The system MUST derive each wiki page slug deterministically from its title, apply a versioned normalization rule, and resolve collisions against both existing pages and unresolved link targets without delegating slug ownership to the language model.

#### Scenario: Same normalized title is compiled repeatedly
- **WHEN** the same title is compiled again under the same slugging version
- **THEN** the system derives the same base slug and resolves any existing collision deterministically

### Requirement: WikiLink synchronization
The system SHALL synchronize wiki links from compiled page content and MUST retain unresolved targets as red links until a matching page exists.

#### Scenario: Compiled page references a missing target
- **WHEN** a compiled page contains a WikiLink whose target page does not exist
- **THEN** the system records an unresolved link that can drive navigation and backlog behavior

### Requirement: Dual searchable representations
The system SHALL maintain searchable representations for both original source chunks and compiled wiki content, including the tokenizer, chunker, and embedding version information required to detect incompatible data.

#### Scenario: Compilation and source processing complete
- **WHEN** a source reaches the searchable state
- **THEN** both source evidence and compiled wiki evidence are available to retrieval with their processing versions

### Requirement: Shrinking reprocessing cleanup
The system MUST remove stale chunks, embeddings, and links when reprocessing produces fewer derived units than a previous run.

#### Scenario: Reprocessed source becomes shorter
- **WHEN** a source or compiled page is reprocessed into fewer chunks or links
- **THEN** derived rows beyond the new result are removed and cannot appear in retrieval or navigation

### Requirement: 구조화 출력의 코드 펜스와 의미 검증
시스템은 구조화 응답 전체를 감싼 코드 펜스 하나를 추가 호출 없이 SHALL 벗겨 검증한다. 펜스 바깥에 문장이 있으면 위반이다. 컴파일 페이지의 제목이나 본문이 공백이거나 전체가 placeholder(`TODO`, `{{title}}` 등)이면 시스템은 MUST 거부한다. 본문 안에 중괄호 표기가 들어 있는 것만으로 거부해서는 MUST NOT 된다. 위반은 값 없이 코드로만 SHALL 기록한다.

#### Scenario: 펜스로 감싼 정상 JSON
- **WHEN** 공급자가 코드 펜스로 감싼 유효한 JSON을 돌려준다
- **THEN** 공급자 호출은 1회이고 페이지가 저장되며 펜스 제거 사실이 사용량 메타데이터에 남는다

#### Scenario: placeholder 페이지
- **WHEN** 페이지 제목이나 본문이 공백, `TODO`, `{{title}}` 중 하나다
- **THEN** 그 응답은 검증 실패이고 잘못된 페이지는 저장되지 않는다

#### Scenario: 본문이 템플릿 문법을 설명한다
- **WHEN** 본문이 설명 문장 안에 `{{variable}}`을 포함한다
- **THEN** 페이지는 정상으로 저장된다

### Requirement: 구조화 출력 호출 상한
구조화 출력 한 작업에서 공급자가 응답을 돌려준 호출은 최초 1회와 재시도 1회를 합쳐 MUST 2회를 넘지 않는다. 시도를 소진한 실패는 작업 큐가 MUST NOT 재시도한다. 전송 실패와 공급자 오류(HTTP 오류, HTTP 200 본문의 `error`)는 모델 출력이 없는 일시 장애이므로 이 상한의 대상이 아니며 큐 재시도로 처리한다. 깨진 사용량 값이 비용 기록과 호출 상한을 MUST NOT 우회한다. 재시도 프롬프트는 JSON 파싱 실패일 때 직전 출력을 싣지 않고, 그 밖의 경우에도 직전 출력을 2,000토큰 이내로 SHALL 제한한다.

#### Scenario: 어떤 입력에도 호출은 2회를 넘지 않는다
- **WHEN** 공급자가 계속 잘못된 응답을 돌려준다
- **THEN** 공급자 호출은 2회이고 두 호출의 비용이 모두 기록되며 잡은 재시도 없이 안전하게 종결된다

#### Scenario: HTTP 200 본문의 공급자 오류
- **WHEN** 공급자가 HTTP 200 본문에 `error`를 담아 돌려준다
- **THEN** 출력 위반으로 소진하지 않고 일시 장애로 재시도되며, 충돌 판정이 판정 없이 성공으로 끝나지 않는다

#### Scenario: 파싱할 수 없는 출력의 재시도
- **WHEN** 첫 응답이 JSON이 아니다
- **THEN** 재시도 요청에 그 응답 원문이 들어가지 않는다

### Requirement: 페이지 근거 청크
시스템은 컴파일 입력의 각 원문 청크에 서버가 발급한 앵커를 SHALL 붙이고, 페이지가 낸 근거 중 발급된 앵커만 저장한다. 저장은 재실행해도 행이 늘지 않게 MUST 멱등이어야 하며, 다른 원문에서 온 같은 페이지의 근거를 MUST NOT 지운다. 근거 행은 워크스페이스 멤버만 읽을 수 있고 쓰기는 워커 전용이다. 근거가 비어도 컴파일은 실패하지 않는다.

#### Scenario: 발급되지 않은 앵커
- **WHEN** 페이지 근거에 발급 앵커와 지어낸 앵커가 섞여 있다
- **THEN** 발급 앵커만 저장되고 지어낸 앵커 수가 구조화 로그에 남는다

#### Scenario: 재컴파일
- **WHEN** 같은 잡이 두 번 실행된다
- **THEN** 근거 행 수가 늘지 않는다

#### Scenario: 다른 워크스페이스 사용자의 조회
- **WHEN** 비멤버가 근거 행을 조회한다
- **THEN** 0행을 받는다

### Requirement: 충돌 판정의 쌍 단위 격리
충돌 판정에서 한 쌍의 시도가 스키마 실패로 소진되면 시스템은 그 쌍을 판정하지 않은 것으로 SHALL 기록하고 다음 쌍으로 진행한다. 판정되지 않은 쌍을 충돌로 표시해서는 MUST NOT 된다. 공급자 전송 실패는 기존처럼 재시도 대상이다.

#### Scenario: 한 쌍만 스키마를 어긴다
- **WHEN** 두 쌍 중 첫 쌍이 시도를 소진한다
- **THEN** 둘째 쌍은 판정되고, 잡은 성공하며, 첫 쌍의 페이지는 그 판정으로 `disputed`가 되지 않는다
