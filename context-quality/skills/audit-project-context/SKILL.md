---
name: audit-project-context
description: Review this project's AGENTS.md — accuracy, size, skeleton, content that belongs in a doc instead. Pass `session` to instead harvest what this session had to discover the hard way. Use when asked to audit or improve the project context, when the context-check hook flags something, or to record what a session learned.
---

# Audit project context

Read-only review of `AGENTS.md`. **Report findings; change nothing without
confirmation.** Two modes, one shared standard:

| Mode | Invocation | Question it answers |
| --- | --- | --- |
| **review** (default) | `/audit-project-context` | Is what's in there still true, and does it still earn its place? |
| **session** | `/audit-project-context session` | What did *this* session have to discover that should have been in there? |

The session mode is informed by Anthropic's `claude-md-management` plugin
(Apache 2.0), retargeted to `AGENTS.md` and this project's doc map.

## The standard, both modes

`AGENTS.md` loads on **every** session, so a line has to be worth that price
on every future session — not just the one that produced it. Three tests:

- **Does the code already say it plainly?** Then it doesn't belong here.
- **Is it generic best practice?** That's what the synced rules are for.
- **Does it have a slot in the doc map?** Then it goes to its slot, and at
  most earns a pointer here.

Also out: history — what a past session fixed, what used to be broken.

**Routing table.** A finding without a destination just becomes a deletion
nobody dares make, so every item that leaves `AGENTS.md` gets one:

| Kind of content | Destination |
| --- | --- |
| A command, a locating fact, an invariant | `AGENTS.md` |
| Why something is built this way; a module map | `docs/architecture.md` |
| A choice made, an alternative rejected | `docs/adr/` |
| An install or environment prerequisite | `docs/developer-guide.md` |
| Personal preference, not team-wide | your user-scope config, not this repo |

**The boundary that decays fastest** is `Layout`. It answers *"where do I
go"* — locating, no explanation — and the cost is paid on every session.
`docs/architecture.md` answers *"why is it built this way"* and carries the
detailed module map. The moment `Layout` starts explaining, it has drifted,
and what it grew belongs in `architecture.md`.

---

## Mode: review

The deep pass. The mechanical checks — size, dead pointers, uninstalled
commands, staleness — already run at session start via `context-check.sh`; if
that hook flagged something, start there and go further.

1. **Skeleton conformance.** Sections present, in the order the
   `project-context` rule fixes. Flag an extra section, a missing mandatory
   one (`Commands`, `Layout`, `Only if you need it`), and any heading kept
   with nothing real under it.

2. **Accuracy — the highest-value check**, and the one no hook can do.
   Everything here is verifiable, so verify it rather than judging it:
   - every command in `Commands` still exists and still does what's claimed
     (run the cheap read-only ones);
   - every path in `Layout` exists;
   - every pointer in `Only if you need it` resolves to a file that exists and
     isn't an on-hold stub;
   - every invariant is still true of the code.

3. **Size and density.** Line count against the 150 target and 200 cap. Then
   the harder question: which lines earn their place on *every* session? Apply
   the three tests above to each.

4. **Routing.** Everything that fails a test goes to its destination in the
   table above.

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

---

## Mode: session

1. **Reflect.** What did this session have to discover the hard way?
   - a command that had to be found, or that failed the way it was documented;
   - a code pattern the project follows and nothing stated;
   - something that broke silently — an ordering constraint, a generated file,
     a platform quirk;
   - an environment or configuration quirk (a variable that must be set at
     build time, a connection string with a mandatory option);
   - a dependency relationship invisible in the code (A must init before B);
   - an entry point that took too long to locate.

2. **Filter, hard**, with the three tests above. Drop one-off fixes unlikely
   to recur — most of what a session learns is not worth recording.

3. **Route** each survivor through the table above.

4. **Propose**, one line per concept:

   ```
   ### AGENTS.md — <section>

   **Why:** <one line: what it cost this session not to know>

   + <the addition, as short as it can be and still true>
   ```

   If `AGENTS.md` is near its 150-line target, say what you'd **remove** to
   make room. An append-only context file degrades on its own.

5. **Apply only what's approved.** Ask before editing. Apply exactly what the
   user accepts, nothing adjacent.
