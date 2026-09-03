## MODIFIED Requirements

### Requirement: Consistent backlog document hierarchy
The system SHALL present backlog topics using the same searchable document-table hierarchy as other workspace libraries while preserving topic selection and source-addition actions as distinct controls. Topics SHALL additionally be filterable by how many wiki pages cite them, so that gaps cited by several documents can be separated from those cited by one. The filter controls and the search input SHALL be presented on one aligned toolbar row so that their top and bottom edges coincide. Filtering and searching SHALL compose rather than replace each other.

Rows SHALL keep a consistent height regardless of how many wiki pages cite a topic; a row that would exceed the available width for citation links SHALL show a bounded number of them plus an indication of how many remain, rather than growing taller. Regardless of the underlying markup, the list MUST continue to expose row and column relationships to assistive technology, because the citation-frequency column is this view's ordering axis. On narrow viewports the list SHALL reflow without forcing horizontal scrolling of the page.

#### Scenario: Member scans and filters backlog topics
- **WHEN** the backlog contains unresolved topics and the member enters a search query
- **THEN** matching topic names, raw slugs, or referring wiki titles remain visible with impact and first-detected context in a readable row hierarchy

#### Scenario: Member operates a backlog row
- **WHEN** the member selects the topic control, a referring wiki link, or the source-addition action within one row
- **THEN** only the selected control's documented destination or panel opens, without the other row actions firing

#### Scenario: Member separates multi-cited gaps from single-cited ones
- **WHEN** the backlog holds topics cited by two or more wiki pages alongside topics cited by exactly one, and the member selects the multi-citation filter
- **THEN** only topics cited by two or more pages remain listed, and each filter control shows how many topics it would display

#### Scenario: Member combines a filter with a search query
- **WHEN** a filter is active and the member also enters a search query
- **THEN** only topics satisfying both the filter and the query remain listed, rather than either condition replacing the other

#### Scenario: Member views a topic cited by many wiki pages
- **WHEN** a topic is cited by more wiki pages than its row can display
- **THEN** the row shows a bounded number of citation links plus a remainder indicator, and its height matches rows for topics with fewer citations

#### Scenario: Assistive technology user reads the citation-frequency column
- **WHEN** a screen reader user navigates the backlog list
- **THEN** the list is exposed with row and column structure, and each topic's citation frequency is associated with the column header naming it

#### Scenario: Member opens the backlog on a narrow viewport
- **WHEN** a member opens the backlog on a narrow viewport
- **THEN** the rows reflow to fit without requiring horizontal scrolling of the page

## ADDED Requirements

### Requirement: Backlog prioritization summary
The system SHALL present a summary above the backlog list covering the number of unresolved topics, how many distinct wiki pages are affected by them, which topic is cited most, and which unresolved topic has waited longest since first detection. Each summary figure SHALL be derived from the same workspace data the list itself renders, so that a figure never contradicts the rows below it. Every figure SHALL be stated in text rather than conveyed through color alone. The summary SHALL be omitted when the backlog holds no topics.

#### Scenario: Member opens a backlog holding unresolved topics
- **WHEN** a member opens the backlog for a workspace with unresolved topics
- **THEN** the summary reports the unresolved topic count, the count of distinct affected wiki pages, the most-cited topic with its citation count, and the longest-waiting topic with how long it has waited, each matching the listed topics

#### Scenario: Several topics tie for most cited
- **WHEN** more than one topic shares the highest citation count
- **THEN** the summary names one of them deterministically, so the same workspace data always produces the same summary

#### Scenario: Backlog is empty
- **WHEN** a member opens the backlog for a workspace with no unresolved topics
- **THEN** the summary is not shown and the empty state is presented instead

### Requirement: Backlog aggregate load failure is distinguishable from an empty backlog
When a query backing the backlog list returns an operational error rather than a successful empty result, the system MUST NOT present the failure as an empty backlog or as an assertion that the workspace has no unresolved links. The view SHALL report that the backlog could not be loaded and SHALL NOT show the resolved-state empty message.

#### Scenario: The backlog query fails
- **WHEN** the unresolved-link or referencing-page query returns an operational error
- **THEN** the view reports that the backlog could not be loaded, and does not claim that every wiki link is resolved

#### Scenario: The backlog is genuinely empty
- **WHEN** the queries succeed and return no unresolved links
- **THEN** the view shows the resolved-state empty message rather than a load-failure message
