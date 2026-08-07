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
- <task> → [<doc>](<path>)
```

- **Commands** — the commands actually typed, verified to work. A command that
  no longer runs is worse than no command at all.
- **Layout** — locating only, never explaining.
- **Invariants** — things that break silently: a generated file that must not
  be hand-edited, an ordering constraint, a platform quirk. Skip the section
  when there's nothing genuine.
- **Only if you need it** — every pointer names the condition that justifies
  opening it, so nothing gets loaded by reflex. Write it as a **markdown
  link**: that's what the session-start check verifies still resolves.

## The one routing test

`AGENTS.md` is the index; `docs/` is the content. The moment a line explains
rather than locates, it belongs in `docs/architecture.md` — and the same test
sorts the rest of what turns up here.

**Target 150 lines, hard cap 200.** Past the target, cut before adding; past
the cap it's a defect, because everything here competes for attention with
everything else here. *Move* what comes out to its slot in the doc map — don't
re-wrap prose to fit, that buys lines and changes nothing.

Writing or reworking this file is `/init-project-context`; reviewing it is
`/audit-project-context`. Both carry the detail this rule deliberately omits.
