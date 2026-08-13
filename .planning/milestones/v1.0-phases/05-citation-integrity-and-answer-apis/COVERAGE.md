# API Coverage — OpenRouter Chat Completions (streaming)

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
>
> Detector fired (`api-coverage.verify-pre`) on Phase 5 scope. The specific matched signal was a false-positive substring match on "API-01" (a requirement ID, not an API-integration term), but Phase 5 does genuinely add new OpenRouter API surface — `apps/worker/src/worker/llm.py` currently only calls the non-streaming chat completions shape (`complete_structured()`, Phase 3); Phase 5 adds the first **streaming** call against the same OpenRouter `/chat/completions` endpoint (`stream: true`). This matrix decides that new surface's capability coverage rather than declaring the detection a pure false positive.

| capability | decision | reason |
|---|---|---|
| Streaming completions (`stream: true`, SSE delta chunks) | INTEGRATE | Required by API-01 (SSE `meta`→`delta*`→`citations`→`done`) — the entire point of this phase's LLM call |
| System prompt / message-array input | INTEGRATE | Required for prompt-template injection (API-02) and anchor-issuance instructions (D-02/D-10) |
| Non-streaming completions | OPT-OUT | not needed — Ask is always a streaming UX (API-01); `worker.llm.complete_structured()` already covers non-streaming for compile (Phase 3), reused as-is, not duplicated |
| Tool / function calling | OPT-OUT | explicitly out of scope — Ask is single-turn Q&A over retrieved evidence, not an agentic/tool-use flow; no requirement in CITE-*/API-* calls for it |
| Vision / multimodal input | OPT-OUT | not needed — sources are text-extracted (PDF/URL/text per Phase 3 ING-*); no image-input requirement anywhere in REQUIREMENTS.md |
| Native `response_format` / structured JSON output | OPT-OUT | explicitly rejected project-wide — `.claude/CLAUDE.md` constraint: OpenRouter routing forfeits Anthropic-native `output_config.format`; this project's structured-output backstop is prompt + Pydantic + 3 retries (`checklists.json > decisions.structured_output`), and Ask's output is free-text-with-anchors, not schema-validated JSON, so this capability doesn't apply to this call shape at all |
| Model fallback / multi-model routing (`provider.order`, `allow_fallbacks`) | OPT-OUT | not needed yet — the project pins a single model via `LLM_MODEL` env (`checklists.json > decisions.llm`) for reproducibility; the embedding boundary (`03-CONTEXT.md > D-05`) made the identical choice for the identical reason (mixed providers/hosts silently corrupt version-tracking metadata) |
| `logprobs` / `seed` (determinism/debugging params) | OPT-OUT | not needed — no requirement calls for reproducible sampling or token-probability introspection |
| Prompt caching (Anthropic-native or OpenRouter equivalent) | OPT-OUT | unavailable via OpenRouter routing per `.claude/CLAUDE.md`'s explicit constraint (native caching is forfeited by the OpenRouter choice); out of this phase's control, not a phase-level decision to revisit |
| Usage/cost accounting from response (`usage` field) | INTEGRATE | required to write `usage_events` for the budget-cap check this phase adds (D-09 addendum, OPS-01 gap the researcher found) — the same accounting Phase 3's compile path already does for non-streaming calls |
| Stop sequences (`stop` param) | OPT-OUT | not needed — the answer's natural end is the provider's own completion signal; no requirement calls for early-truncation control |

**A second integration against the same need:** none in this phase — this is the first (and only) streaming chat-completions integration; Phase 3's non-streaming `complete_structured()` is a distinct, already-decided capability (COMP-01/COMP-03), not re-decided here.
