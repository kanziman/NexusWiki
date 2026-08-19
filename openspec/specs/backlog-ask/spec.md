# backlog-ask Specification

## Purpose

워크스페이스 멤버가 컴파일된 위키 문서에서 발생한 미해결 레드링크 백로그(`to_wiki_id IS NULL`)를 확인하고 인용 빈도별로 우선순위를 파악하여 관련 원본 소스를 보강할 수 있도록 하며, 자연어 질문(Ask)을 통해 실시간 SSE 스트리밍 답변과 이중 Citation 마커를 제공한다.

## Requirements

### Requirement: Unresolved red-link backlog aggregation and sorting
The system SHALL aggregate unresolved wiki links (`to_wiki_id IS NULL`) by `target_slug` in the backlog view, sorted by reference count (`impact`) descending. Each aggregated topic SHALL carry a display title recovered from the `[[...]]` spelling in its referencing wiki bodies, falling back to the de-slugified `target_slug` when no spelling is found.

#### Scenario: Member views backlog list
- **WHEN** a member navigates to `/w/[workspaceId]/backlog`
- **THEN** the system displays aggregated backlog topics with their impact count, first detected timestamp, and referencing wiki pages

#### Scenario: Referencing bodies spell a topic differently
- **WHEN** the wiki pages referencing one topic contain more than one distinct `[[...]]` spelling
- **THEN** the system displays the most frequent spelling, breaking ties by the referencing page title in ascending order, so the label is identical on every render

#### Scenario: No original spelling survives in any referencing body
- **WHEN** no referencing wiki body contains a `[[...]]` occurrence for the topic
- **THEN** the system displays the de-slugified `target_slug` and still shows the raw slug alongside it

### Requirement: Backlog topic detail panel with server-side citation context
The system SHALL provide a detail panel for a selected backlog topic showing its display title, first detected timestamp, referencing wiki pages, one citation excerpt per referencing page, and the same source ingestion action offered in the list. Excerpts SHALL be produced on the server, and full wiki page bodies SHALL NOT be transferred to the client.

#### Scenario: Member opens a backlog topic
- **WHEN** a member selects a backlog topic row
- **THEN** the system opens the detail panel showing the topic, its first detected timestamp, each referencing wiki page, and an excerpt of the text surrounding the reference in that page

#### Scenario: Detail panel renders reference markup
- **WHEN** an excerpt or display title contains wiki link markup
- **THEN** the system renders the spelling as plain text and never exposes the surrounding brackets

#### Scenario: Member requests source ingestion from the detail panel
- **WHEN** a member activates the source action inside the detail panel
- **THEN** the system navigates to `/w/[workspaceId]/sources?prefillTitle=<display title>&tab=text`, matching the list row action

### Requirement: Source ingestion guidance from backlog topics
The system SHALL provide a '소스 추가' action on each backlog item that navigates to the source ingestion view with `prefillTitle` and `tab=text`.

#### Scenario: Member clicks source addition for a backlog topic
- **WHEN** a member clicks '소스 추가' on a backlog topic
- **THEN** the system navigates to `/w/[workspaceId]/sources?prefillTitle=<slug>&tab=text`

### Requirement: Real-time ask SSE streaming and citation markers
The system SHALL stream LLM answers via SSE events (`meta`, `delta`, `citations`, `done`), render citations with active markers once resolved, and handle connection errors gracefully.

#### Scenario: Member submits question in ask view
- **WHEN** a member submits a query in the Ask view
- **THEN** the system streams tokens in real-time and converts citation anchors into clickable inspection chips upon receiving citations
