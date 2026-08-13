## Context

GraphLensFilter and GraphCanvas are adjacent siblings. The canvas owns all data loading and node navigation.

## Decisions

- Wrap filters in a labelled soft-surface control region and give the canvas a bordered labelled region.
- Keep Cytoscape sizing and all fetch/node behavior unchanged.
