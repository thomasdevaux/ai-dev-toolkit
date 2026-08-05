---
description: Record what this session learned into AGENTS.md
allowed-tools: Read, Edit, Glob, Grep
---

Review this session for context that would have made it go better, and propose
it as an addition to `AGENTS.md`. Informed by Anthropic's
`claude-md-management` plugin (Apache 2.0), retargeted to `AGENTS.md` and this
project's doc map.

## Step 1: Reflect

What did this session have to discover the hard way?

- a command that had to be found, or that failed the way it was documented;
- a code pattern the project follows and nothing stated;
- something that broke silently — an ordering constraint, a generated file, a
  platform quirk;
- an environment or configuration quirk (a variable that must be set at build
  time, a connection string with a mandatory option);
- a dependency relationship that isn't visible in the code (module A must be
  initialised before B);
- an entry point that took too long to locate.

## Step 2: Filter, hard

`AGENTS.md` loads on **every** session. An addition has to be worth that price
on every future session, not just this one. Drop:

- one-off fixes unlikely to recur;
- anything the code states plainly;
- generic advice already covered by the synced rules;
- anything with a slot in the doc map — that goes to its slot instead, and at
  most earns a pointer here.

## Step 3: Route each remaining item

| Kind of learning | Destination |
| --- | --- |
| A command, a locating fact, an invariant | `AGENTS.md` |
| Why something is built this way | `docs/architecture.md` |
| A choice made, an alternative rejected | `docs/decisions.md` |
| An install/environment prerequisite | `docs/developer-guide.md` |
| Personal preference, not team-wide | your user-scope config, not this repo |

## Step 4: Propose

One line per concept. For each:

```
### AGENTS.md — <section>

**Why:** <one line: what it cost this session not to know>

+ <the addition, as short as it can be and still true>
```

If `AGENTS.md` is near its 150-line target, say what you'd **remove** to make
room. An append-only context file degrades on its own.

## Step 5: Apply only what's approved

Ask before editing. Apply exactly what the user accepts, nothing adjacent.
