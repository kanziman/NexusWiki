## ADDED Requirements

### Requirement: User-facing free credit quota feedback and limit modal
The system SHALL present an actionable free credit quota limit dialog (`CreditLimitModal`) whenever a member encounters a budget limit rejection (`402 budget_exceeded`) during conversational asking or source ingestion. The dialog SHALL inform the user that their monthly free credit quota has been exhausted, state that the quota resets on the 1st of the next month, and provide direct access to view usage details in settings.

#### Scenario: Member asks question with exhausted monthly budget
- **WHEN** a member submits a question in `AskConversation` or `AskHero` and receives a 402 budget_exceeded response
- **THEN** the system halts streaming and displays the credit limit dialog explaining the monthly free credit quota exhaustion

#### Scenario: Member uploads source with exhausted monthly budget
- **WHEN** a member uploads a file, URL, or text in `Dropzone` and receives a 402 budget_exceeded response
- **THEN** the system halts the upload pipeline and presents the credit limit dialog
