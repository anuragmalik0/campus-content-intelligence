# About This Project

## The name

Smart Media Analysis Agent, built as a **Campus Content Intelligence Agent**.

## The problem

A student revising for an exam has the same topic scattered across three
formats: a recorded lecture video, a slide deck, and a PDF of notes. To answer
one question — "what did they actually say about gradient descent?" — the
student has to scrub a 50-minute video, flip through slides, and skim notes,
separately, with no way to search across them at once.

The gap is not summarisation. Plenty of tools summarise a video. The gap is
that the three sources are never queried together, so the student never gets
one answer that draws on all of them.

## What we are building

A system that ingests video, slides/images, and PDFs for a single course topic,
extracts their content into a common format, indexes it together, and answers
natural-language questions by retrieving across all three and synthesising one
grounded answer — with a citation pointing at the exact video timestamp or page
number the claim came from.

## Why citations are not optional

The citation is the product. An answer without a traceable source is a guess
with good grammar. A student cannot revise from something they cannot verify,
and the project is graded partly on transparency and human oversight. If a
tradeoff ever appears between a smoother answer and a verifiable one, take the
verifiable one.

## Who this is for

Students revising from mixed-format course material. Secondarily, the five team
members, who need to demonstrate it live and answer questions about how every
part works.

## Scope boundary

In scope:
- One topic's worth of content: roughly one video, one deck, one PDF
- Question answering over that content, with citations
- A simple chat interface

Out of scope, deliberately:
- Whole-course or whole-semester libraries
- User accounts, multi-tenancy, persistence beyond a session
- Anything requiring a GPU or self-hosted model
- Real-time / live lecture ingestion

Scope creep is the main risk to this project. The build window is short and
shared. When in doubt, cut.

## Definition of done

The system is done when a person who has never seen it can:
1. Ask a question in plain language about the indexed topic
2. Get an answer that is correct according to the source material
3. Click or read a citation and find the claim at that exact timestamp or page
4. Ask something the material does not cover, and be told so rather than
   receiving an invented answer

Point 4 matters as much as points 1-3. A system that confidently answers
questions outside its knowledge is worse than one that admits the gap.

## Constraints that shape everything

- **Build window is about ten days**, alongside classes.
- **The team shares one laptop.** Work that can be done in a browser (Azure
  portal, Colab, writing) should be structured so it does not compete for the
  laptop. Modules must be independently developable and testable.
- **Budget is a $100 student Azure credit shared across the team.** Reprocessing
  the same video repeatedly is the main way that credit disappears. Cache
  extraction output to disk and never re-extract during development.
- **Every team member must be able to explain the code they own.** Generated
  code that nobody understands is a liability at presentation time.
