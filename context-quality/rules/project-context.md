# Project context: AGENTS.md

`AGENTS.md` is this project's agent context. `CLAUDE.md` is a one-line pointer
to it:

```markdown
@AGENTS.md
```

That's the whole file. Keeping the content in `AGENTS.md` is what makes it
portable — another agentic tool reads the same context without a second,
slowly diverging copy. Don't generate `GEMINI.md` or a Cursor config
preemptively; add one the day someone actually uses that tool.

## Fixed skeleton

Same sections, same order, on every project — that's what makes the audit
mechanical and the routing predictable. **A section with no real content is
removed, never padded.**

```markdown
# <project>
<one sentence: what this is>

## Commands
| command | what it does |

## Layout
where things live — 5 lines, no explanation

## Invariants          [only if there are any]
what breaks if you don't know it

## Only if you need it
- <task> → <doc>
```

- **Commands** — the commands actually typed, verified to work. A command that
  no longer runs is worse than no command at all.
- **Layout** — locating only. See the boundary below.
- **Invariants** — things that break silently: a generated file that must not
  be hand-edited, an ordering constraint, a platform quirk. Skip the section
  when there's nothing genuine.
- **Only if you need it** — every pointer names the condition that justifies
  opening it, so nothing gets loaded by reflex.

**Target 150 lines, hard cap 200.** Past the target, cut before adding. Past
the cap, it's a defect: the context that loads on every single session is the
most expensive text in the repository.

## The boundary that decays fastest

`Layout` answers **"where do I go"** — locating, no explanation, and the cost
is paid on *every* session. `docs/architecture.md` answers **"why is it built
this way"** and carries the detailed module map.

If `Layout` starts explaining, it has drifted, and what it grew belongs in
`architecture.md`. Same test for the rest: `AGENTS.md` is an index, `docs/` is
the content.

## What doesn't belong in AGENTS.md

- Anything the code already states plainly.
- Generic best practice — that's what the synced rules are for.
- History: what a past session fixed, what used to be broken.
- Anything that has a slot in the doc map. Put it in its slot and point at it.
