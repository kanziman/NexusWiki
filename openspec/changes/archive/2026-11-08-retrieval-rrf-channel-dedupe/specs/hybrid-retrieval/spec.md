## MODIFIED Requirements

### Requirement: Rank-based configurable fusion
The system SHALL fuse channel results by rank rather than comparing channel-specific raw scores, and SHALL keep per-channel weights, depth, candidate counts, output limits, and the same-channel aggregation rule in an explicit, versioned retrieval policy. Under the default policy, a piece of evidence that a channel returns more than once (for example several embedding chunks of one wiki page) MUST contribute to the fused score only once for that channel, at its best rank in that channel, so that evidence with many chunks does not outrank evidence with one chunk by repetition alone.

#### Scenario: Channels return incomparable score ranges
- **WHEN** semantic and lexical channels return results with different score scales
- **THEN** the fusion order depends on rank and configured channel weight rather than raw score magnitude

#### Scenario: Wiki page with several matching chunks in one channel
- **WHEN** the wiki-vector channel returns three embedding chunks of the same wiki page at ranks 1, 2, and 3
- **THEN** that page receives one wiki-vector contribution computed from rank 1, not the sum of three contributions

#### Scenario: Evidence found by different channels
- **WHEN** the same wiki page is returned by both the wiki-vector and wiki-lexical channels
- **THEN** it receives one contribution from each channel and its fused score is their sum

#### Scenario: Policy identifies the aggregation rule
- **WHEN** a retrieval result or benchmark record reports the policy that produced its ordering
- **THEN** the reported policy content includes the same-channel aggregation rule and its version differs from the policy that summed repeated contributions

