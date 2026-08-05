---
name: init-project-docs
description: Create this project's docs/ tree — the five filled slots and the five on-hold stubs of the doc map. Use when setting up a project that just adopted process-light, or when its docs/ tree is missing or partial.
when_to_use: Use when a project adopts process-light and has no docs/ tree yet, or when the doc map's slots are partly missing.
disable-model-invocation: true
---

# Init project docs

Materialize the doc map (see the `docs-map` rule) in a project that has just
adopted `process-light`. `AGENTS.md` is **not** created here — that's
`init-project-context`'s job, in the `context-quality` block.

Read-then-write: never overwrite an existing file. Report what you skipped.

## Procedure

1. **Check the profile.** `.claude/.toolkit-sync-state` must list
   `process-light`. If it lists `process-none`, stop and say so — that profile
   deliberately has no docs tree.

2. **Fill the five active slots** from what the repository actually contains —
   never from a template's placeholder text:

   - `README.md` — what this is (one paragraph), how to install and run it,
     links to the rest. If one exists, leave it alone.
   - `docs/architecture.md` — structure, flows, and the map of the modules
     (where each part of the code lives, one line each). Derive it by reading
     the tree, not by guessing.
   - `docs/decisions.md` — the header and format described by the `decisions`
     rule, plus any decision already visible in the code or git history that's
     worth recording. An empty log with a correct header is fine.
   - `docs/requirements.md` — the table described by the `requirements` rule.
     Seed it with what the code already does, one `REQ-00X` line per feature,
     status `done`. If the code does nothing yet, an empty table is fine.
   - `AGENTS.md` — skip. Tell the user to run `init-project-context`.

3. **Create the five on-hold stubs.** Exact shape, one per file:

   ```markdown
   # <Title>

   > On hold. Fill this in as soon as <trigger>. Don't fill it before:
   > invented content here costs more than an empty file.
   ```

   | File | Trigger sentence |
   | --- | --- |
   | `docs/vision.md` | the project carries an ambition or roadmap worth stating |
   | `docs/user-guide.md` | someone other than the author uses it |
   | `docs/developer-guide.md` | install or environment prerequisites stop being obvious |
   | `docs/build-and-release.md` | an artifact is distributed beyond the dev machine |
   | `docs/testing-strategy.md` | there's a deliberate coverage gap worth recording |

4. **Check a trigger hasn't already fired.** If the project already ships an
   artifact, already has a second contributor in `git log`, or already has
   users, say so and offer to fill that slot now instead of leaving the stub.

5. **Report**: files created, files left untouched, and any trigger you found
   already fired.

## What not to do

- Don't fill an on-hold stub because it looks empty. The guard line is the
  point of the stub, not decoration.
- Don't create a file outside the map. If the project has content that fits no
  slot, report it to the user — that's a map problem, and it's theirs to
  arbitrate.
