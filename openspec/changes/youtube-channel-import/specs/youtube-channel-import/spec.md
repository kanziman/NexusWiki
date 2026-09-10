## Purpose

키워드로 유튜브 채널을 찾아 그 채널의 영상 중 주제와 관련된 것만 골라 자막을 원문 소스로 일괄 수집하는 경계를 정의한다. 개별 영상은 각각 독립적으로 인용 가능한 원문이어야 하고, 자막을 얻지 못하는 영상은 나머지 수집을 중단시키지 않아야 한다.

## ADDED Requirements

### Requirement: Keyword channel discovery

The system SHALL let an authorized workspace member search YouTube channels by keyword and SHALL return, for each result, the channel identifier, channel name, description, and thumbnail needed to choose between candidates. The system SHALL support continuing the result list beyond the first page.

#### Scenario: Member searches channels by keyword

- **WHEN** an authorized workspace member submits a non-empty search keyword
- **THEN** the system returns a bounded list of channel candidates, each carrying its channel identifier, name, description, and thumbnail, plus a continuation marker when more results exist

#### Scenario: Member continues to the next result page

- **WHEN** a member requests more results using the continuation marker from a previous search
- **THEN** the system returns the next page of channel candidates for the same keyword

#### Scenario: Non-member attempts channel search

- **WHEN** a user who is not a member of the workspace submits a channel search
- **THEN** the system denies the request and returns no channel candidates

### Requirement: Search quota conservation

The system MUST NOT consume external search quota for a repeated identical channel search, and MUST serve a repeated search from previously stored results while they remain valid.

#### Scenario: Same keyword is searched again

- **WHEN** a member submits a channel search whose keyword and region match a previous search that is still valid
- **THEN** the system returns the stored result without issuing a new external search request

### Requirement: Exhausted external quota outcome

The system MUST return a distinguishable, actionable outcome when the external YouTube quota is exhausted, and MUST NOT present the failure as an empty result set.

#### Scenario: Quota is exhausted during channel search

- **WHEN** a member submits a channel search and the external quota is exhausted
- **THEN** the system returns a distinguishable quota-exhausted outcome that the interface can explain, rather than reporting zero channels found

### Requirement: Channel video browsing

The system SHALL list the videos of a selected channel with the title, publication date, duration, and thumbnail needed to judge topical relevance, and SHALL support continuing the list beyond the first page.

#### Scenario: Member opens a selected channel

- **WHEN** a member selects a channel from the search results
- **THEN** the system returns a bounded list of that channel's videos with the metadata needed to judge relevance, plus a continuation marker when more videos exist

### Requirement: Selective batch registration

The system SHALL register only the videos a member explicitly selected, SHALL create one independently identifiable source per selected video, and SHALL report a per-video outcome so that a partial failure is distinguishable from a total failure. Registration SHALL target the workspace the member is acting in.

#### Scenario: Member registers a subset of a channel's videos

- **WHEN** a member selects a subset of the listed videos and confirms registration
- **THEN** the system registers exactly the selected videos, one source per video, and returns an outcome for each selected video

#### Scenario: Some selected videos cannot be registered

- **WHEN** registration succeeds for some selected videos and fails for others
- **THEN** the successful videos remain registered and the response identifies which videos failed and why

#### Scenario: Registration targets another workspace

- **WHEN** a registration request names a workspace the requester is not a member of
- **THEN** the system denies the request and registers no source

### Requirement: Transcript as source content

The system SHALL use a selected video's transcript as the registered source's content so the video becomes citable by the same chunk coordinates as any other source, and SHALL retain the video identity needed to return to the original.

#### Scenario: Video with an available transcript is registered

- **WHEN** a selected video's transcript can be retrieved
- **THEN** the registered source carries the transcript as its content and retains the video identity needed to open the original video

#### Scenario: Citation resolves to a registered video

- **WHEN** a downstream citation refers to a chunk of a registered video source and its character range
- **THEN** slicing the stored transcript by that range yields exactly the stored chunk content

### Requirement: Distinguishable transcript failure

The system MUST end processing with a distinguishable, safe reason when a selected video's transcript cannot be obtained, and a single such failure MUST NOT stop the other selected videos from completing.

#### Scenario: Selected video has no transcript

- **WHEN** a selected video's transcript cannot be retrieved because the video has none, is private, or is otherwise unavailable
- **THEN** that video's processing ends with a distinguishable failure reason the interface can explain, and the remaining selected videos continue processing

### Requirement: Already collected video

The system MUST detect a video already collected in the workspace, MUST NOT create duplicate derived records for it, and MUST return a distinguishable already-collected outcome.

#### Scenario: Previously registered video is selected again

- **WHEN** a member registers a video that the workspace already collected
- **THEN** the system reports that video as already collected and does not grow source, chunk, page, or embedding records
