## Why

The Sources file dropzone accepts drag-and-drop but clicking its visible target does not open the operating-system file picker. Keyboard users cannot activate the target with Enter or Space, blocking the primary source-upload path.

## What Changes

- Make the existing single-file dropzone activate its file input through click, Enter, and Space.
- Preserve drag-and-drop, selected-file state, raw-byte upload requests, and existing validation.
- Add regression coverage for pointer and keyboard activation.

## Capabilities

### New Capabilities

- `source-file-selection`: Accessible selection of one source file from the Sources dropzone.

### Modified Capabilities

None.

## Impact

- Affected code: `apps/dashboard/components/Dropzone.tsx` and its tests.
- No changes to source APIs, RLS, MIME policy, storage, or multi-file upload behavior.
