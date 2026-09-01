# knowledge-quality Specification

## Purpose

컴파일된 지식의 충돌과 사람 검증 상태를 명시적으로 추적하여 사용자가 최신성·논쟁 상태와 검증 책임자를 구분하고 감사할 수 있도록 한다.

## Requirements

### Requirement: Knowledge conflict state
The system SHALL evaluate bounded same-workspace conflict candidates and MUST mark both confirmed conflicting wiki pages as disputed without exposing cross-workspace candidates.

#### Scenario: Two pages contain a confirmed factual conflict
- **WHEN** the conflict check confirms that two pages in the same workspace make incompatible claims
- **THEN** both pages transition to the disputed state and can be identified as requiring review

### Requirement: Audited human verification
An authorized human verification transition MUST record who verified the page, when verification occurred, and when that verification expires.

#### Scenario: Editor verifies a wiki page
- **WHEN** an authorized editor marks a page as verified with an expiry
- **THEN** the system stores the editor identity, verification timestamp, and expiry timestamp with the verified state

### Requirement: Verification role enforcement
The system MUST reject verification transitions from users without the required workspace role and MUST derive verifier identity from the authenticated requester rather than client-supplied audit fields.

#### Scenario: Viewer attempts verification
- **WHEN** a workspace viewer submits a verification transition or supplies another user's verifier identity
- **THEN** the system rejects the transition and preserves the existing audit state

### Requirement: Automated dispute preserves human audit
An automated transition from verified to disputed MUST preserve the preceding human verifier and verification timestamp so automation does not erase the audit trail.

#### Scenario: Verified page later becomes disputed automatically
- **WHEN** background conflict detection changes a human-verified page to disputed
- **THEN** the disputed page retains the prior human verifier and verification timestamp

### Requirement: Bulk wiki page verification
The system SHALL allow authorized editors and workspace owners to verify multiple wiki pages in a single operation, setting their `verification_status` to `verified` while recording the authenticated user's verification audit metadata and rejecting requests from users without the editor or owner role.

#### Scenario: Editor bulk-verifies multiple wiki pages
- **WHEN** an authorized editor or owner submits a bulk verification request for a list of wiki page IDs within the workspace
- **THEN** the system updates each page's `verification_status` to `verified`, sets `verified_by` to the requester's user ID, sets `verified_at` to the current timestamp, and returns the verified pages

#### Scenario: Non-editor attempts bulk verification
- **WHEN** a workspace viewer submits a bulk verification request
- **THEN** the system rejects the operation with a 403 Forbidden error and leaves all wiki pages unchanged

