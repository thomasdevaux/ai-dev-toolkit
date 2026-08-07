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

The five on-hold slots exist as stub files, each carrying its own trigger.
**A stub is not an invitation**: filling one before its trigger fires
produces plausible fiction, which is worse than the gap it hides. Read the
trigger in the file itself; `init-project-docs` is what writes the stubs.

## The boundaries that decay fastest

- `README.md` is the entry point, not a container — architecture
  explanations belong in `architecture.md`.
- `docs/adr/` holds the *why*, `architecture.md` the *what*. A decision
  buried in an architecture paragraph is a decision nobody will find.

## Keeping it current

**No commit is required to carry a doc update.** Staleness is caught by
review instead: `audit-docs` on demand and as a mandatory step of the release
procedure, `adr-cleanup` on demand for `docs/adr/` specifically.
