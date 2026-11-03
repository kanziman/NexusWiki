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

### Requirement: 위험한 위키 쓰기 분류와 개정 이력
시스템은 컴파일이 위키 페이지를 쓰기 전에 위험 등급을 SHALL 분류한다. 새 페이지이거나 같은 원문이 만든 미검증 페이지는 `low`, 다른 원문이 만든 페이지의 갱신이나 본문 50% 이상 축소는 `medium`, 검증 완료 또는 공개 페이지의 변경은 `high`다. 기존 본문을 바꾸는 쓰기는 이전 본문을 개정 이력으로 MUST 남긴다. 다만 복구용 `AI_CONTROL_RISK_MODE=off`에서는 분류와 이력을 모두 끈다. 개정 이력은 멤버만 읽고 쓰기는 워커 전용이다. 본문이 같으면 개정을 남기지 않는다.

#### Scenario: 새 페이지
- **WHEN** 슬러그가 없는 페이지를 컴파일한다
- **THEN** 등급은 `low`이고 개정 이력은 없다

#### Scenario: 다른 원문이 만든 페이지 갱신
- **WHEN** 다른 원문의 페이지 본문을 갱신한다
- **THEN** 등급은 `medium`이고 이전 본문이 개정 이력에 남는다

#### Scenario: 재실행
- **WHEN** 같은 잡이 두 번 실행된다
- **THEN** 개정 이력은 한 건이다

### Requirement: 위험한 쓰기의 승인 보류
`AI_CONTROL_RISK_MODE=enforce`에서 `high` 쓰기(본문과 제목·분류·별칭·신뢰도 변경)는 페이지를 바꾸지 않고 승인 대기 제안으로 MUST 저장한다. 같은 페이지와 원문의 대기 제안은 재실행해도 하나로 유지되고 최신 내용으로 갱신된다. `shadow`에서는 쓰기를 진행하되 개정 이력에 `high`로 기록한다. `editor` 이상만 승인이나 거부를 할 수 있고, 다른 워크스페이스의 제안은 MUST 처리할 수 없다. 승인하면 이전 본문을 개정으로 남기고 어휘와 벡터 검색 색인까지 갱신한다. 재컴파일로 본문이 바뀐 페이지도 벡터 색인을 MUST 갱신한다. 승인은 재실행해도 한 번만 적용된다.

#### Scenario: 검증된 페이지 재컴파일
- **WHEN** `enforce`에서 검증 완료 페이지의 본문이 바뀌는 컴파일이 실행된다
- **THEN** 페이지 본문은 그대로이고 승인 대기 제안이 하나 생기며 잡은 성공한다

#### Scenario: 두 번 재컴파일
- **WHEN** 같은 페이지와 원문으로 다시 컴파일한다
- **THEN** 대기 제안은 하나뿐이고 내용은 최신이다

#### Scenario: editor가 승인한다
- **WHEN** `editor`가 대기 제안을 승인한다
- **THEN** 잡이 페이지와 색인을 갱신하고 이전 본문이 개정 이력에 남으며 제안은 `applied`가 된다

#### Scenario: viewer나 비멤버가 승인을 시도한다
- **WHEN** `viewer`나 비멤버가 제안을 승인한다
- **THEN** HTTP 403으로 거부되고 페이지와 제안은 바뀌지 않는다

#### Scenario: 거부한다
- **WHEN** `editor`가 대기 제안을 거부한다
- **THEN** 페이지는 그대로이고 제안은 `rejected`가 된다

### Requirement: 기존 본문을 보존하는 근거 백필
시스템은 기존 위키 페이지의 청크 근거를 채우기 위해 페이지를 재컴파일하지 않는 관리용 백필을 SHALL 제공한다. 백필은 페이지의 본문·제목·메타데이터·검증 상태·검색 색인과 기존 근거를 MUST 보존한다. 후보는 해당 페이지의 기존 문서 출처에 포함되는 원문의 동일 워크스페이스 청크로 MUST 제한한다. 문서 출처에 속한다는 사실이나 유사도 점수만으로 근거 연결을 확정해서는 MUST NOT 된다.

#### Scenario: 검증 완료 페이지의 근거 보완
- **WHEN** 운영자가 검증 완료 페이지에 대해 검토한 청크 연결을 적용한다
- **THEN** 승인된 근거 연결만 추가되고 페이지와 검색 색인은 변하지 않는다

#### Scenario: 후보 생성
- **WHEN** 운영자가 백필 후보 보고서를 생성한다
- **THEN** DB 쓰기나 재컴파일 잡 실행 없이 후보와 판단에 필요한 페이지·청크 대조 정보 및 근거 미확정 페이지를 얻는다

#### Scenario: 다른 워크스페이스 또는 출처의 후보
- **WHEN** 후보가 다른 워크스페이스나 페이지의 기존 문서 출처 밖 청크를 가리킨다
- **THEN** 후보 생성·적용에서 거부되고 근거 연결은 추가되지 않는다

### Requirement: 검토 결과의 제한된 적용
시스템은 후보 생성과 적용을 SHALL 분리하고 명시적으로 검토·승인된 연결만 MUST 적용한다. 검토된 페이지·원문·청크의 내용 또는 출처 관계가 바뀌면 낡은 결과를 MUST 거부한다. 한 승인 배치의 검증과 추가는 MUST 원자적이어야 하며 하나라도 유효하지 않으면 배치 전체를 거부한다. 적용은 기존 근거를 지우지 않는 추가 방식이어야 하며 반복 실행 시 중복을 MUST 만들지 않는다. 연결 근거가 부족한 페이지는 미확정으로 남기고, 처리율이나 연결률을 높이기 위해 추정 연결을 MUST NOT 추가한다. 백필 전용 조회·쓰기 경로는 워커 운영 권한에 한정하고 일반 사용자·익명 역할에 MUST NOT 허용한다. 운영 적용은 운영자가 별도로 승인·실행하며 에이전트가 자동 실행하지 않는다.

#### Scenario: 승인하지 않은 후보
- **WHEN** 후보 보고서에 있지만 적용 대상으로 승인하지 않은 연결이 있다
- **THEN** 그 연결은 저장되지 않는다

#### Scenario: 검토 후 내용 변경
- **WHEN** 보고서 생성 후 페이지·원문·청크 내용 또는 출처 관계가 변경된다
- **THEN** 해당 낡은 검토 결과의 적용을 거부하고 재검토 필요를 알린다

#### Scenario: 반복 적용과 기존 근거
- **WHEN** 같은 검토 결과를 반복 적용한다
- **THEN** 새 중복 행이 생기지 않고 기존 또는 다른 원문의 근거는 보존된다

#### Scenario: 근거가 부족하다
- **WHEN** 검토자가 뒷받침하는 청크를 확정할 수 없다
- **THEN** 해당 페이지는 미확정으로 보고되고 근거 연결 없이 남는다

#### Scenario: 배치 일부가 유효하지 않다
- **WHEN** 승인 배치의 한 연결이 없거나 낡았거나 허용 범위 밖이다
- **THEN** 다른 연결도 저장되지 않고 배치 전체가 실패한다

#### Scenario: 검토와 적용 사이의 동시 변경
- **WHEN** 다른 처리가 페이지·원문·청크를 변경하거나 삭제하는 동안 백필이 적용된다
- **THEN** 검토한 상태에서의 연결 추가 또는 배치 전체 실패만 일어나며 낡은 연결이 부분 저장되지 않는다

#### Scenario: 일반 사용자와 익명 역할
- **WHEN** 일반 사용자나 익명 역할이 백필 전용 경로를 실행한다
- **THEN** 요청이 거부되고 운영 보고서 본문과 근거 쓰기 권한을 얻지 못한다
