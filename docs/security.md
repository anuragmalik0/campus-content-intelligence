# Security Review

Run at the end of every phase, not only at the end of the project. The most
common serious failure in a student project is a credential committed early and
discovered late, when it is already permanent in the git history.

This is also graded. "Testing, reliability and responsible AI" is 15% of the
mark, and the project brief is explicit that credentials must never reach the
repository.

---

## Every phase — credential hygiene

**Nothing secret in the repo, ever.**

- Keys, endpoints, connection strings, resource names, and account identifiers
  live in `.env`. `.env` is gitignored. `.env.example` carries placeholders
  only.
- Before committing, actually look at the diff. Not `git commit -am` from
  muscle memory.
- Search the working tree for anything resembling a key — long base64-ish
  strings, `api_key=`, `sk-`, `.cognitiveservices.azure.com`, `.search.windows.net`.
- **Search the git history too, not just the current files.** A file deleted in
  a later commit is still fully present in the history and still fully
  exploitable.
- Check notebook outputs. Colab and Jupyter cells cheerfully serialise printed
  keys into the `.ipynb` file, which then gets committed, and nobody scrolls
  that far down when reviewing.
- Check log output and error messages. Exception text that includes the request
  URL often includes the key as a query parameter.

**If a key is ever exposed: rotate it in the Azure portal first, then clean the
repo.** In that order. Removing it from the repo while the live key remains
valid fixes nothing. Log the incident in `progress.md` — this is exactly the
kind of thing an examiner respects being told about honestly.

**Before anything is made public or shown:** the same check applies to the
README, screenshots, the recorded demo video, and any slide. A key visible for
two frames in a screen recording is a key that is published. Blur or re-record.

---

## Phase 1-2 — Ingestion

- **Path handling.** If a file path ever comes from user input rather than
  being hardcoded, `../../etc/passwd` and friends become relevant. Validate
  that resolved paths stay inside the intended directory.
- **File type validation.** Do not infer type from extension alone if the file
  came from outside the team.
- **Source material licensing.** If the demo video is somebody else's lecture,
  do not commit the media file to a public repo. Keep `data/sample_media/`
  gitignored and describe the content in the README instead.
- **Personal data.** A recorded lecture may contain students' names, voices, or
  faces, and a PDF may carry author metadata. Consider whether that belongs in
  a public repository. If in doubt, use material you own or that is openly
  licensed.

---

## Phase 3 — Index

- The search service is a network endpoint with a key. Treat the key exactly
  like any other credential.
- Use a query key rather than an admin key wherever only reading is needed.
  Least privilege is easy here and worth the two minutes.
- Note in the README that the free tier index is not a secure store — nothing
  sensitive should be indexed in the first place.

---

## Phase 4 — Agent (the interesting one)

This is where an LLM-backed system has failure modes that a normal application
does not.

**Prompt injection.** The retrieved chunks are untrusted input that gets placed
directly into a model prompt. If a source document contains text along the
lines of "ignore previous instructions and...", the model may follow it.

This is not hypothetical for this project — a PDF or a slide deck can contain
arbitrary text, and lecture material is not curated for this.

Worth doing:
- Structure the prompt so retrieved content is clearly demarcated as data, not
  as instruction.
- Test it: put a line of injected instruction into a test document, index it,
  and see what the system does. Whatever the outcome, write it in the README's
  limitations section. Demonstrating awareness of this is worth more marks than
  pretending it cannot happen.

**Output grounding.** Verify that citations refer to chunks that were actually
retrieved, rather than plausible-looking references the model produced. Cross-
check the cited locations against the retrieved chunk list programmatically if
possible. A fabricated citation is worse than none.

**Refusal path.** Confirm the system declines rather than answering from the
model's general world knowledge. Ask it something the material does not cover
but the model certainly knows — if it answers, grounding has failed regardless
of what the prompt says.

**Cost as an attack surface.** An unbounded input field connected to a paid API
can drain the credit. Cap input length. Consider a simple per-session request
limit before the demo, when strangers will be typing into it.

---

## Phase 5-6 — Interface and delivery

- Do not render model output as raw HTML. If the UI interprets markup, injected
  content in a source document becomes injected markup in the page.
- Error messages shown to users should not include stack traces, endpoints, or
  request URLs.
- If the app is exposed on a network for the demo, know what else that exposes.
  Localhost is sufficient for a classroom demo.
- Final check on a clean clone: does the repo contain any secret, any private
  media, any personal data? Check the history, not just the tree.

---

## What to write in the README

Not a claim that the system is secure. A short, honest section covering:
- how credentials are handled
- what prompt injection is, that it was tested, and what was found
- what the system refuses to do and why that is deliberate
- what a production version would need that this does not have

Honest limitations read as competence. Overclaiming reads as not having
checked, and invites exactly the question the team cannot answer.
