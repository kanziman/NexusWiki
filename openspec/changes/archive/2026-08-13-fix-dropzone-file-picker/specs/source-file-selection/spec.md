## Purpose

워크스페이스 멤버가 Sources 화면에서 포인터나 키보드로 단일 파일을 안전하게 선택해 등록할 수 있도록 한다.

## ADDED Requirements

### Requirement: Accessible single-file picker activation
The system SHALL let a user activate the Sources single-file picker from the visible dropzone by pointer click, Enter, or Space. It MUST open no more than one picker for a single activation.

#### Scenario: Pointer activation
- **WHEN** a user clicks the visible file dropzone
- **THEN** the system opens the operating-system file picker once

#### Scenario: Keyboard activation
- **WHEN** a user focuses the visible file dropzone and presses Enter or Space
- **THEN** the system opens the operating-system file picker once

### Requirement: Existing source selection compatibility
The system SHALL preserve existing drag-and-drop selection and single-file upload behavior when adding picker activation.

#### Scenario: Drag-and-drop selection
- **WHEN** a user drops one file on the visible dropzone
- **THEN** the system selects that file for the existing source-registration flow

#### Scenario: Existing upload contract
- **WHEN** a user selects a file through the picker and submits it
- **THEN** the system uses the existing single-file raw-byte source-upload contract
