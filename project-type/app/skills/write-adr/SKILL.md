---
name: write-adr
description: Write a new architecture decision record in docs/adr/ — pick its number, fill the Nygard format, add its INDEX.md row, and supersede or deprecate the ADR it replaces. Use when a decision worth recording has just been made.
when_to_use: Use when actually writing an ADR on a project that has adopted project-type-app — a decision was made that constrains the design, or an existing ADR needs superseding.
---

# Write an ADR

The `adr` rule says what deserves an ADR and what binds. This is the shape
one takes on disk.

## Layout

- `docs/adr/<NNNN>-<slug>.md`, whatever its status. Numbers are assigned
  once and **never reused**; take the highest existing number plus one,
  including deprecated and superseded files in the scan.
- `docs/adr/INDEX.md` — one row per ADR: id, title, status, one-sentence
  summary, tags. The summary states the *decision*, not the topic ("No
  global state — props down, callbacks up", not "State management"): it is
  what a reader routes on. Tags reuse `architecture.md`'s module names.

## Format (Nygard)

```markdown
# <NNNN>. <Title>

Status: <Proposed | Accepted | Deprecated | Superseded by ADR-<NNNN>>
Date: <YYYY-MM-DD>

## Context

<the forces at play, stated as neutrally as the decision allows>

## Decision

<the decision, stated plainly>

## Consequences

<what this makes easier, harder, or forecloses>
```

## Procedure

1. **Check it isn't already decided.** Scan `INDEX.md` — an existing ADR on
   the same subject means superseding it, not writing a parallel one.
2. **Write the file** at the next free number, status `Proposed`. Never
   self-accept: promoting to `Accepted` is the user's call.
3. **Supersede in place, never edit to reverse.** The old file stays as it
   is, with its status changed to `Superseded by ADR-<NNNN>`. With nothing
   replacing it: `Deprecated`, with the reason in its own `Consequences`.
4. **Add the `INDEX.md` row** in the same pass, and update the superseded
   ADR's row too.
5. **Log the ADR in the change that makes the decision** — the commit body
   naming `ADR-<NNNN>` is what ties the two together later.
