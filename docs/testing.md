# Testing

The goal is to find out what is broken, not to produce evidence that nothing
is. A test suite built only from cases the code was written to handle tells you
nothing you did not already believe.

## The test set

`tests/questions.md`, written in Phase 0 before any pipeline exists — which
matters, because questions written after the fact tend to be questions the
system already answers.

Four categories, all needed:

**Single-source, straightforward.** Answerable from one place in the video or
one page of the PDF. These should always work; when they stop working,
something upstream broke.

**Cross-source.** Answerable only by combining the video and the slides or
notes. These are what the project claims to do and what the demo will show.
They are also the ones most sensitive to chunking and retrieval quality.

**Boundary cases.** A concept explained across a chunk boundary. A term that
appears in passing in three places. A question phrased with vocabulary the
lecturer never used. These find the real limits.

**Out of scope.** Questions the material does not answer, especially ones the
underlying model definitely knows from general knowledge. If the system answers
these, it is not grounded, and every other passing test is less meaningful than
it looks.

For each question, record the expected answer and where it comes from. Without
that, "did it work?" becomes a matter of opinion at 2am.

---

## What to check at each phase

**Ingestion.** Read the chunks. Are they coherent units of meaning or arbitrary
fragments? Is the location metadata right — open the video at a cited timestamp
and confirm the words match, open the PDF at a cited page and confirm the text
is there. Do this by hand for a few chunks; nothing automated substitutes for
it. Also: what happens with an empty file, a corrupt file, a PDF that is pure
scanned images?

**Retrieval.** For each test question, does the material containing the answer
appear in the top results? Track which questions fail — the failures are more
informative than the successes and will point at chunk size.

**Agent.** Correctness of answers against expected. Correctness of citations —
verify the cited location actually contains the claim, not merely that a
citation was produced. Refusals on out-of-scope questions. Behaviour on an
empty query, a very long query, a query in another language.

**Interface.** Someone outside the team uses it with no instructions. Watch
without helping. Where they hesitate is a design problem, and their first
question is usually the one the interface should have answered.

**End to end, clean machine.** Clone fresh, follow the README exactly, run it.
Every missing step surfaces here, and this is also what the examiner will do.

---

## Recording results

`tests/results.md`. Question, expected, actual, pass/fail, notes. Update it
when tests are run, not from memory afterwards.

This file feeds the README's "Testing and results" section directly, and is the
difference between telling an examiner "we tested it" and showing them.

**Write down the failures.** A results table with a few honest failures and a
sentence about why reads as a team that understands its own system. A perfect
table reads as a team that tested lightly, and the follow-up question will find
out which.

---

## Regression

Every phase after Phase 4, re-run the full set. Chunking changes break
retrieval. Prompt changes break refusals. These regressions are silent — the
code still runs, the answers are still fluent, they are just worse. Only
re-running catches it.
