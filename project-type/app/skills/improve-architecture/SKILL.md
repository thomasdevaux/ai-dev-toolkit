---
name: improve-architecture
description: Find where this codebase's structure costs the most — shallow modules, interfaces as complex as what they hide, seams in the wrong place — report the candidates as a self-contained HTML page, then interrogate the one that gets picked before any code moves. Use when asked to improve the architecture, reduce structural friction, or judge whether a refactor is worth its price.
when_to_use: Use on a project that has adopted project-type-app, when asked to "improve the architecture", "this is getting hard to change", "should we refactor X", or before a large feature lands in an area that already resists change.
disable-model-invocation: true
---

# Improve architecture

Two phases, and **the first one produces no code**. Report candidates, wait
for a pick, interrogate it, then act. A refactor proposed and started in the
same breath is how a session ends with a half-migrated codebase.

The goal is **depth**: substantial behaviour behind a small interface. Not
fewer files, not more layers.

## Vocabulary

Use these words, and no synonyms. "Component", "service", "helper", "clean"
and "decouple" carry no information here — they let a vague proposal pass for
a concrete one.

| Term | Meaning |
| --- | --- |
| **module** | Anything with an interface and an implementation — a function, a class, a package, a slice spanning tiers. Scale-agnostic on purpose. |
| **interface** | Everything a caller must know to use it correctly: the signature, but also invariants, ordering constraints, error modes, required configuration, performance characteristics. |
| **depth** | How much behaviour a caller — or a test — gets per unit of interface it has to learn. |
| **seam** | A place where behaviour can be altered without editing in that place. Where an interface *lives*. |
| **adapter** | A concrete implementation sitting at a seam. |
| **leverage** | The caller's benefit from depth. |
| **locality** | The maintainer's benefit: a change, the bug it causes, and its fix all land in one place. |

Two rules settle most arguments:

- **The deletion test.** Delete the module in your head and inline it into its
  callers. If the complexity *reappears at every call site*, the module earns
  its place. If it merely moves, the module was a rename.
- **One adapter is a hypothesis, two are a seam.** An interface with a single
  implementation and no second one in sight is speculative generality: the
  interface cost is paid, the leverage is never collected.

## Phase 1 — Find the candidates

**Never scan the codebase exhaustively.** Structural pain is unevenly
distributed; a full sweep buries the three findings that matter under thirty
that don't.

1. **Read the record first.** `docs/architecture.md` for the intended
   structure, `docs/adr/INDEX.md` for what was already settled. A candidate
   that contradicts an `Accepted` ADR is not dropped — it is **labelled**, and
   reopening the ADR becomes part of its cost. Silently re-proposing a
   rejected design is the fastest way to make the whole report untrustworthy.
   If either file is missing, say so in the report rather than working around
   it in silence: it means nothing below was checked against a decision.
2. **Follow the churn.** `git log` over the last few months: which files
   change often, and which keep changing *together* without living together.
   Co-change across a boundary is the boundary telling you it's misplaced.
3. **Then look for the signals**, in those hot areas only:
   - understanding one concept means opening five files;
   - the interface is nearly as complex as the implementation — a
     pass-through, a bag of options, a wrapper that only renames;
   - a seam with one adapter and no second one in sight;
   - state or invariants leaking across a boundary: callers must call in a
     given order, or repair what the module handed back;
   - pure functions extracted for testability while the bug lives in how the
     caller strings them together;
   - one rule of the domain implemented in three places, none named after it.
4. **Check the tests before proposing anything.** If nothing in the area is
   covered, the finding is "this cannot be changed safely", and the first move
   is coverage at the *current* seam — not a redesign.

Aim for **3 to 6 candidates**. More than that means the filter wasn't applied.

## The report

Two outputs, same pass.

**The HTML page.** Copy the bundled template, then fill it with `Edit` — never
`Write`, the markup is the template's job:

```sh
cp <skill-dir>/template.html "${TMPDIR:-/tmp}/improve-architecture-<repo>-$(date +%Y%m%d-%H%M).html"
```

```powershell
Copy-Item <skill-dir>/template.html "$env:TEMP\improve-architecture-<repo>-$(Get-Date -f yyyyMMdd-HHmm).html"
```

**Name the file after the repository** — the temp directory is shared by every
project on the machine, and a date alone doesn't say which codebase a report is
about. **Never inside the repository**
— the doc map closes the project's file list at ten slots, and a report is
none of them. One `.card` per candidate, strongest first, each carrying:

- the modules and files involved;
- the friction **with evidence** — a commit, a call site, a test that had to
  be written twice. An adjective is not evidence, and a card without any is
  an opinion wearing a badge;
- a before/after drawn with the template's `.flow` boxes;
- the target interface, written out;
- what it buys, said in leverage and locality;
- what it costs — call sites touched, migration steps, what gets harder;
- a strength badge: `Strong` (friction measured, shape obvious) /
  `Worth exploring` (real friction, shape uncertain) / `Speculative` (a
  hunch — say so). **A report where everything is Strong has ranked nothing**;
- the ADR conflict and its number, when there is one.

Report the absolute path. **Don't open it** — that's the user's call.

**The chat summary**, in the same reply: the **three strongest** candidates,
a title line and two lines of friction each, so a choice can be made without
opening the file. Name the others in one line and stop there.

Then **stop**. Do not start the top one because it is obviously right.

## Phase 2 — Grill the pick

The user picks one. Now interrogate it, **one question at a time**, until the
shape is settled or the candidate dies. A candidate that dies here is a
success: it died for free.

1. **The interface, first.** Write the target signature, with its invariants
   and error modes. If it can't be written yet, the design isn't ready and
   the remaining questions are premature.
2. **The load-bearing constraints.** What forces the current shape — a
   platform limit, a deadline long past, a dependency, a caller nobody owns?
   Most "bad" structure is a constraint nobody wrote down.
3. **The seam.** Where does the interface live, and what are the two adapters?
4. **The migration.** Can it land incrementally, with the codebase working at
   every step? A refactor that only works once finished is a rewrite under a
   friendlier name — say so, and let the user decide that explicitly.
5. **The tests.** Which existing ones pin the current behaviour, and what has
   to be written *before* the move rather than after.
6. **The stopping condition.** What is out of scope — written down, because
   this is where scope creep enters.

## Landing it

- **A load-bearing reason found during the grilling earns an ADR** —
  `write-adr`, status `Proposed`, never self-accepted. That includes the
  candidate that *died*: "we keep this shallow deliberately, because X" is
  exactly the decision nobody records and everybody re-litigates.
- **`docs/architecture.md` is updated in the same change** as the code that
  moves. It describes the structure; letting it describe the old one is worse
  than having no map at all.
- **New domain vocabulary** from the discussion goes to `docs/architecture.md`
  with the rest of the structure — and to `AGENTS.md` only if an agent needs
  it to navigate.
- Follow the project's git workflow for the change itself: one refactor per
  branch, never mixed into a feature.
