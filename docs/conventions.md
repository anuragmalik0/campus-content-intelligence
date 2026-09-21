# Conventions

The governing constraint: **five students must be able to explain every line to
an examiner who asks follow-up questions.** That rules out cleverness more than
any style guide would.

## Code

- Python, standard library and the pinned dependencies. No new dependency
  without a reason worth writing in `decisions.md`.
- Plain functions. No class hierarchy, no dependency injection, no framework
  unless it earns its place.
- Explicit over concise. A readable loop beats a dense comprehension that needs
  a moment's thought to parse.
- Type hints on anything that crosses a module boundary — they double as
  documentation of the Chunk contract.
- Comments explain *why*, not *what*. `# chunk ~45s of speech: shorter loses
  context, longer dilutes retrieval` is useful. `# loop through chunks` is
  noise.

## Modules

- One responsibility each, matching the layers in `architecture.md`.
- Each module runnable standalone under `if __name__ == "__main__":` for manual
  testing. This is what lets people work on separate pieces without the shared
  laptop and without the full pipeline existing.
- Modules communicate through the Chunk contract, never by reaching into each
  other's internals.

## Repository

- Commit small and often, with messages that say what changed and why.
- Check the diff before committing. Every time. This is the credential
  safeguard that actually works.
- Never commit: `.env`, media files, `venv/`, `__pycache__`, notebook outputs
  containing keys.
- The README is a deliverable, not an afterthought. It carries marks.

## Cost

- Cached extraction output is committed to disk and never regenerated without
  a reason.
- Small clip before full run, always.
- Note roughly what each expensive operation cost in `progress.md`. The team
  needs to know how much credit is left without guessing.

## Documentation as you go

Write the reasoning down while it is fresh. Six days later, nobody remembers
why chunk size ended up at 45 seconds, and the examiner will ask.
