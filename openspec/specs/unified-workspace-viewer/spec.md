# unified-workspace-viewer Specification

## Purpose

워크스페이스 멤버가 AI에게 질문하면서 그 근거가 되는 위키 문서·원시 소스·지식 그래프를 같은 화면에서 곧바로 확인할 수 있도록, 대화와 콘텐츠 열람을 하나의 통합 뷰로 제공한다.

## Requirements

### Requirement: Simultaneous conversation and content viewer
The system SHALL present the Ask conversation and a content viewer (wiki document, raw source, knowledge graph, or mind map) together in a single destination, without requiring navigation to a separate route to read either.

#### Scenario: Member opens the unified workspace viewer
- **WHEN** a workspace member navigates to the Ask destination
- **THEN** the member sees the conversation panel and the content viewer panel at the same time, within the same page

### Requirement: Content viewer tab switching

The system SHALL let a member switch the content viewer between four views — wiki document, raw source, 2D knowledge graph, and mind map — and SHALL reflect the active view and its target (e.g. wiki slug) in the URL so it is shareable and survives a page reload. The wiki document view exists to show the evidence behind an answer; it is not the only way to read a wiki page, and the standalone wiki reader route owns that job.

#### Scenario: Member switches to the raw source view
- **WHEN** a member selects the raw source tab for a wiki page that has backing sources
- **THEN** the viewer shows the raw sources that produced that wiki page, sourced from the wiki page's recorded source references

#### Scenario: Member switches to the mind map view
- **WHEN** a member selects the mind map tab for a wiki page
- **THEN** the viewer renders a layout centered on that page using the same link data the knowledge graph uses, without requiring a separate data fetch mechanism

#### Scenario: Reload preserves the active tab and target
- **WHEN** a member reloads the page while a specific tab and wiki page are active
- **THEN** the viewer restores the same tab and target from the URL

#### Scenario: Member opens the full reader from the viewer
- **WHEN** a member viewing a wiki page in the content viewer chooses to open the full document
- **THEN** the system takes them to the standalone wiki reader route for that page

### Requirement: Citation click integrates with the viewer
The system SHALL route a citation marker activation in the conversation to the content viewer's matching tab and target, instead of opening a separate overlay panel, and MUST terminate loading with an explicit unavailable state when the cited resource was deleted or is inaccessible.

#### Scenario: Member clicks a wiki citation marker
- **WHEN** a member activates a resolved citation marker pointing at an accessible wiki page
- **THEN** the content viewer switches to the wiki document tab showing that page, and the conversation remains visible

#### Scenario: Member clicks a source citation marker
- **WHEN** a member activates a resolved citation marker pointing at an accessible raw source chunk
- **THEN** the content viewer switches to the raw source tab showing that source

#### Scenario: Member clicks an unavailable wiki citation marker
- **WHEN** a member activates a resolved wiki citation marker whose page was deleted or is inaccessible
- **THEN** the content viewer switches to the wiki tab and displays an explicit unavailable state without indefinite loading

#### Scenario: Member clicks an unavailable source citation marker
- **WHEN** a member activates a resolved source citation marker whose chunk was deleted or is inaccessible
- **THEN** the content viewer switches to the raw source tab and displays an explicit unavailable state without indefinite loading
