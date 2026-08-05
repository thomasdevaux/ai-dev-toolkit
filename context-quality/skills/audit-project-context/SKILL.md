---
name: audit-project-context
description: Full review of this project's AGENTS.md — accuracy, size, skeleton conformance, content that belongs in a doc instead. Use when asked to audit or improve the project context, or when the session-start check flagged something.
when_to_use: Use when asked to "audit the context", "check AGENTS.md", "improve the project memory", or after the context-check hook reports a problem.
disable-model-invocation: true
---

# Audit project context

Read-only review of `AGENTS.md`. **Report findings; change nothing without
confirmation.**

This is the deep pass. The mechanical checks — size, dead commands, pointers
to missing docs — already run at session start via `context-check.sh`; if that
hook flagged something, start there and go further.

## Procedure

1. **Skeleton conformance.** Sections present, in the order the
   `project-context` rule fixes. Flag an extra section, a missing mandatory
   one (`Commands`, `Layout`, `Only if you need it`), and any heading kept
   with nothing real under it.

2. **Accuracy — the highest-value check.** Everything here is verifiable, so
   verify it rather than judging it:
   - every command in `Commands` still exists and still does what's claimed
     (run the cheap read-only ones);
   - every path in `Layout` exists;
   - every pointer in `Only if you need it` resolves to a file that exists and
     isn't an on-hold stub;
   - every invariant is still true of the code.

3. **Size and density.** Line count against the 150 target and 200 cap. Then
   the harder question: which lines earn their place on *every* session?
   Flag filler, generic advice already covered by the synced rules, and
   anything restating what the code says plainly.

4. **Routing.** Content that belongs elsewhere:
   - `Layout` that explains rather than locates → `docs/architecture.md`;
   - a rationale or a rejected alternative → `docs/decisions.md`;
   - install prerequisites → `docs/developer-guide.md`;
   - anything else with a slot in the doc map → its slot.
   For each, name the destination — a finding without a destination just
   becomes a deletion nobody dares make.

5. **What's missing.** The inverse check, and the one the size cap makes easy
   to forget: something a session repeatedly has to rediscover — a
   non-obvious command, a quirk that bit twice, an entry point nobody finds —
   and that isn't recorded. Read the recent git history for candidates.

6. **Red flags** — cheap to spot, and each one means the file has stopped
   being trusted:
   - template text left uncustomised (a section that would read identically
     in any other repository);
   - a version or tool named that the project no longer uses;
   - the same fact stated in `AGENTS.md` and in a doc, drifting apart.

7. **`CLAUDE.md`** is exactly `@AGENTS.md`, nothing more.

8. **Report**, most consequential first, and say explicitly when a category is
   clean. End with a proposed set of edits — including what to *remove*, not
   only what to add. An audit that only ever adds is how a context file
   reaches 400 lines.
