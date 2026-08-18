## Purpose

워크스페이스 멤버가 AI에게 질문하면서 그 근거가 되는 위키 문서·원시 소스·지식 그래프를 같은 화면에서 곧바로 확인할 수 있도록, 대화와 콘텐츠 열람을 하나의 통합 뷰로 제공한다.

## MODIFIED Requirements

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
