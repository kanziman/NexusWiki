## ADDED Requirements

### Requirement: Retrieval scoring records keep per-item channel contributions
Each retrieval scoring record SHALL keep, for every ranked evidence item, the channels that contributed to it and each channel's contribution as returned by the retrieval endpoint, so that a ranking difference between two records can be traced to the channels that produced it. The record MUST NOT add evidence text.

#### Scenario: Contribution kept for a ranked item
- **WHEN** the retrieval endpoint returns an evidence item with contributions from two channels
- **THEN** the record stores both channel names and their contribution values for that item's rank

#### Scenario: Older record without contributions
- **WHEN** a record written before this rule is compared with a newer one
- **THEN** the comparison still reports every metric and does not fail because contributions are missing
