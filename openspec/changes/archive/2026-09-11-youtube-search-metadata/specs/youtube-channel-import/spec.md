## MODIFIED Requirements

### Requirement: Keyword channel discovery

The system SHALL let an authorized workspace member search YouTube channels by keyword and SHALL return, for each result, the channel identifier, channel name, description, thumbnail, subscriber count, video count, and handle needed to choose between candidates. The system SHALL support continuing the result list beyond the first page. The system SHALL let the member choose a result order (relevance, video count, or view count), a relevance language hint, and a region, and SHALL apply the chosen values to the search.

#### Scenario: Member searches channels by keyword

- **WHEN** an authorized workspace member submits a non-empty search keyword
- **THEN** the system returns a bounded list of channel candidates, each carrying its channel identifier, name, description, thumbnail, subscriber count, video count, and handle, plus a continuation marker when more results exist

#### Scenario: Member continues to the next result page

- **WHEN** a member requests more results using the continuation marker from a previous search
- **THEN** the system returns the next page of channel candidates for the same keyword and the same order, language, and region as the original search

#### Scenario: Non-member attempts channel search

- **WHEN** a user who is not a member of the workspace submits a channel search
- **THEN** the system denies the request and returns no channel candidates

#### Scenario: Member changes the result order

- **WHEN** a member selects video-count or view-count order instead of the default relevance order
- **THEN** the system returns channel candidates ordered accordingly for that keyword

#### Scenario: Channel statistics cannot be enriched

- **WHEN** the channel statistics lookup for a search result fails or omits a candidate
- **THEN** the system still returns that candidate with its core identity and a distinguishable missing-statistics state, rather than dropping the candidate from the list

### Requirement: Channel video browsing

The system SHALL list the videos of a selected channel with the title, publication date, duration, thumbnail, caption availability, view count, and like count needed to judge topical relevance and transcript viability, and SHALL support continuing the list beyond the first page.

#### Scenario: Member opens a selected channel

- **WHEN** a member selects a channel from the search results
- **THEN** the system returns a bounded list of that channel's videos with the metadata needed to judge relevance and transcript viability, plus a continuation marker when more videos exist

#### Scenario: Video has no captions available

- **WHEN** a channel's video listing includes a video the provider reports as having no captions
- **THEN** the system marks that video as lacking captions in the returned listing, distinguishable from a video with captions available
