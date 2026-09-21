# Architecture

## Shape

Four layers, one direction of flow. Each layer depends only on the one above it
through a documented data contract, never on its internals.

```
  video.mp4        slides.pdf / .png        notes.pdf
      |                    |                    |
      v                    v                    v
 +---------------------------------------------------+
 |  LAYER 1 — INGESTION                              |
 |  Turns any input format into Chunks               |
 |  video_processor.py    document_processor.py      |
 +---------------------------------------------------+
      |
      |  Chunk[]  (written to disk as JSON — the cache boundary)
      v
 +---------------------------------------------------+
 |  LAYER 2 — INDEXING                               |
 |  Loads Chunks into a searchable store             |
 |  search_index.py                                  |
 +---------------------------------------------------+
      |
      |  search(query) -> Chunk[]
      v
 +---------------------------------------------------+
 |  LAYER 3 — AGENT                                  |
 |  Retrieves, decides, synthesises, cites           |
 |  orchestrator.py                                  |
 +---------------------------------------------------+
      |
      |  Answer { text, citations[], confidence }
      v
 +---------------------------------------------------+
 |  LAYER 4 — INTERFACE                              |
 |  app.py                                           |
 +---------------------------------------------------+
```

## The Chunk is the spine of the system

Everything upstream converts *into* a Chunk. Everything downstream consumes a
Chunk. If the Chunk contract is right, the layers can be built in parallel by
different people on different machines, which is the only way five people
sharing one laptop can work at once.

A Chunk is a piece of source material small enough to be a useful search hit
and large enough to make sense on its own, carrying enough metadata to cite
itself. See `system-design.md` for the exact fields.

The consequence worth understanding: **a video chunk and a PDF chunk are the
same type of object.** The system does not have a "video pipeline" and a
"document pipeline" that meet at the end. It has one pipeline with two
entrances. This is what makes cross-source answering fall out naturally rather
than needing special handling.

## The disk cache between Layer 1 and Layer 2

Extraction is the expensive step — in money, in wall-clock time, and in API
quota. Indexing and querying are cheap and will be run hundreds of times during
development.

So extraction output is written to disk as JSON and Layer 2 reads from disk,
never from Layer 1 directly. Once a video has been extracted, it is never
extracted again. This single boundary is what keeps the project inside its
budget, and it is not optional.

## Layer 3 is where the actual thinking happens

Layers 1, 2, and 4 are plumbing. They can be built by following documentation.
Layer 3 is the part where design choices have real consequences:

- **How many chunks to retrieve** — too few and the answer misses context, too
  many and the model drowns and starts padding.
- **What to do when retrieval comes back weak** — this is the refusal path.
  It has to be an explicit branch in the code, not a hope that the prompt will
  handle it.
- **How to force citations** — the model must be given chunks that are already
  labelled with their source, so citing is the path of least resistance rather
  than an instruction it may drift away from.
- **How to combine sources** — when the video and the slides both cover a
  topic, the answer should read as one answer, not two pasted together.

Spend design effort here. Spend as little as possible elsewhere.

## What is deliberately not in this architecture

- **No vector embeddings in the first working version.** Keyword search gets a
  demo working. Vectors are a Phase 5 improvement, added only if the plain
  version is already solid and there is time left. Adding them early is the
  classic way to spend four days and have nothing to show.
- **No database.** JSON on disk plus a managed search index is enough. A
  database is another thing to configure, secure, and explain.
- **No authentication.** Out of scope, and a login screen adds zero marks.
- **No agent framework or multi-agent orchestration.** One agent, one clear
  control flow that a student can read top to bottom and explain.

## Where this could go wrong

Failure modes worth designing against, in rough order of likelihood:

1. **Extraction produces garbage and nobody notices** until the answers are
   bad, at which point it looks like a model problem. Inspect extraction output
   by eye before building anything on top of it.
2. **Chunks are the wrong size.** Too small and each one lacks the context to
   be meaningful; too large and retrieval returns mostly irrelevant text and
   the citation points at a whole page rather than a claim.
3. **Timestamps drift** and citations point at the wrong moment, which is worse
   than no citation because it is confidently wrong.
4. **The credit runs out** in week one from repeated re-extraction.
5. **Everything integrates on the last day** and nothing works. The phase
   structure exists specifically to prevent this — every phase ends with
   something runnable.
