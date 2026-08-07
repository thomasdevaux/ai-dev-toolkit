---
name: adr-cleanup
description: Garden docs/adr/ — flag ADRs that contradict each other, propose consolidations for near-duplicate or obsolete ADRs, check index rows still state their decision, and regenerate docs/adr/INDEX.md from what's actually on disk.
when_to_use: Use on demand ("clean up the ADRs", "/adr-cleanup") on a project that has adopted project-type-app and has a docs/adr/ tree.
disable-model-invocation: true
---

# ADR cleanup

Read-only review. **Report findings; apply nothing without confirmation.**
This is the periodic gardening pass for `docs/adr/` — see the `adr` rule for
what belongs in the tree, and the `write-adr` skill for the format, numbering
and supersede chains it checks against.

## Procedure

1. **Run the mechanical checks.** Delegate to the `docs-lint` agent with
   `scope: adr`. It returns, as a plain findings list: status-value validity
   and missing `Date`s; `Superseded by` entries naming no replacement or one
   that isn't on disk; stalled `Proposed` ADRs oldest first; ADRs whose
   `Decision` or `Consequences` changed after they reached `Accepted` with no
   status change; and `INDEX.md` rows that have no file, files that have no
   row, and statuses that disagree.

   It runs on a cheaper model on purpose — those are vocabulary comparisons and
   file-presence tests, and none of them needs judgment. Invoking this skill is
   what asks for that delegation; don't ask again. What the agent hands back is
   raw material: it ranks nothing and proposes nothing, which is deliberate —
   steps 2 to 5 below are where this skill earns its keep.

   Read what it returns, then interpret it:

   - An **edited-in-place** hit is a reversal that skipped the lifecycle rule
     (a new ADR should have been written instead) — but check the commits it
     names first, since a typo fix in the same section is not a reversal.
   - **Stalled proposals** bind nobody. Accepting or dropping them is the
     user's call; carry them into the report, don't arbitrate them.

2. **Contradictions.** Two `Accepted` ADRs whose decisions conflict on the
   same concern (check `INDEX.md` tags for overlap, then read both). Flag the
   pair — resolving which one holds is a call for the user, not this skill.

3. **Consolidation candidates.** Several `Accepted` ADRs on the same narrow
   topic, none contradicting but clearly fragments of one decision. Propose a
   single ADR that supersedes all of them, with a draft `Context`/`Decision`
   summarizing the group — don't write it without confirmation.

4. **INDEX.md quality.** Step 1 already reported the structural drift (missing
   rows, orphan rows, statuses that disagree). What's left needs reading:
   rows that name a *topic* rather than the decision ("State management"
   instead of "No global state — props down, callbacks up") — the summary is
   what a reader routes on — and tags that match no module in
   `docs/architecture.md`. Propose a regenerated `INDEX.md` covering both the
   structural drift and these.

5. **Report.** A short list per category, most consequential first (a
   contradiction between two `Accepted` ADRs outranks a stale `INDEX.md`
   row). State explicitly when a category is clean. End with a proposed plan
   of fixes — status corrections, consolidations, the regenerated index — and
   stop there.
