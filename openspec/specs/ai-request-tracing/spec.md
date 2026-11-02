# ai-request-tracing Specification

## Purpose

사용자 요청과 수집 작업에서 시작된 API, 내부 호출, 잡, LLM 호출을 하나의 식별자로 되짚고, 본문을 노출하지 않으면서 통제 결정을 관측할 수 있게 한다.

## Requirements

### Requirement: 서버 발급 trace 식별자
시스템은 API 요청마다 서버가 새 `trace_id`를 MUST 발급하고, 성공과 오류를 포함한 모든 응답의 `X-Trace-Id` 헤더로 SHALL 돌려준다. 클라이언트가 보낸 trace 값은 신뢰하지 않고 MUST 무시한다.

#### Scenario: 일반 요청
- **WHEN** 클라이언트가 API를 호출한다
- **THEN** 응답 헤더에 서버가 발급한 `trace_id`가 있고 그 요청의 구조화 로그에 같은 값이 남는다

#### Scenario: 클라이언트가 trace 값을 위조한다
- **WHEN** 요청에 임의의 `X-Trace-Id` 헤더가 포함되어 있다
- **THEN** 시스템은 그 값을 사용하지 않고 새 값을 발급한다

#### Scenario: 오류 응답
- **WHEN** 요청이 권한 또는 입력 오류로 실패한다
- **THEN** 오류 응답에도 `X-Trace-Id` 헤더가 있다

### Requirement: 내부 호출과 Ask 턴으로의 전파
시스템은 API에서 워커로 가는 질의 임베딩과 LLM 스트림 내부 호출에 `trace_id`를 MUST 전달하고, 워커의 로그와 사용량 기록은 같은 값을 SHALL 사용한다. Ask 턴 행은 시작한 요청의 `trace_id`를 MUST 저장한다.

#### Scenario: Ask 요청 한 건
- **WHEN** 멤버가 근거가 있는 질문을 한다
- **THEN** API 로그, 워커 로그, 질의 임베딩과 LLM 사용량 행, Ask 턴이 모두 같은 `trace_id`를 가진다

#### Scenario: 워크스페이스 헤더가 없는 질의 임베딩
- **WHEN** 프로세스 컨텍스트에 다른 워크스페이스 값이 묶여 있는 상태에서 헤더가 없거나 형식이 틀린 질의 임베딩이 온다
- **THEN** 임베딩은 정상 처리되고 사용량은 어떤 워크스페이스에도 기록되지 않는다

#### Scenario: 내부 호출 호환성
- **WHEN** 배포 중 trace를 전달하지 않는 이전 버전 API가 워커를 호출한다
- **THEN** 워커는 요청을 거부하지 않고 자체 `trace_id`를 발급해 처리한다

### Requirement: 잡 체인의 trace 연속성
수집 잡은 시작한 요청의 `trace_id`를 MUST 저장하고, 후속 단계 잡은 선행 잡의 값을 SHALL 물려받는다. 재시도, 회수, 반납은 값을 MUST NOT 바꾼다.

#### Scenario: 수집 체인 완료
- **WHEN** 멤버가 원문을 등록해 `parse`, `compile`, `link_sync`, `embed`, `conflict_check`가 차례로 실행된다
- **THEN** 모든 단계 잡과 그 사용량 행이 같은 `trace_id`를 가진다

#### Scenario: 실패한 잡의 재시도
- **WHEN** 실패하거나 회수된 잡을 다시 실행하거나 멤버가 dead 잡을 재시도한다
- **THEN** 잡은 원래 `trace_id`를 유지한다

#### Scenario: 이미 큐에 있는 대상의 중복 인큐
- **WHEN** 같은 대상으로 다시 인큐해 기존 잡이 반환된다
- **THEN** 기존 잡의 `trace_id`를 덮어쓰지 않는다

#### Scenario: trace가 없던 기존 잡
- **WHEN** 마이그레이션 이전에 만들어진 잡을 처리한다
- **THEN** 처리는 그대로 진행되고 값이 없는 상태로 기록된다

### Requirement: Router 결정의 shadow 기록
시스템은 Ask 턴과 컴파일 잡마다 Router 결정과 사유 코드를 SHALL 기록한다. Ask 턴에서는 근거 0건(`NO_EVIDENCE`) 단락만 실행하고 나머지 결정(`LOOKUP`, `SINGLE_KIND`, `STANDARD`)은 기록만 하며 LLM 호출 여부를 바꾸지 않는다. 컴파일 잡에서는 입력 지문(컴파일 본문 해시, `template_id`, `model`)이 직전 성공 컴파일과 같고 해당 원문에서 생성된 위키 페이지가 워크스페이스에 이미 존재할 때(`SKIP_UNCHANGED`) 공급자 LLM 호출을 MUST 생략하고 후속 체인(`link_sync`)으로 진행해야 한다. 지문 조회 실패나 기존 위키 페이지 부재 시에는 LLM 호출을 생략하지 않고 `STANDARD` 또는 `TRUNCATED`로 실행한다.

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

### Requirement: 관측 데이터의 본문 금지
trace, 로그, 사용량, Router 결정, 외부 관측 데이터는 질문, 프롬프트, 응답, 원문, 위키 본문을 MUST NOT 포함한다.

#### Scenario: 고유한 문자열이 담긴 Ask와 컴파일
- **WHEN** 식별 가능한 문자열을 담은 질문과 원문이 전체 경로를 통과한다
- **THEN** 관측용으로 저장되거나 전송된 어떤 값에도 그 문자열이 나타나지 않는다

### Requirement: 선택적 외부 관측 내보내기
시스템은 자격 증명이 설정된 경우에만 trace 메타데이터를 외부 관측 서비스로 SHALL 내보낸다. 워크스페이스 식별자는 원문이 아닌 해시로 MUST 보내고, 자격 증명 값은 로그에서 MUST 마스킹한다. 내보내기 실패는 요청과 잡의 결과를 MUST NOT 바꾸며, 월 상한 판정과 Control Room은 외부 서비스에 MUST NOT 의존한다. 외부 관측 비밀 키는 워커만 가지며 API 프로세스 설정에 MUST NOT 존재한다. API는 종결된 턴의 보고서를 내부 토큰으로 인증되는 워커 라우트에 넘긴다.

#### Scenario: 자격 증명이 없다
- **WHEN** 외부 관측 자격 증명 없이 프로세스가 시작된다
- **THEN** 프로세스는 정상 기동하고 내보내기는 비활성이다

#### Scenario: Ask 턴을 내보낸다
- **WHEN** API에서 Ask 턴이 종결된다
- **THEN** API는 답변을 기다리게 하지 않고 보고서를 워커 내부 라우트로 넘기며, 워커가 같은 `trace_id`로 내보내고, 워커에 닿지 못해도 턴과 응답은 영향받지 않는다

#### Scenario: 내부 라우트에 인증 없이 호출한다
- **WHEN** 내부 토큰 없이 내보내기 라우트를 호출하거나 허용되지 않은 필드를 함께 보낸다
- **THEN** 호출은 거부되고 아무것도 내보내지 않는다

#### Scenario: 외부 서비스 장애
- **WHEN** 내보내기 요청이 실패하거나 시간 초과된다
- **THEN** 사용자 응답과 잡 상태, 사용량 기록은 영향받지 않는다

#### Scenario: 프로세스 종료
- **WHEN** 워커가 SIGTERM을 받는다
- **THEN** 남은 데이터를 제한 시간 안에서만 내보내고 잡 반납 동작을 지연시키지 않는다
