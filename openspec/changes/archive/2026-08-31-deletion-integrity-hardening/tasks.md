## 1. 참조 보호 삭제 경계

- [x] 1.1 GitHub sub-issue #116을 만들고 umbrella #112 아래에 연결했다. AC: Given 원문 삭제 정합성 change가 준비됐을 때, When 수직 슬라이스 추적을 시작하면, Then umbrella #112 아래에 확인 가능한 sub-issue가 존재한다.
- [x] 1.2 참조·활성 작업 검사를 통과한 원문만 삭제하고 Storage 정리 잡을 함께 만드는 보안 정의자 RPC와 격리 테스트를 구현한다. AC: Given owner의 원문이 위키·공개본·Ask·활성 잡에서 참조되거나 참조되지 않을 때, When 삭제 RPC를 호출하면, Then 참조 중이면 모든 데이터를 보존한 409가 반환되고 미참조이면 원문 삭제와 정리 잡 생성이 한 트랜잭션으로 완료된다.
- [x] 1.3 API 삭제 엔드포인트를 RPC 기반 202/409/403 계약으로 전환하고 대시보드에 `source_in_use` 안내를 표시한다. AC: Given owner·non-owner·타 테넌트 사용자가 삭제를 요청할 때, When API와 확인 모달을 사용하면, Then 각 요청이 202·409·403으로 일관되게 매핑되고 사용자는 참조 해제 안내를 받는다.

## 2. 내구성 있는 Storage 정리

- [x] 2.1 GitHub sub-issue #115를 만들고 umbrella #112 아래에 연결했다. AC: Given Storage 정리 슬라이스가 준비됐을 때, When 구현 추적을 시작하면, Then umbrella #112 아래에 확인 가능한 sub-issue가 존재한다.
- [x] 2.2 정리 대기 객체를 일반 멤버가 읽지 못하도록 Storage SELECT 정책을 보강한다. AC: Given raw source 행이 삭제되고 Storage 객체 정리 잡이 대기 중일 때, When authenticated 멤버가 해당 경로를 읽으면, Then 정책이 객체를 노출하지 않고 service role 정리 경로는 유지된다.
- [x] 2.3 `delete_source_storage` worker 핸들러와 멱등 Storage 삭제 테스트를 구현한다. AC: Given 정리 잡의 workspace와 Storage 경로가 일치하거나 불일치하고 객체가 존재하거나 이미 없을 때, When worker가 잡을 처리하면, Then 같은 workspace의 존재 객체와 404는 성공하고 경로 불일치와 일시 오류는 예외로 전파되어 큐 회계가 처리한다.

## 3. 실제 인용 뷰어 폴백

- [x] 3.1 GitHub sub-issue #117을 만들고 umbrella #112 아래에 연결했다. AC: Given 통합 인용 뷰어 슬라이스가 준비됐을 때, When 구현 추적을 시작하면, Then umbrella #112 아래에 확인 가능한 sub-issue가 존재한다.
- [x] 3.2 `ContentViewer`와 Ask 마커 라우팅에 삭제·접근 불가 원문 및 위키 상태를 구현하고 미사용 `CitationSidePanel` 보강을 제거한다. AC: Given 저장된 답변이 삭제되었거나 접근 불가한 인용 ID를 포함할 때, When 사용자가 해당 마커를 누르면, Then 실제 콘텐츠 뷰어가 알맞은 탭에서 명시적 unavailable 상태를 표시하고 무한 로딩이나 무반응이 발생하지 않는다.

## 4. 검증과 계약 동기화

- [x] 4.1 API·worker·dashboard 관련 테스트, typecheck, lint, strict OpenSpec validation을 새로 실행한다. AC: Given 모든 구현 task가 완료됐을 때, When 필수 검증을 실행하면, Then 어떤 검증도 skip 또는 실패를 성공으로 오인하지 않고 결과가 기록된다.
- [x] 4.2 delta spec을 정본에 동기화하고 strict specs validation 후 change를 아카이브한다. AC: Given 구현과 검증이 완료됐을 때, When OpenSpec 동기화·아카이브 절차를 실행하면, Then 정본과 아카이브가 같은 202·409·403 및 인용 폴백 계약을 보존한다.
