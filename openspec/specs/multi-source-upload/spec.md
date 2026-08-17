# multi-source-upload Specification

## Purpose

워크스페이스 멤버가 여러 자료를 한 번에 등록하되, 각 자료의 업로드와 처리 결과를 독립적으로 확인하고 관리할 수 있도록 한다.

## Requirements

### Requirement: Independent multi-file source registration
The system SHALL let a workspace member select or drop multiple supported files in the Sources file flow. It MUST register each selected file as an independent source using the existing per-file upload contract, so a duplicate or failed file does not cancel other selected files.

#### Scenario: Multiple files are selected
- **WHEN** a workspace member selects multiple supported files from the file picker
- **THEN** the system creates an independent registration attempt and status record for each file

#### Scenario: Files are dropped together
- **WHEN** a workspace member drops multiple supported files on the visible file dropzone
- **THEN** the system queues each dropped file as an independent registration attempt

#### Scenario: One registration fails
- **WHEN** one file in a multi-file registration is rejected, duplicated, or fails to upload
- **THEN** the system reports that file's outcome without cancelling the registration attempts for the other selected files

### Requirement: Filename-derived source titles
The system SHALL derive each multi-file source title from its filename with the final file extension removed. It MUST preserve Unicode characters, including Hangul, in the derived title and MUST not require or display a shared title field for the multi-file flow.

#### Scenario: Unicode filename title
- **WHEN** a member selects a file named `IVI 대시보드 요구사항.pdf`
- **THEN** the system registers that file with the derived title `IVI 대시보드 요구사항`

#### Scenario: Multiple file title fields are avoided
- **WHEN** the file flow contains more than one selected file
- **THEN** the system does not display a single title input that would apply to every file

### Requirement: Per-file registration feedback
The system SHALL expose a separate status for every file in a multi-file registration. The status MUST distinguish queued, duplicate, uploading, processing, completed, and failed outcomes without relying on color alone.

#### Scenario: Mixed registration outcomes
- **WHEN** a multi-file registration produces a duplicate, an upload failure, and a successful source registration
- **THEN** the system presents the corresponding distinct outcome for each affected file

#### Scenario: Successful processing continues
- **WHEN** a file is successfully registered and its processing job advances
- **THEN** the system exposes that file's processing and completed states independently from the other selected files
