---
name: init-project-context
description: Create or rebuild this project's AGENTS.md (and its one-line CLAUDE.md pointer) from what the repository actually contains. Use when a project has no AGENTS.md, when its context file predates the fixed skeleton, or when asked to bootstrap project context.
when_to_use: Use when a project has no AGENTS.md, has a CLAUDE.md holding content instead of a pointer, or when asked to "set up the project context".
disable-model-invocation: true
---

# Init project context

Write `AGENTS.md` from evidence, not from a template's placeholders. The
`docs/` tree is **not** created here — on a `project-type-app` project that's
`init-project-docs`'s job.

## Procedure

1. **Gather evidence before writing a line.**
   - Commands: read the actual build/test config (`Makefile`, `pyproject.toml`,
     `package.json`, `Cargo.toml`, CI workflows). **Run the ones that are cheap
     and read-only** to confirm they work — an unverified command is the most
     common defect in a context file.
   - Layout: read the tree, one level or two. Name what a newcomer needs to
     locate, not everything present.
   - Invariants: look for generated files, ordering constraints, platform
     quirks, anything a `README` warns about.
   - `git log --oneline -30` for what the project is actually about, versus
     what it says it is.

2. **Handle an existing `CLAUDE.md`.**
   - If it holds real content, move that content into `AGENTS.md` (dropping
     what the code already says), then reduce `CLAUDE.md` to `@AGENTS.md`.
     Show the diff before replacing anything.
   - If it's already a pointer, leave it.

3. **Write `AGENTS.md`** to the fixed skeleton in the `project-context` rule.
   Drop any section you have no genuine content for — an empty `Invariants`
   heading is noise, not structure.

4. **Point at the docs, with conditions.** In `Only if you need it`, one line
   per doc that exists, each naming what triggers opening it, each written as
   a **markdown link** — that's the form `context-check.sh` verifies still
   resolves, and a bare path goes unchecked. Don't point at on-hold stubs:
   pointing at an empty file trains the reader to ignore the list. Where the
   project keeps ADRs, point at the index and never at individual ADRs — the
   index is the scan layer, and this file is the most expensive text in the
   repository:

   ```markdown
   - changing something structural, or adding a dependency → [ADR index](docs/adr/INDEX.md)
   ```

5. **Check the size.** Over 150 lines, cut before you finish. Over 200, you
   must cut. What comes out goes to its slot in the doc map, not to a scratch
   file.

6. **Report**: what you wrote, what you deliberately left out, and any command
   you couldn't verify (say so plainly rather than shipping it silently).

## What doesn't belong in the file

Three tests, applied to every line before it goes in. `AGENTS.md` loads on
**every** session, so a line has to be worth that price on every future one:

- **Does the code already say it plainly?** Then leave it out.
- **Is it generic best practice?** That's what the synced rules are for.
- **Does it have a slot in the doc map?** Then it goes to its slot, and at
  most earns a pointer here.

Also out: history — what a past session fixed, what used to be broken.

## Failure modes worth naming

- **Copying the tree into Layout.** Five lines that let someone find their way,
  not an inventory.
- **Documenting aspiration.** Only what's true today. A command that "should"
  work is a lie the next session will pay for.
- **Explaining in Layout.** This is the boundary that decays fastest.
  `Layout` answers *"where do I go"* — locating, no explanation.
  `docs/architecture.md` answers *"why is it built this way"* and carries the
  detailed module map. The moment `Layout` explains, what it grew belongs
  there.
