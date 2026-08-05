# The doc map

This project's documentation has a **closed map**: ten slots, each with one
purpose. The map exists to make routing deterministic — every topic has
exactly one destination, known in advance.

**Content that fits no slot is reported to the user, not filed somewhere.**
Never invent `docs/notes.md`, `docs/misc.md`, or a new `docs/` file outside
this map. An open map is how documentation silently scatters.

## The slots

| Slot | Answers | State |
| --- | --- | --- |
| `README.md` | What is this, how do I run it, where do I go next | filled |
| `AGENTS.md` | The agent's working context (see the project-context rule) | filled |
| `docs/architecture.md` | How it's built and why, plus the map of the code | filled |
| `docs/adr/` | Why a choice was made, and what was rejected | filled |
| `docs/requirements.md` | What the software is expected to do | filled |
| `docs/vision.md` | The original idea, the ambition, the roadmap | on hold |
| `docs/user-guide.md` | How to use it, for someone who isn't the author | on hold |
| `docs/developer-guide.md` | Prerequisites, environment, how to contribute | on hold |
| `docs/build-and-release.md` | Packaging, publishing, releasing | on hold |
| `docs/testing-strategy.md` | What's covered, what isn't, and why | on hold |

## Files on hold

The five on-hold slots exist as stub files from the start, so the map is
visible in the tree rather than only in this rule. Each stub names its own
trigger and forbids filling it early:

```markdown
# Build & release

> On hold. Fill this in as soon as an artifact is distributed beyond the
> dev machine. Don't fill it before: invented content here costs more
> than an empty file.
```

**Respect that line.** A stub is not an invitation — filling
`docs/build-and-release.md` on a project that ships nothing produces plausible
fiction, which is worse than the gap it hides. Fill a stub when its trigger
actually fires, and remove the on-hold line at that point.

Triggers:

- `vision.md` — the project carries an ambition or a roadmap worth stating.
- `user-guide.md` — someone other than the author uses it.
- `developer-guide.md` — install or environment prerequisites aren't obvious.
  This one anticipates the second developer rather than waiting for them: the
  point is that they can start, not that they already exist.
- `build-and-release.md` — an artifact is distributed beyond the dev machine.
- `testing-strategy.md` — there's a deliberate coverage gap worth recording.

## Boundaries that decay fastest

- `README.md` is the entry point, not a container. Architecture explanations
  in the README belong in `architecture.md`.
- `architecture.md` holds structure, flows **and the map of the modules**
  (where each part of the code lives and what it's for). A code-graph tool, if
  the project uses one, answers fine-grained questions on top of that map — it
  doesn't replace it.
- `docs/adr/` holds the *why*; `architecture.md` holds the *what*. A
  decision buried in an architecture paragraph is a decision nobody will find.

## Keeping it current

There is **no rule requiring a doc update in the same commit** — no commit is
weighed down by documentation. Staleness is caught by review instead:

- `audit-docs` on demand, whenever you want to know where things stand;
- `audit-docs` as a **mandatory step of the release procedure**;
- `adr-cleanup` on demand, to garden `docs/adr/` specifically.
