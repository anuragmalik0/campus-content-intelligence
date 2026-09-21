# Build Phases

Seven phases. Each one ends with something that runs and can be shown to a
person. No phase ends with "the code is written but untested."

The ordering is deliberate: the riskiest and most expensive thing (video
extraction) happens early, because discovering it does not work on day eight is
fatal and discovering it on day two is a Tuesday.

A phase is not complete until its exit criteria are met, `testing.md` has been
worked through for it, and `security.md` has been worked through for it.

---

## Phase 0 — Ground truth

Before any pipeline code exists.

- Choose the actual demo media: one video, one deck, one PDF, all on the same
  topic. Put them in `data/sample_media/`.
- Watch the video. Read the slides. This is not a formality — chunking
  decisions, whether visual extraction is worth paying for, and what a good
  answer even looks like all depend on knowing what is in the material.
- Write 15-20 test questions in `tests/questions.md`, with the answer you
  expect and where in the material it comes from. Include:
  - questions answerable from the video alone
  - questions answerable from the slides or PDF alone
  - **questions that need two sources combined** — these are the demo
  - **questions the material does not answer** — these test the refusal path
- Confirm Azure resources exist and credentials load from `.env`.

**Exit criteria:** media in place, test questions written with expected
answers, a trivial script successfully authenticates against each Azure service.

This phase produces no features and is the one most likely to be skipped. It is
also the one that determines whether the rest of the project is testable.

---

## Phase 1 — Document ingestion

Start with PDFs, not video. They are free, fast, local, and they let the Chunk
contract get exercised before spending any credit.

- Implement `extract_pdf_content`.
- Look at the output with your eyes. Are the chunks coherent? Is the page
  number right? Would this text, alone, answer one of the test questions?
- Write the JSON cache.

**Exit criteria:** running the script on the demo PDF produces valid Chunks on
disk whose page numbers are verifiably correct.

---

## Phase 2 — Video ingestion

The expensive one. Treat the credit as a finite resource being spent.

- Test on a 2-3 minute clip first. Never the full video until the clip works
  end to end.
- Implement `extract_video_content` with chunking and timestamps.
- **Verify timestamps by hand.** Take three chunks, open the video at the cited
  time, confirm the words match. A citation that points at the wrong moment is
  the worst failure this project can have, and it is invisible unless checked
  deliberately.
- Run on the full video once. Cache it. Do not run it again.

**Exit criteria:** full video extracted to disk, timestamps spot-checked
against the actual video, cost recorded in `progress.md`.

---

## Phase 3 — Index and retrieval

- Create the index, upload the cached chunks from Phases 1 and 2.
- Query it directly from a script, no agent involved.
- Take the Phase 0 test questions and check: does search return chunks that
  *contain* the answer? If retrieval cannot find it, no amount of prompting
  downstream will fix it.

This is the phase where chunking mistakes surface. Expect to go back and adjust
chunk size, and expect that to be normal rather than a sign something went
wrong.

**Exit criteria:** for most test questions, the correct source material appears
in the top 5 results. Known failures written down.

---

## Phase 4 — The agent

Now the retrieval seam is proven, build on top of it.

- Implement `answer_question`, including the refusal branch.
- Run every Phase 0 test question through it.
- Check citations point at real, correct locations — not plausible ones.
- Check the out-of-scope questions actually get refused rather than answered
  from the model's general knowledge. This is the single most important test in
  the project.

**Exit criteria:** correct, cited answers for in-scope questions; clean
refusals for out-of-scope ones; results recorded in `tests/results.md`.

---

## Phase 5 — Interface

- Wire the real agent into the UI that was built against a mock.
- Make citations prominent and readable.
- Make the refusal state look intentional.
- Have someone outside the team use it without instructions and watch where
  they get confused.

**Exit criteria:** a person who has never seen the project can ask a question
and understand the answer and its sources without help.

---

## Phase 6 — Hardening and delivery

- Full pass through `security.md`, including git history, not just the current
  files.
- Re-run the whole test suite from a clean checkout on a different machine.
  "Works on the laptop it was built on" is not working.
- Finish the README: architecture, setup, testing and results, limitations,
  acknowledgements.
- Record demo material.

**Exit criteria:** a stranger can clone the repo, follow the README, and run
it. No secret has ever been committed. Limitations are written down honestly.

---

## If time runs out

Cut from the bottom. In order of what to sacrifice first:

1. Visual/frame extraction from video — transcript alone carries most of the value
2. Slide image OCR — if the deck exists as a text PDF, use that instead
3. UI polish — a plain interface with correct answers beats a pretty one with wrong ones
4. Vector or hybrid search — keyword search demos fine

Never cut: the refusal path, citation correctness, or the security pass. Those
are the parts that distinguish this from a weekend chatbot.
