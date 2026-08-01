# Feature Research

**Domain:** Multi-tenant LLM-compiled "Living Wiki" SaaS — raw sources compiled into an interlinked wiki, answered over with hybrid retrieval and dual citation
**Researched:** 2026-08-01
**Confidence:** MEDIUM (cross-verified web sources + vendor primary docs; no hands-on product trials)

---

## Orientation: What Product Class Is This, Actually

Before the tables, one finding that reframes the competitive set.

**"Cairni" is not findable as a named product.** Web search resolves it to Cairn.info (a French scholarly portal) and codewithcairn.ai (a coding assistant). Neither matches. Treat the Cairni reference as either a private/pre-launch product or a misremembered name, and do **not** anchor requirements on it.

**The real named ancestor is Andrej Karpathy's "LLM Wiki" pattern (April 2026)**, and NexusWiki's schema maps onto it almost 1:1:

| LLM Wiki pattern | NexusWiki schema |
|---|---|
| `sources/` — immutable, LLM reads but never modifies | `raw_sources` (no UPDATE policy) |
| Entity pages with `[[wikilinks]]` | `wiki_pages` + `wiki_links` |
| `index.md` navigation | `wiki_pages.category` lenses |
| `log.md` — chronological record of ingests, queries, lint passes | **MISSING** — see Gap below |
| `AGENTS.md` — conventions the agent follows | `prompt_templates` |
| Workflows: ingest / query / **maintain** | ingest ✓ / query ✓ / **maintain: MISSING** |

Two structural gaps fall straight out of that mapping, and both are more important than anything on the current v1 list:

1. **There is no `maintain` workflow.** The pattern has three workflows; the draft has two. Maintain = de-duplicate pages, merge near-identical entities, update canonical pages instead of creating clutter, and lint. Without it, the wiki degrades monotonically as sources accumulate — which is precisely the failure mode "living wiki" is supposed to beat RAG on.
2. **There is no compile log.** `jobs` records job outcomes but nothing records *why a wiki page says what it says* across recompiles. This is the audit surface teams ask for the moment two people disagree with a page.

The other product-class landmarks worth naming: **DeepWiki** (Cognition/Devin) proves the "auto-generated wiki + Q&A over the wiki" shape works and that users want to *steer the page taxonomy* (`.devin/wiki.json` lets you specify exactly which pages get created). **NotebookLM** is the citation-UX benchmark. **Guru** is the only product with proven, load-bearing verification affordances. **Glean** sets the attribution bar. **Onyx/Danswer** shows what the enterprise floor looks like — and what the roadmap sink is.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| **PDF + URL + plain text ingest** | The three universal inputs. NotebookLM, Onyx, Notion all accept at minimum these. | MEDIUM | Already scoped (P2 ingest API). URL fetch needs a readability/boilerplate strip or the wiki compiles nav menus. |
| **Per-source ingestion status, not per-batch** | Standard status vocabulary across Bedrock KB / Azure AI Search / Dify: `IN_PROGRESS` / `INDEXED` / `PARTIALLY_INDEXED` / `FAILED`. Users need to know *which* file broke. | LOW | `jobs` gives this nearly free — members already have SELECT. The **`PARTIALLY_INDEXED` equivalent is the one to not skip**: a 200-page PDF where 3 chunks failed must not render as success. |
| **Retry and delete affordances in the UI** | The single most-cited ingestion UX complaint industry-wide is *no way to cancel, retry, or un-index from the UI*. Users end up in the DB. | LOW | `fail_job`/`dead` already models it. Needs a "Retry" button on `dead` jobs and a source-delete path. |
| **Visible dedupe, not silent dedupe** | Re-uploading the same file and seeing "nothing happened" reads as a bug, not as idempotence. | LOW | `content_hash` dedupe exists. UI must say **"Already ingested on {date} — skipped"** and link to the existing source. Silent success is the bug. |
| **Inline citation markers placed at the claim** | Perplexity/Bing/NotebookLM/Glean all do it. Citation UX research: readers spend more time hovering citations than re-reading paragraphs — it is the trust surface. | MEDIUM | Markers must sit **immediately after the clause they support**, not in a footer list. The `[[wiki:slug]]` / `[[src:chunk_id]]` anchors already enable this; the risk is the UI rendering them as a trailing "Sources" block, which throws the value away. |
| **Hover preview on a citation** | NotebookLM: hover previews the quoted text before you commit to navigating. Documented as the speed/thoroughness balance. | LOW | Popover with source title + exact snippet. Cheap; high perceived quality. |
| **Click-through that jumps to the exact passage** | NotebookLM scrolls the source to the cited passage. Its *absence* is the top complaint filed against open-webui and anything-llm — "undermines trust in RAG-based answers." | MEDIUM | See Differentiators — `char_start`/`char_end` makes the strong version of this cheap for you and expensive for competitors. |
| **Streaming answers** | Documented baseline output pattern. Non-streaming reads as broken at LLM latencies. | LOW | SSE from FastAPI. Note: citation anchors arrive mid-stream and must be resolved progressively, not only at the end. |
| **Honest empty state / refusal** | Notion Q&A's reputational damage comes from *invisible coverage gaps* — it silently ignores databases and embeds. Coverage gaps you can't see destroy trust faster than wrong answers. | LOW | If fusion returns nothing above threshold, say "no sources cover this" and offer to ingest. Never let the LLM free-run. |
| **WikiLink navigation between pages** | It is a wiki. Clicking `[[X]]` must go to X. | LOW | Already modeled. |
| **Workspace switcher + email invite + 3 roles** | Onyx stops at basic/curator/admin. Glean is permissions-aware. Three levels is the ceiling even at enterprise scale. | MEDIUM | owner/editor/viewer already exists in schema and RLS. Invite flow (token, email, accept) is the actual work. |
| **Answer language follows question language** | Korean + English corpus. Asking in Korean and getting English back is a hard failure for the primary user. | LOW | Prompt-template concern; make it explicit in the `ask` templates rather than hoping. |

---

### Differentiators (Competitive Advantage)

Features that set the product apart. Ordered by leverage-per-unit-effort.

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| **Dual citation card: compiled page + originating source chunk, side by side** | This is the Core Value and genuinely nobody in the studied set ships it. NotebookLM cites sources only. Guru cites cards only. Glean cites documents only. **Nobody shows you the synthesized claim and the raw evidence simultaneously.** | MEDIUM | The card must show, per claim: the wiki page (what we concluded) AND the source chunk (why). If the UI renders these as two separate lists, the differentiator evaporates — they must be *paired per claim*. |
| **Char-offset span highlight in the original document** | The #1 unmet citation need across the whole category. NotebookLM's own top complaint is "attributes a claim to Source 3 with a vague highlight" — no page/paragraph precision. | MEDIUM | **You already have `char_start`/`char_end` on `source_chunks` and the original file in Storage.** This is a schema advantage most competitors do not have. Render the source with the exact span highlighted. Highest trust-per-line-of-code in the entire roadmap. |
| **Per-claim attribution, not per-answer** | Glean's stated bar: a synthesized answer shows which claim came from the legal brief and which from the support playbook. | MEDIUM | Requires the compile/ask prompt to emit anchors inline and Pydantic validation to *reject answers with unanchored claims*. Enforce it in validation, not in the prompt hope. |
| **Verification status that feeds retrieval ranking** | Guru's proof point: verification is not a badge, it is a **ranking input**. Overdue cards get deprioritized or flagged in answers; verified cards get preferentially surfaced. This is why Guru's affordance is actually used and everyone else's rots. | MEDIUM | You have `verification_status`. **The decisive design choice is whether it enters RRF fusion.** If it is display-only, expect near-zero usage — this is the empirical lesson from every KB product that shipped a badge without a consequence. |
| **Named owner + expiry on verification** | Guru: verification is assigned to a named SME with a frequency (default 1 month, up to 10 years, or "does not expire"). Ownership + a date is what converts a badge into a workflow. | MEDIUM | Schema gap: `verification_status` has no `verified_by` / `verified_at` / `expires_at`. **A badge with no owner and no date is decoration.** Worth a migration. |
| **Typed conflict surfacing, not a boolean `disputed`** | Research finding (DRAGged into Conflicts, Google Research; ConflictRAG): explicitly telling the model the *conflict category* significantly improves response quality. Conflict subtypes are factual / temporal / opinion — and **temporal is the common real-world case, which is staleness, not disagreement.** | HIGH | A bare `disputed` boolean conflates "two teams disagree about policy" with "the 2024 doc is superseded by the 2026 doc." Users need the second handled automatically and only the first escalated to a human. Recommend at minimum a conflict *kind* alongside `disputed`. |
| **Red links as a ranked content backlog** | Genuinely differentiating and nearly free — `wiki_links.to_wiki_id IS NULL` already is the backlog. No competitor in the set ships "here is what your knowledge base is missing." | LOW | **Rank by inbound reference count.** A raw alphabetical list of 400 red links is noise; "12 pages reference `[[온보딩 절차]]` and it doesn't exist" is a product. Ranking is a `count(*) group by target_slug`. |
| **Per-page backlinks panel** | Consistently rated more useful than graph view because it is in-context and per-page. Answers "what depends on this?" before you edit or dispute it. | LOW | `wiki_links` reverse lookup. One query. Ship this instead of the canvas. |
| **The `maintain` workflow: dedupe / merge / lint** | The third Karpathy workflow, absent from the draft. It is what makes the wiki "living" rather than "accumulating." | HIGH | Detect near-duplicate slugs and near-identical embeddings; propose merges to a human. Also the natural home for staleness detection. Big, but it is the moat. |
| **Compile log / provenance history per page** | `log.md` in the pattern. When two teammates disagree with a page, "which sources produced this, in which compile, under which prompt version" is the only way to settle it. | MEDIUM | Especially valuable because prompt templates are swappable — a page can change because the *prompt* changed, not because the sources did. Record `prompt_template_id` + source set per compile. |
| **Follow-up chips derived from wiki_links (zero LLM cost)** | Follow-up chips are the higher-value chip pattern (2-4 max, must reference specifics from the answer, never generic). Perplexity's work because they cite facts from the answer. | LOW | **You can generate these for free**: take the cited pages, walk `wiki_links`, offer the top 2-4 neighbors as "관련 페이지" chips. No extra LLM call, no latency, and they are inherently specific. Cheap differentiator. |
| **Steerable compile scope / page outline** | DeepWiki's `.devin/wiki.json` lets a user specify exactly which pages get created. Users want to steer the taxonomy, not accept whatever the LLM decided. | MEDIUM | Partially covered by swappable `prompt_templates`, but a per-workspace "these are the categories/entities we care about" input is stronger and cheaper than prompt editing for non-technical users. |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Cytoscape graph canvas at v1** | Demos beautifully; every PKM tool has one; it is on the current v1 list. | Obsidian's graph view is the category's cautionary tale — widely described as **"graph theatre": visual richness substituting for analytic content, where dense link density looks like understanding.** Consensus is it adds little value on small/new corpora and hits a real ceiling past a few hundred nodes. A brand-new workspace's graph is 8 nodes; a mature one is unreadable. It is expensive (Cytoscape + React 19 + layout tuning + lens filters) and it is the feature most likely to eat a phase. | **Cut from v1.** Ship the per-page backlinks panel (LOW complexity, in-context, actually used) and the ranked red-link backlog. Revisit the canvas in v1.x *as a diagnostic* — orphan pages, dense clusters, missing bridges — which is the only framing where it earns keep. Glean has a knowledge graph and deliberately does **not** expose it as a user-facing canvas; it is a ranking input. |
| **Free-text editing of compiled wiki pages** | "It's a wiki, let me fix the typo." Feels obviously correct. | **Directly collides with `(workspace_id, slug)` upsert.** The next compile silently clobbers human edits. This is a merge-conflict problem, and solving it properly means page versioning, three-way merge, and edit-vs-regenerate arbitration — a phase you cannot afford. DeepWiki dodges it by being regenerate-only; Guru dodges it by being human-authored. You cannot be both. | **v1 wiki is read-only, by design.** Human input enters via (a) verification status transitions, (b) dispute flags, (c) prompt template editing, (d) adding a corrective source. Say this out loud in the UI — "pages are compiled, not written" — or users will assume it's broken. If editing is ever added, it needs a `human_edited` lock that compile respects. |
| **SaaS connectors (Slack / Drive / Confluence / Notion)** | Every enterprise buyer asks. Onyx has 40+, Glean has 100+. | This is *the* roadmap sink of the category. Each connector is auth + pagination + incremental sync + rate limits + **permission mirroring** — Onyx and Glean both mirror source-app ACLs, which for you would mean reconciling external permissions against RLS. That is a product, not a feature. On a Railway Hobby budget it is unaffordable. | Ship file/URL/text. If pulled, add exactly one connector after PMF, chosen by paying-customer demand, and mirror permissions or explicitly refuse to (state it). |
| **Chat threads / conversation history as a first-class object** | Every AI product has it; users expect chat memory. | Multi-turn state, thread storage, per-thread context windows, and share-a-thread all arrive together, and none of it advances dual citation. It also weakens the core thesis: the *wiki* is supposed to be the persistent memory, not the chat log. | Single-turn ask + follow-up chips (which carry context implicitly). If someone wants to keep an answer, the right move is "add this answer as a source" or "promote to a wiki page" — which strengthens the compounding loop instead of forking it. |
| **Numeric confidence scores displayed to users** | `confidence` is already in the schema; showing a number feels rigorous. | LLM self-reported confidence is uncalibrated and users learn to ignore it within a week. Guru's affordance works because it encodes **who verified it and when it expires** — a social fact, not a model output. A bare "confidence: medium" badge is noise that dilutes the verification badge next to it. | Surface `verification_status` (human, owned, dated) prominently. Keep `confidence` as an internal ranking input and a compile-time trigger for "flag for review," not a user-facing badge. Do not put two competing trust badges on one page. |
| **Public sharing / published knowledge base** | "We want customers to see this." NotebookLM Pro has chat-only sharing. | Requires anonymous access, which means an `anon` policy path — and `anon` currently has **no policies at all** (fully denied). Opening that is the single highest-risk change to the 38-case isolation guarantee. Also implies SEO, theming, custom domains. | Defer past v1 entirely. When it comes, model it as NotebookLM's **chat-only share** (assistant exposed, raw sources not) — it is the safer primitive and it protects the source corpus. |
| **Auto-recompile the whole wiki on every new source** | "Keep it always fresh" sounds like the whole point of "living." | Cost is linear in sources × pages, LLM spend is already flagged as the top budget risk (Key Decisions marks OpenRouter ⚠️ Revisit for exactly this), and it makes cost unpredictable per upload. | Incremental compile touching only affected slugs, plus an explicit manual "recompile workspace." Show estimated cost before a full recompile. This is what the per-workspace LLM budget cap is for. |
| **SSO / SAML / SCIM / audit log** | Enterprise checklist items. Onyx ships all of them. | Zero value for small teams, weeks of work, and they are trailing indicators of enterprise demand you do not have yet. | Supabase Auth email + magic link. Revisit only when a paying customer blocks on it. |
| **Per-page or per-category permissions** | "Sales shouldn't see the legal wiki." | Granular ACLs multiply the RLS policy surface you already verified at 38 cases, and every new policy is a chance to break isolation. | The workspace *is* the permission boundary. Two audiences = two workspaces. Cheap, already proven, zero new policy risk. |
| **Real-time collaborative editing / presence** | Notion-shaped expectations. | Requires CRDT or OT, websockets, and presence infra — and it is moot anyway because v1 pages are read-only compiled artifacts. | Nothing. Not applicable to a compiled wiki. |

---

## Feature Dependencies

```
[Storage bucket 0005]
    └──requires──> (nothing; but BLOCKS cloud db push)
            └──enables──> [Original document viewer]
                              └──requires──> [char_start/char_end span highlight]
                                                 └──requires──> [Dual citation card]

[Parser + chunking]
    └──produces──> [source_chunks + char offsets]
                        └──requires──> [Embedding pipeline]
                                            └──requires──> [5-way hybrid search]
                                                               └──requires──> [Citation anchors in context]
                                                                                  └──requires──> [Per-claim attribution]
                                                                                                     └──requires──> [Dual citation card]

[Wiki compiler] ──produces──> [wiki_pages]
                                   └──requires──> [WikiLink parse + link sync]
                                                      ├──enables──> [WikiLink navigation]
                                                      ├──enables──> [Backlinks panel]        (LOW)
                                                      ├──enables──> [Ranked red-link backlog] (LOW)
                                                      ├──enables──> [Follow-up chips]         (LOW)
                                                      └──enables──> [Graph canvas]            (HIGH — defer)

[verification_status] ──requires──> [verified_by / verified_at / expires_at]  ← SCHEMA GAP
                            └──must feed──> [RRF fusion ranking]
                                  (without this, the badge is decoration and goes unused)

[Conflict detection] ──requires──> [source_chunks embeddings]
                          └──requires──> [conflict KIND, not just disputed boolean]
                                └──feeds──> [Ask prompt: name the conflict category]

[maintain workflow] ──requires──> [wiki_embeddings] + [jobs]
                         └──conflicts with──> [Free-text page editing]

[Free-text page editing] ──CONFLICTS──> [(workspace_id, slug) upsert]
[Graph canvas]           ──COMPETES──> [Backlinks panel]  (same need, 10x the cost)
[confidence badge]       ──DILUTES──> [verification badge]
```

### Dependency Notes

- **Span highlight requires Storage (`0005`) to land first.** You cannot highlight `char_start..char_end` in a document you did not keep. `0005` is already flagged as must-land-before-cloud-push; this is a second, product-level reason it is critical path.
- **Dual citation requires per-claim anchors, which requires validation.** The existing anti-pattern note ("assembling LLM context without citation anchors → dual citation silently collapses to prose") is correct but incomplete: anchors in the *context* are necessary but not sufficient. The Pydantic layer must **reject answers whose claims carry no anchor**, or the collapse happens one layer later and just as silently.
- **Verification status must feed ranking or it will not be used.** This is the sharpest empirical finding in the research. Guru's verification is used because overdue content is demoted in AI answers. Every product that shipped a badge with no downstream consequence saw it rot. Decide this at design time, not after.
- **Backlinks panel competes with, and beats, the graph canvas.** Both answer "what connects to this?" One is a single reverse query on an existing table; the other is a Cytoscape integration, layout tuning, lens filters, and React 19 wrapper risk. They are not complementary at v1.
- **Free-text editing conflicts with the upsert key.** `(workspace_id, slug)` upsert is the idempotency guarantee that makes at-least-once jobs safe. Human edits and that guarantee cannot coexist without page versioning.
- **`confidence` dilutes `verification_status`.** Two trust badges on one page teach users to read neither. Pick one for the UI.

---

## MVP Definition

### Launch With (v1)

- [ ] **Storage bucket (`0005`)** — unblocks cloud push *and* the source viewer that dual citation depends on
- [ ] **PDF / URL / text ingest with visible dedupe** — "already ingested, skipped" not silence
- [ ] **Per-source job status + retry on dead** — the most-cited ingestion UX failure is missing remediation
- [ ] **Wiki compiler + WikiLink parse/sync** — the product thesis
- [ ] **5-way hybrid search + RRF** — already designed
- [ ] **Dual citation card with per-claim inline anchors** — Core Value; nothing ships without this
- [ ] **Jump-to-source with `char_start`/`char_end` span highlight** — the category's #1 unmet need and your cheapest structural advantage
- [ ] **Hover preview on citations** — LOW cost, disproportionate perceived quality
- [ ] **Streaming answers + honest empty state** — baseline, plus the Notion lesson
- [ ] **Read-only wiki viewer with WikiLink navigation + backlinks panel** — say "compiled, not written" in the UI
- [ ] **Ranked red-link backlog** — LOW cost, genuinely differentiating
- [ ] **Auth, workspace switcher, email invite, 3 roles** — team-first is already a locked decision
- [ ] **Korean/English answer-language matching** — primary-user hard failure otherwise
- [ ] **Per-workspace LLM cost cap** — already Active; budget is a stated constraint

### Add After Validation (v1.x)

- [ ] **`verified_by` / `verified_at` / `expires_at` + verification feeding RRF** — trigger: users start disagreeing with pages. Ship the full Guru-shaped workflow or don't ship the badge.
- [ ] **Typed conflict detection (factual / temporal / opinion)** — trigger: first workspace with genuinely contradictory sources. Handle temporal (= staleness) automatically; escalate only factual to humans.
- [ ] **Follow-up chips from `wiki_links`** — trigger: ask usage is real. Zero LLM cost; could arguably land in v1 if the wiki viewer lands early.
- [ ] **`maintain` workflow (dedupe / merge / lint)** — trigger: any workspace passes ~100 pages, or duplicate-slug complaints appear. This is the moat; do not defer past the first sign.
- [ ] **Compile log / per-page provenance history** — trigger: first "why does this page say that?" support question.
- [ ] **Steerable compile outline** — trigger: users complain the LLM chose the wrong page taxonomy.
- [ ] **Incremental recompile + cost preview** — trigger: LLM bill surprises anyone.

### Future Consideration (v2+)

- [ ] **Graph canvas, reframed as a diagnostic** — defer: "graph theatre" risk is real, cost is high, and backlinks cover the actual need. Only worth it if reframed around orphans/clusters/missing-bridges.
- [ ] **Chat-only public sharing** — defer: requires opening the `anon` path, the highest-risk change to verified isolation.
- [ ] **One SaaS connector** — defer: category roadmap sink; only on paying-customer demand, with an explicit permission-mirroring stance.
- [ ] **SSO / SAML / audit log** — defer: enterprise trailing indicator.
- [ ] **Free-text page editing with versioning + `human_edited` lock** — defer: only if read-only proves untenable, and only with the merge story solved first.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| Dual citation card (per-claim, paired) | HIGH | MEDIUM | **P1** |
| Span highlight via char offsets | HIGH | MEDIUM | **P1** |
| Storage bucket `0005` | HIGH | LOW | **P1** |
| Per-source status + retry | HIGH | LOW | **P1** |
| Visible dedupe messaging | MEDIUM | LOW | **P1** |
| Hover citation preview | HIGH | LOW | **P1** |
| Streaming + honest empty state | HIGH | LOW | **P1** |
| Read-only wiki viewer + WikiLink nav | HIGH | MEDIUM | **P1** |
| Backlinks panel | MEDIUM | LOW | **P1** |
| Ranked red-link backlog | MEDIUM | LOW | **P1** |
| Workspace switcher + invites + roles | HIGH | MEDIUM | **P1** |
| KO/EN answer-language matching | HIGH | LOW | **P1** |
| LLM cost cap | MEDIUM | LOW | **P1** |
| Follow-up chips from `wiki_links` | MEDIUM | LOW | **P2** |
| Verification: owner + expiry + ranking | HIGH | MEDIUM | **P2** |
| Typed conflict detection | MEDIUM | HIGH | **P2** |
| `maintain` workflow (dedupe/merge) | HIGH | HIGH | **P2** |
| Compile log / provenance history | MEDIUM | MEDIUM | **P2** |
| Incremental recompile + cost preview | MEDIUM | MEDIUM | **P2** |
| Steerable compile outline | MEDIUM | MEDIUM | **P2** |
| Graph canvas | LOW | HIGH | **P3** |
| Chat-only public sharing | LOW | HIGH | **P3** |
| SaaS connectors | LOW (now) | HIGH | **P3** |
| Free-text page editing | LOW | HIGH | **P3** |
| Numeric confidence badge | NEGATIVE | LOW | **Do not build** |

**Priority key:** P1 = must have for launch · P2 = should have, add when possible · P3 = future consideration

---

## Competitor Feature Analysis

| Feature | NotebookLM | Guru | Glean / Onyx | Obsidian | **NexusWiki approach** |
|---|---|---|---|---|---|
| **Compiled wiki layer** | No — RAG over raw sources | No — human-authored cards | No — search over raw docs | Human-authored | **Yes — LLM-compiled `wiki_pages` (the thesis)** |
| **Citation granularity** | Source-level; "vague highlight" on long PDFs is its top complaint | Card-level | Glean: per-claim, document-level | N/A | **Chunk-level with `char_start`/`char_end` span highlight — finer than any of them** |
| **Dual (source + synthesis) citation** | Source only | Card only | Document only | N/A | **Both, paired per claim — the differentiator** |
| **Hover preview / jump to passage** | Yes, both | No | Yes (document) | N/A | **Yes, both, plus exact-span highlight** |
| **Verification affordance** | None | **3 states, named SME owner, expiry, feeds AI ranking** | None (freshness is implicit) | None | Adopt Guru's shape: `verification_status` + add owner/expiry, **and wire it into RRF** |
| **Contradiction handling** | None | Human re-verification | None | None | Typed conflict (`disputed` + kind); temporal auto-resolved, factual escalated |
| **Red links / gap backlog** | None | None | None | Yes (unresolved links) but unranked | **Ranked by inbound reference count — no competitor ships this** |
| **Backlinks** | None | None | None | **Yes — its most-praised nav feature** | Yes, per-page panel |
| **Graph canvas** | None | None | Graph exists but is a **ranking input, not a UI** | Yes — "graph theatre" criticism | **Cut from v1**; revisit as a diagnostic |
| **Multi-tenant isolation** | Notebook-scoped, Chat-only share | Workspace + groups | Source-ACL mirroring | Local files | **Postgres RLS, 38/38 verified — stronger floor than app-layer checks** |
| **Roles** | Owner / viewer | Multiple | basic / curator / admin | N/A | owner / editor / viewer — matches the category ceiling |
| **Connectors** | Upload + Drive | Many | 40–100+ | N/A | **File / URL / text only — deliberate** |
| **Page editing** | N/A | Human-authored | N/A | Full editing | **Read-only compiled artifact — deliberate** |

---

## Confidence and Gaps

**MEDIUM overall.** Findings are cross-verified across multiple independent sources and include vendor primary documentation (Guru's own verification docs, Glean's product pages, Cognition's DeepWiki docs) plus peer-reviewed conflict-detection work (Google Research / arXiv). No product was trialed hands-on, and no NexusWiki user research exists.

Per-area:

| Area | Confidence | Reason |
|---|---|---|
| Citation UX | MEDIUM–HIGH | Convergent across NotebookLM behavior, published AI-UX pattern libraries, and concrete GitHub feature requests naming the exact gap |
| Verification affordances | MEDIUM–HIGH | Guru primary docs are explicit that verification feeds AI ranking — this is the strongest single finding |
| Graph canvas skepticism | MEDIUM | Multiple independent critiques converge on "graph theatre"; opinion-heavy but consistent, and corroborated by Glean keeping its graph non-user-facing |
| Ingestion UX | MEDIUM | Status vocabulary is consistent across four independent vendor docs; the remediation-affordance complaint is well-documented |
| Conflict handling | MEDIUM | Strong academic grounding, but **no shipping product in the studied set actually exposes contradiction to users** — so this is unvalidated as a *product* feature, only as a technique |
| Team/multi-tenant v1 needs | LOW–MEDIUM | Generic SaaS sources; the useful signal is negative (three roles is the ceiling even at enterprise scale) |
| "Cairni" as reference product | LOW | **Not findable.** Do not build requirements against it. |

**Open gaps for later phase-specific research:**

1. **Does anyone successfully surface contradictions to end users?** Academic work is strong; product evidence is absent. Before spending a phase on conflict UX, find one shipping example or accept it as an unvalidated bet.
2. **Korean-language chunking and bigram retrieval quality** — no sources found on Korean-specific chunking parameters. This maps to the existing open question on chunking parameters and needs empirical tuning, not literature.
3. **Whether read-only wiki pages are acceptable to users.** This is the biggest untested product assumption in the v1 scope. Worth putting in front of a real user before P3 UI work locks it in.
4. **Cost per compiled workspace** — no comparable public data on LLM spend for compile-first architectures. The per-workspace cap will have to be set empirically.

## Sources

**Products and primary vendor docs**
- Guru — verification workflow, states, SME ownership, expiry, AI ranking impact: getguru.com/features/verification, help.getguru.com/docs/what-is-verifcation, help.getguru.com/docs/verifying-and-unverifying-cards
- Glean — per-claim attribution, enterprise graph, connectors, permissions: glean.com/perspectives/top-ai-assistants-for-accurate-source-citations, glean.com/blog/knowledge-graph-agentic-engine, glean.com/press/glean-introduces-third-generation-ai-assistant-new-enterprise-graph
- DeepWiki (Cognition/Devin) — auto-generated wiki, `.devin/wiki.json` steering, Q&A: docs.devin.ai/work-with-devin/deepwiki, github.com/CognitionAI/deepwiki
- Onyx / Danswer — connectors, ACL mirroring, roles, inline citations: docs.openwebui.com/alternatives/onyx, github.com/unoplat/danswer
- NotebookLM — citations, hover/jump, chat-only sharing, limits and complaints: xda-developers.com/notebooklm-limitations, atlasworkspace.ai/blog/notebooklm-limitations, joesabado.substack.com/p/notebooklm-versions-explained-free
- Notion AI Q&A — citation to blocks, database/embed blind spots: eesel.ai/blog/notion-ai-qa-in-knowledge-hub, aiunpacker.com/blog/notion-qa-feature-2025

**Pattern and category references**
- Karpathy LLM Wiki pattern (three layers, ingest/query/maintain): aaif.io/blog/karpathys-llm-wiki-as-agent-memory, datasciencedojo.com/blog/llm-wiki-tutorial, levelup.gitconnected.com "Beyond RAG"
- LLM wiki implementations: github.com/vbarsoum1/llm-wiki-compiler, muhammadraza.me "Building CodeWiki"
- Citation UX patterns: shapeof.ai/patterns/citations, shifthq.ai/blog/creating-rich-citation-experiences-with-llms, 7wdata.be "Citations as the User-Visible Proof of Grounding"
- Missing deep-link/highlight as filed complaints: open-webui discussions #20829 and #3326, Mintplex-Labs/anything-llm issue #2064
- Ask/chip/streaming patterns: aiuxplayground.com/pattern/follow-up-chips, aiuxplayground.com/pattern/streaming, shapeof.ai/patterns/follow-up
- Graph view criticism: knodegraph.com/blog/obsidian-graph-view-alternative, affine.pro/blog/obsidian-alternative, forum.obsidian.md/t/personal-knowledge-graphs/69264
- Ingestion status/UX: AWS Bedrock KB docs and re:Post threads, Azure AI Search indexer errors doc, Crosstalk-Solutions/project-nomad issue #883 (Knowledge Base Ingestion UX Redesign), langgenius/dify issue #8996
- Knowledge conflict: arXiv 2506.08500 (DRAGged into Conflicts, Google Research), arXiv 2605.17301 (ConflictRAG), arXiv 2504.00180 (Contradiction Detection in RAG)

---
*Feature research for: multi-tenant LLM-compiled living wiki with dual citation*
*Researched: 2026-08-01*
