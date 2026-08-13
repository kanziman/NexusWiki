# graph-surface-separation Specification

## Purpose

워크스페이스 멤버가 그래프 필터를 조작하는 영역과 필터 결과를 탐색하는 캔버스 영역을 즉시 구분하도록 한다.

## Requirements

### Requirement: Separated graph controls and canvas
The system SHALL render graph category controls in a labelled control region that is visually separated from the graph canvas by spacing, boundary, or surface treatment. The canvas region SHALL retain a distinct accessible label.

#### Scenario: Member filters a graph
- **WHEN** a member opens the graph destination
- **THEN** the member can distinguish the category-control region from the graph canvas before interacting with either

#### Scenario: Keyboard member reaches the canvas
- **WHEN** a keyboard member moves from graph controls to graph content
- **THEN** the canvas region is exposed with an accessible label and the filters retain their existing accessible names
