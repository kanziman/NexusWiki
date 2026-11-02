## ADDED Requirements

### Requirement: Terminal outcome for failed answer streams
The system MUST finish every started Ask turn with a terminal state whenever the failure happens while the server can still write the turn. A malformed provider frame or a provider error frame during streaming MUST end the turn with the `llm_unavailable` error outcome in the `citations` event and MUST NOT persist partial generated text as a resolved answer. A failure while gathering evidence or preparing the prompt MUST also end the turn with an error outcome. A client that disconnects before the turn ends is outside this requirement and is tracked by issue #170.

#### Scenario: Provider stream contains a malformed frame
- **WHEN** the answer stream delivers a data frame that cannot be parsed
- **THEN** the client receives the error outcome and `done`, and the stored turn has status `error` rather than `streaming`

#### Scenario: Provider stream contains a frame with the wrong shape
- **WHEN** the answer stream delivers a parseable frame whose `choices`, `delta`, or `content` has an unexpected type
- **THEN** the client receives the error outcome and `done`, and the stored turn has status `error` rather than `streaming`

#### Scenario: Preparation fails after the turn started
- **WHEN** retrieval, evidence content lookup, template selection, or prompt rendering fails after the turn was started
- **THEN** the client receives an error outcome and `done`, the stored turn has status `error`, and the provider is not called

#### Scenario: Provider reports an error mid-stream
- **WHEN** the answer stream delivers a provider error frame after partial text
- **THEN** the stored turn has status `error`, contains no partial answer, and is not reported as resolved

### Requirement: Citation quality metrics exclude removed anchors
The system SHALL compute dual-citation and unsourced-sentence metrics from the answer after unissued anchors are removed, and SHALL persist the metrics with the turn without storing additional answer text. An anchor placed directly after sentence-ending punctuation MUST count toward the sentence it follows.

#### Scenario: A sentence cites only fabricated anchors
- **WHEN** a sentence's only anchors were not issued for the request
- **THEN** that sentence does not count as dual-cited and counts as unsourced

#### Scenario: Anchor follows the period
- **WHEN** generated text places a valid anchor immediately after the sentence's period
- **THEN** that sentence counts as cited

### Requirement: Partial retrieval is reported to the answer client
The system SHALL report retrieval channels that failed for the request in Ask metadata, and MUST NOT report a channel that is intentionally disabled by policy.

#### Scenario: One retrieval channel fails
- **WHEN** a channel fails while another channel returns evidence
- **THEN** the `meta` event names the failed channel and the client shows its partial-search notice

#### Scenario: Graph channel is disabled
- **WHEN** all enabled channels succeed and the graph channel is disabled by policy
- **THEN** the `meta` event reports no missing channels and no notice is shown
