## ADDED Requirements

### Requirement: Non-retryable provider credit exhaustion
The system SHALL classify model provider credit exhaustion (HTTP 402) as a non-retryable failure. When an external model provider responds with HTTP 402 Payment Required, the worker MUST terminate the job as `dead` immediately without retrying up to `max_attempts` and SHALL persist a sanitized credit exhaustion failure token.

#### Scenario: Model provider returns 402 Payment Required
- **WHEN** a background job encounters an HTTP 402 response from an external model provider
- **THEN** the worker dead-letters the job on the first attempt and stores a sanitized `provider_credit_exhausted` failure token
