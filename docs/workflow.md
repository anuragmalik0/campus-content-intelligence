# Working Loop

The same cycle repeats for every phase. It exists so that work can stop and
resume across sessions without losing context, and so that no phase closes on
the strength of code that was never run.

```
   read state  ->  orient  ->  build  ->  prove  ->  review  ->  record
        ^                                                          |
        +----------------------------------------------------------+
```

## 1. Read state

Open `progress.md`. Find the active phase, what the last session finished, and
anything left blocked or unresolved. Open `decisions.md` and read the decisions
relevant to the current phase — they explain why the code looks the way it
does, and re-litigating a settled decision wastes a session.

Do not start from an assumption about where things stand. Read.

## 2. Orient

Look at the phase's exit criteria in `phases.md`. Look at the relevant contract
in `system-design.md`. Then look at the code that already exists.

Decide what actually needs doing to close the phase — which may be less, or
more, than the plan anticipated. Say what the plan is for this session before
writing code, so a human can redirect before effort is spent rather than after.

If the phase turns out to be larger than one session, that is normal. Do a
coherent piece of it, leave the tree in a runnable state, and record where it
stopped.

## 3. Build

Write the smallest thing that moves the phase toward its exit criteria, and run
it. Not "write the module then test the module" — write a piece, run it, look
at the output, then write the next piece. Code that has never been executed is
a draft.

Two habits that matter more than they sound:

**Look at intermediate data with your eyes.** Print the first three chunks.
Read them. A pipeline that runs without errors and produces subtly wrong data
is the default outcome, not the unusual one, and it is invisible from the exit
code.

**Spend credit deliberately.** Before any call that costs money, know roughly
what it will cost and whether a cheaper version of the same test would answer
the same question. Small clip first, full run once.

## 4. Prove

Work through `testing.md` for this phase. The point is not to produce a green
checkmark; it is to find out what is broken while there is still time to fix
it.

Actively try to break what was just built. Feed it the out-of-scope questions.
Feed it an empty file. Feed it a question whose answer sits exactly on a chunk
boundary. A test suite that only contains cases the code was written to handle
proves nothing.

If something fails, that is information, not a setback. Record it.

## 5. Review

Work through `security.md` for this phase. Every phase, not only the last one —
a secret committed in Phase 2 and discovered in Phase 6 is still in the git
history and is considerably harder to remove by then.

Also ask, plainly: could each of the five humans explain this code to an
examiner? If a piece is too clever to explain, it is the wrong piece regardless
of how well it works. Simplify it or write down the explanation.

## 6. Record

Update `progress.md`:
- what got done
- what was verified, and how
- what is broken or unresolved
- roughly what was spent
- what the next session should pick up

Add to `decisions.md` anything that was chosen between real alternatives, with
the reasoning and what was given up. The team has to defend these choices out
loud; "it seemed fine" is not a defence, and six days later nobody remembers
the actual reason.

Then either continue to the next phase or stop cleanly.

---

## Judgement calls

**When the plan is wrong.** These documents were written before the code
existed. When reality disagrees with them, reality is right. Say what the
document assumed, what turned out to be true, and what should change. Update
the document and log it. Do not quietly build something different from what is
written down — the humans are navigating by these files.

**When something is ambiguous.** Several decisions are deliberately left open
in `system-design.md` because they depend on data nobody has seen yet. Make a
reasoned choice, write down the reasoning, and flag it as revisitable. Do not
stall waiting for permission on a reversible decision.

**When something is irreversible or costly.** Spending a large share of the
remaining credit, restructuring the Chunk contract after other modules depend
on it, or deleting work — surface it first. Reversible decisions are made;
irreversible ones are proposed.

**When a phase cannot close.** Say so directly, with what is blocking it.
A phase marked complete that is not complete corrupts every estimate after it.

**On tools and approach.** Use whatever gets the job done well — libraries,
skills, connectors, whatever fits. The constraint is not on method; it is that
the result must be explainable by a second-year student and free of secrets.
