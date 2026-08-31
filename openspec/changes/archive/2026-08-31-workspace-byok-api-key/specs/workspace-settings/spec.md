## ADDED Requirements

### Requirement: BYOK custom AI API key management
The system SHALL allow workspace owners to configure, test, and remove a custom OpenRouter or OpenAI API key (Bring Your Own Key) in the general settings panel. Non-owners SHALL only see masked status or read-only indicators.

#### Scenario: Owner registers and saves a custom API key
- **WHEN** the workspace owner inputs a valid custom API key (e.g. `sk-or-v1-...`) and saves
- **THEN** the system persists the key, displays the masked key format (e.g. `sk-or-v1-••••••••1a2b`), and displays a success notification

#### Scenario: Owner deletes a custom API key
- **WHEN** the workspace owner clicks the delete/remove API key button and confirms
- **THEN** the system removes the custom key and reverts the workspace to the default free credit quota

#### Scenario: Non-owner views the general settings BYOK section
- **WHEN** a viewer or editor views the general settings panel
- **THEN** the API key input is disabled or masked without exposing the raw secret key
