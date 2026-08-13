## Why

현재 Sources 화면은 한 번에 한 파일만 등록할 수 있어 여러 자료를 위키로 컴파일하려는 사용자의 반복 작업이 크다. 파일별 실패와 중복을 독립적으로 처리하면서 한글 파일명을 제목으로 안전하게 보존하는 다중 등록 흐름이 필요하다.

## What Changes

- Sources dropzone과 파일 선택기가 여러 지원 파일을 한 번에 선택하거나 드롭하도록 확장한다.
- 각 파일을 기존 단일-file raw-byte 업로드 계약으로 독립 등록하고, 한 파일의 중복 또는 실패가 다른 파일의 처리를 중단하지 않도록 한다.
- 다중 파일 흐름에서는 공통 제목 입력을 표시하지 않고, 파일 확장자를 제거한 이름을 각 source 제목으로 사용한다.
- 각 파일의 대기, 중복, 업로드, 처리, 완료, 실패 상태를 개별적으로 표시한다.
- 한글을 포함한 Unicode 파일명으로 만든 제목과 생성된 위키 페이지의 탐색을 회귀 검증한다.

## Capabilities

### New Capabilities

- `multi-source-upload`: 여러 파일을 독립적인 source 등록 및 처리 단위로 관리하는 Sources 업로드 흐름

### Modified Capabilities

- `source-file-selection`: 기존 dropzone과 파일 선택기의 단일 파일 선택 요구사항을 다중 파일 선택 및 드롭 동작으로 확장

## Impact

- 영향 영역: `apps/dashboard/components/Dropzone.tsx`, Sources 화면의 업로드 상태 및 테스트
- 기존 per-file source-upload API, MIME/용량 검증, Storage 업로드 순서, 중복 처리, RLS, job lifecycle은 유지한다.
- 새 배치 업로드 API나 데이터베이스 스키마 변경은 포함하지 않는다.
