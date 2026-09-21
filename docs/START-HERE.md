# START HERE

This folder describes a student project that is being built in phases. It is
written for an AI coding agent that will do the implementation work, and for
the five humans on the team who own the result.

## How to use this folder

Read these in order before doing anything:

| File | What it gives you |
|---|---|
| `about.md` | What the project is, who it is for, what "done" means |
| `architecture.md` | The intended shape of the system and why |
| `system-design.md` | Component-level detail: data contracts, interfaces |
| `phases.md` | The build broken into phases with exit criteria |
| `workflow.md` | The loop to follow for every phase |
| `security.md` | What to check before a phase is allowed to close |
| `testing.md` | How to prove a phase actually works |
| `conventions.md` | Code style, naming, repo hygiene |
| `progress.md` | Living state file — current phase, what's done, what's blocked |
| `decisions.md` | Running log of technical decisions and their reasoning |

`progress.md` and `decisions.md` are the two files that change constantly.
Everything else changes only when the plan itself changes.

## The one rule that matters most

These documents describe intent, not orders. If following a document literally
would produce a worse system, say so, explain the reasoning, and propose the
alternative. Write the disagreement into `decisions.md`. A plan written before
the code existed is a hypothesis, not a specification.

The humans on this team have to explain every line of this project to an
instructor who will ask follow-up questions. Anything clever enough that a
second-year student cannot explain it is the wrong choice, even if it is
technically better. Prefer boring and legible.

## What to do first

Open `progress.md`. It will tell you which phase is active and what state the
last session left things in. If it says Phase 0 has not started, start there.
