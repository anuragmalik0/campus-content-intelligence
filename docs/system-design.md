# System Design

Component-level detail. `architecture.md` says what the shape is and why; this
file says what the pieces actually look like.

These contracts are the coordination mechanism for five people working
separately. Changing one is allowed, but it is a decision that affects other
people's code, so it goes in `decisions.md` and gets mentioned in `progress.md`.

---

## The Chunk contract

Every ingestion module emits a list of these. Every downstream component
consumes them.

```python
{
    "id":            str,    # stable, unique, derived not random (see below)
    "text":          str,    # the actual content
    "source_type":   str,    # "video" | "slide" | "pdf"
    "source_name":   str,    # human-readable, appears in the citation
    "location":      str,    # "00:12:04" for video, "7" for page/slide
    "location_kind": str,    # "timestamp" | "page"
}
```

Notes on the fields:

**`id` must be derived, not random.** Something like
`f"{source_name}-{location_kind}-{location}"`, slugified. If it is random, then
re-running indexing creates duplicate entries in the search index instead of
overwriting them, and search results fill up with copies of the same chunk.
This bites late and is confusing when it does.

**`location` is a string even when it is a page number.** One field, two
meanings, discriminated by `location_kind`. A schema with both an optional
`timestamp` and an optional `page_number` means every consumer writes the same
if/else, and eventually one of them gets it wrong.

**`source_name` is what a human reads in the citation.** Not a filename.
"Lecture 3 — Neural Networks", not "lec3_final_v2.mp4".

---

## Layer 1 — Ingestion

### `video_processor.py`

```python
def extract_video_content(video_path: str, source_name: str) -> list[Chunk]
```

Sends the video to Azure AI Content Understanding, receives a transcript with
timing, and groups it into chunks.

Design questions to work out during implementation:

- **Chunking strategy.** Transcript segments from the API are usually too short
  to be useful on their own — a single sentence rarely answers a question.
  Grouping into windows of roughly 30-60 seconds of speech tends to be about
  right, but verify against the actual output rather than trusting that number.
- **Overlap.** A concept explained across a chunk boundary is invisible to
  retrieval if chunks are disjoint. A small overlap between adjacent chunks
  is cheap insurance.
- **Which timestamp to cite.** The start of the chunk, so that a viewer jumping
  there hears the explanation begin rather than catching its tail.
- **Whether to use visual frame information at all.** If the lecture is a
  talking head, visual extraction adds cost and no value. If it is a
  screen-recorded slide walkthrough, it may be the most valuable signal in the
  video. Look at the actual demo video before deciding.

### `document_processor.py`

```python
def extract_pdf_content(pdf_path: str, source_name: str) -> list[Chunk]
def extract_slide_content(path: str, source_name: str) -> list[Chunk]
```

Two extraction paths, and the choice between them matters:

- **Plain text PDFs** — local extraction with PyPDF2 is free, instant, and
  offline. Use it wherever it works.
- **Slides, diagrams, scanned pages, anything where layout carries meaning** —
  local text extraction returns either nothing or a scrambled word soup. This
  is where Content Understanding earns its cost.

Try local extraction first and look at the output. If a page comes back empty
or garbled, that page needs the API. Deciding per-document rather than
globally saves real money.

A page of a PDF is often too large to be one chunk. Splitting on paragraph or
section boundaries, while keeping the page number attached to each piece, keeps
citations precise.

---

## Layer 2 — Indexing

### `search_index.py`

```python
def create_index() -> None
def upload_chunks(chunks: list[Chunk]) -> None
def search(query: str, top: int = 5) -> list[Chunk]
```

The index schema mirrors the Chunk contract. `text` is searchable;
`source_type` and `source_name` are filterable; the rest are retrievable
metadata.

`search()` is the seam between indexing and the agent. As long as it takes a
string and returns Chunks, the agent does not care what is behind it — keyword
search now, vector or hybrid search later, with no change above this line.
That is the point of putting the seam here.

Worth considering: whether `search()` should return a relevance score
alongside each chunk. The agent needs *some* signal to distinguish "found good
material" from "found nothing relevant but returned the top 5 anyway", and a
score is the most direct way to get it. Azure AI Search returns one; deciding
whether to expose it is an early decision with consequences for the refusal
path.

---

## Layer 3 — Agent

### `orchestrator.py`

```python
def answer_question(question: str) -> Answer
```

```python
Answer = {
    "text":       str,
    "citations":  list[Citation],   # what was actually used
    "answered":   bool,             # False when the system declined
    "reason":     str | None,       # why, when answered is False
}
```

The control flow, roughly:

1. Retrieve chunks for the question.
2. **Decide whether the retrieved material is good enough to answer from.**
3. If not: return `answered=False` with a reason. Do not call the model.
4. If yes: build a context block where every chunk carries a visible source
   label, prompt the model to answer only from that context and to cite, and
   return the result.

Step 2 is the part that requires judgement and is the part that most
implementations skip. Options worth weighing:

- A relevance-score threshold — simple, cheap, but the right threshold is
  data-dependent and has to be found by experiment.
- Asking the model itself whether the context answers the question, before
  asking it to answer — more robust, doubles the cost per query.
- Returning the answer but flagging low confidence — softer, but a flag users
  ignore is not a safeguard.

There is no obviously correct answer. Pick one, write down why in
`decisions.md`, and test it against questions that are deliberately outside the
source material.

**On prompt construction:** the model should receive chunks already labelled
with their sources, so that citing is easier than not citing. Instructing a
model to cite while handing it unlabelled text is asking it to invent the
labels, which it will do.

**On temperature:** low. This is a retrieval task, not a creative one.

---

## Layer 4 — Interface

### `app.py`

A chat interface. Question in, answer out, citations visible and readable.

Two things worth getting right:

- **Citations must be legible at a glance**, because the citation is the
  feature being demonstrated. "Lecture 3 @ 12:04" next to the claim, not a
  reference number the viewer has to chase.
- **The refusal case needs a real design.** When the system declines to answer,
  that should look like a deliberate, confident behaviour — not like an error
  or a crash. It is a feature and should read as one during the demo.

Build this against a mock `answer_question()` from day one so that UI work is
never blocked on the pipeline being finished.

---

## Configuration

All Azure endpoints and keys come from environment variables loaded from
`.env`, which is gitignored. `.env.example` documents the required names with
placeholder values.

No key, endpoint, or resource name appears in any committed file, in any
notebook output, in any screenshot, or in the demo video. See `security.md`.
