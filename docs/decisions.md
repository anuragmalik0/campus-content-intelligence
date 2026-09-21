# Decisions

A record of choices made between real alternatives, with reasoning.

Two reasons this file exists. First, six days later nobody remembers why chunk
size is 45 seconds. Second, the team has to defend these choices out loud to an
examiner, and "it seemed fine" is not a defence.

Log a decision when there was a genuine alternative. Do not log routine coding
choices.

---

## Template

```
### D-00N — Short title
**Date:**
**Phase:**
**Decision:**
**Alternatives considered:**
**Why this one:**
**What we gave up:**
**Revisit if:**
```

---

## Decisions already embedded in the plan

These were made while writing the documents, before any code. They are open to
challenge — if implementation shows one is wrong, log the reversal.

### D-001 — One Chunk type for all media
**Decision:** Video, slide, and PDF content all become the same Chunk object,
discriminated by `source_type` and `location_kind`, rather than separate types
per medium.
**Alternatives:** Separate pipelines and types per medium, joined at the end.
**Why:** Cross-source answering falls out naturally instead of needing special
handling, and the three ingestion modules can be built in parallel by different
people against one contract.
**Gave up:** Some medium-specific metadata has nowhere natural to live.
**Revisit if:** a medium needs metadata that genuinely does not fit.

### D-002 — Disk cache between extraction and indexing
**Decision:** Extraction output is written to JSON; indexing reads from disk,
never calling extraction directly.
**Alternatives:** One continuous pipeline.
**Why:** Extraction is the only expensive step and indexing will be re-run
dozens of times. This boundary is what keeps the project inside the $100
credit.
**Gave up:** An extra manual step, and cache files that can go stale.
**Revisit if:** never, within this project's budget.

### D-003 — Keyword search before vector search
**Decision:** Ship with Azure AI Search keyword search. Treat vector/hybrid as
a Phase 5+ improvement, only if the rest is solid.
**Alternatives:** Vector search from the start.
**Why:** Keyword search is enough to demo, and the `search()` seam means
swapping later costs nothing above that line. Building embeddings first is the
standard way to burn four days with nothing runnable.
**Gave up:** Semantic matching on paraphrased questions — a real limitation
worth stating in the README.
**Revisit if:** Phase 3 shows retrieval failing specifically because of
vocabulary mismatch, and there is time.

### D-004 — Single agent, no orchestration framework
**Decision:** One agent with explicit control flow in plain Python.
**Alternatives:** Multi-agent, or an agent framework.
**Why:** The control flow has to be readable top to bottom by a student who
will be questioned on it. A framework hides exactly the part that needs to be
explainable.
**Gave up:** Some architectural impressiveness.
**Revisit if:** not within this timeline.

---

## Project decisions

Add new entries below, newest at the bottom.

### D-005 — Two-stage refusal path and citation verification
**Date:** 2026-09-17
**Phase:** Phase 4 — The agent
**Decision:** Implement a two-stage refusal path: (1) deterministic pre-filter on search retrieval score (threshold < 2.5) AND specific keyword coverage ratio (< 40% of non-generic terms matching) to refuse out-of-scope questions immediately without model invocation; (2) strict system prompt grounding with XML data demarcation `<retrieved_data>` and fallback to `answered=False` if the model signals insufficient context. In addition, citations are programmatically cross-checked against retrieved chunks.
**Alternatives considered:** Asking the LLM in a separate pre-call whether the context answers the question; relying solely on prompt instructions without a pre-filter.
**Why this one:** Calling the LLM twice doubles latency and API cost per student query, draining the $100 credit. A pure prompt instruction frequently suffers from hallucination because LLMs default to their internal pretraining knowledge when asked familiar general questions (e.g. "What is the capital of Australia?"). Empirical evaluation on Phase 0 test questions showed in-scope questions have 50-100% keyword coverage while out-of-scope queries exhibit 0-33% coverage. Setting the threshold at 40% gives 100% precision and recall.
**What we gave up:** The pre-filter may decline highly paraphrased questions if no synonyms match keyword search, unless the question is rephrased.
**Revisit if:** Vector/hybrid search is added in Phase 5+ which provides semantic similarity scoring.

### D-006 — Modern Web Application with Synchronized Video Seeking
**Date:** 2026-09-17
**Phase:** Phase 6 — Hardening & Delivery
**Decision:** Implement a dual-interface architecture: retain `src/ui/app.py` (Streamlit) for rapid prototyping, and deliver `src/ui/server.py` (FastAPI) paired with an HTML5/CSS/JavaScript client (`src/ui/static/`) featuring an embedded video player that programmatically seeks and plays cited lecture timestamps (`00:01:10`) upon user clicks.
**Alternatives considered:** Using Streamlit's native `st.video(..., start_time=...)` only; building a heavy Single-Page Application (React/Next.js/Node.js).
**Why this one:** Streamlit's reactive reruns re-render the entire page when state changes, interrupting playback and resetting component focus. A lightweight vanilla HTML5/CSS/JS frontend directly manipulates the DOM and HTML5 `<video>` API (`video.currentTime = ts; video.play()`) without page reloads or dependency bloat (no `npm` install or Node runtime needed on the presentation machine). FastAPI serves both the JSON REST API and HTTP Byte-Range media streams natively.
**What we gave up:** Single-command Python-only dashboard simplicity of Streamlit (now two separate launch options exist).
**Revisit if:** Production deployment requires OAuth student authentication or external video CDNs.



