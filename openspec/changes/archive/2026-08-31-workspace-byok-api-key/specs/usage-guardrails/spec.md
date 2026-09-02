## ADDED Requirements

### Requirement: BYOK unlimited quota and limit modal integration
The system SHALL treat workspaces with an active custom API key as having an unlimited monthly quota, bypassing 402 budget exceeded errors. The credit limit modal SHALL offer a direct action link for users to register their own API key.

#### Scenario: Workspace with custom API key performs operations
- **WHEN** a workspace has a registered custom API key
- **THEN** the system bypasses the default 500-credit quota check and displays an unlimited API key status badge in navigation and account menus

#### Scenario: Credit limit modal offers BYOK setup
- **WHEN** a user encounters the credit limit modal
- **THEN** the modal presents a direct link to register their own API key in workspace settings for unlimited usage
