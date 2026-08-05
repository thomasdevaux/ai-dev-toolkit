---
name: adr-cleanup
description: Garden docs/adr/ — flag ADRs that contradict each other, propose consolidations for near-duplicate or obsolete ADRs, check active/archive placement matches status, and regenerate docs/adr/INDEX.md from what's actually on disk.
when_to_use: Use on demand ("clean up the ADRs", "/adr-cleanup") on a project that has adopted process-light and has a docs/adr/ tree.
disable-model-invocation: true
---

# ADR cleanup

Read-only review. **Report findings; apply nothing without confirmation.**
This is the periodic gardening pass for `docs/adr/` — see the `adr` rule for
the format, layout and lifecycle it checks against.

## Procedure

1. **Status validity.** Every ADR in `active/` or `archive/` has one of
   `Proposed`, `Accepted`, `Deprecated`, `Superseded by ADR-<NNNN>`. Flag any
   other value, and any `Superseded` entry that doesn't name its replacement.

2. **Placement matches status.** `Deprecated` and `Superseded` ADRs must live
   in `archive/`, never `active/`. `Proposed` and `Accepted` must live in
   `active/`. Flag every mismatch — don't move files yourself, propose the
   move.

3. **Edited-in-place check.** An ADR whose `git log` shows its `Decision` or
   `Consequences` section changed after it reached `Accepted`, with no status
   change, is a reversal that skipped the lifecycle rule (a new ADR should
   have been written instead). Flag it.

4. **Contradictions.** Two `Accepted` ADRs whose decisions conflict on the
   same concern (check `INDEX.md` tags for overlap, then read both). Flag the
   pair — resolving which one holds is a call for the user, not this skill.

5. **Consolidation candidates.** Several `active/` ADRs on the same narrow
   topic, none contradicting but clearly fragments of one decision. Propose a
   single ADR that supersedes all of them, with a draft `Context`/`Decision`
   summarizing the group — don't write it without confirmation.

6. **INDEX.md drift.** Compare `docs/adr/INDEX.md` against the files actually
   present in `active/` and `archive/`: missing rows, stale statuses, entries
   for files that no longer exist. Propose a regenerated `INDEX.md`.

7. **Report.** A short list per category, most consequential first (a
   contradiction between two `Accepted` ADRs outranks a stale `INDEX.md`
   row). State explicitly when a category is clean. End with a proposed plan
   of fixes — moves, status corrections, consolidations, the regenerated
   index — and stop there.
