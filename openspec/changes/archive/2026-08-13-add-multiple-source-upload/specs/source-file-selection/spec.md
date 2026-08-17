## MODIFIED Requirements

### Requirement: Accessible multi-file picker activation
The system SHALL let a user activate the Sources file picker from the visible dropzone by pointer click, Enter, or Space. It MUST open no more than one picker for a single activation and MUST allow the picker to return one or more files.

#### Scenario: Pointer activation
- **WHEN** a user clicks the visible file dropzone
- **THEN** the system opens the operating-system file picker once and accepts one or more selected files

#### Scenario: Keyboard activation
- **WHEN** a user focuses the visible file dropzone and presses Enter or Space
- **THEN** the system opens the operating-system file picker once and accepts one or more selected files

### Requirement: Existing source selection compatibility
The system SHALL preserve existing drag-and-drop selection and per-file raw-byte source-upload behavior while supporting one or more selected files.

#### Scenario: Drag-and-drop selection
- **WHEN** a user drops one or more files on the visible dropzone
- **THEN** the system selects every dropped file for its own source-registration flow

#### Scenario: Existing upload contract
- **WHEN** a user submits selected files
- **THEN** the system uses the existing single-file raw-byte source-upload contract separately for each file
