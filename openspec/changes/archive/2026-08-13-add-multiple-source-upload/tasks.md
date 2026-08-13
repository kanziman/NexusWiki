## 1. 파일 선택 및 항목 상태

- [x] 1.1 파일 탭의 선택 및 drop 처리를 여러 `File` 항목으로 확장하고, 각 항목에서 확장자를 제거한 Unicode 보존 제목을 생성한다.
- [x] 1.2 공유 제목 입력을 제거하고, 파일별 대기·중복·업로드·처리·완료·실패 상태와 접근 가능한 텍스트 피드백을 렌더링한다.

## 2. 독립 등록 흐름

- [x] 2.1 각 선택 파일을 기존 raw-byte source-upload endpoint로 독립 제출하고, 제한된 동시성으로 부분 실패와 중복을 다른 파일에 영향 없이 처리한다.
- [x] 2.2 성공한 각 등록 결과를 기존 `onIngested` 및 Sources 처리 상태 흐름에 연결한다.

## 3. 회귀 검증

- [x] 3.1 picker click·Enter·Space 및 다중 파일 drop/select의 단일 picker 활성화와 파일별 상태를 component 테스트로 검증한다.
- [x] 3.2 Unicode/Hangul filename 제목, raw-byte per-file 요청, 혼합 성공·중복·실패 결과의 독립 처리를 테스트한다.
- [x] 3.3 dashboard 테스트, typecheck, lint와 strict OpenSpec validation을 실행한다.
