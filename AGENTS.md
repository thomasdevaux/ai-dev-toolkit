# ai-dev-toolkit

Shared Claude Code configuration baseline for a multi-stack engineering
team, distributed as a **synced-and-committed toolkit**: consumer projects
run `tools/sync` against a checkout of this repo to copy rules/skills/
agents/hooks into their own `.claude/`, committed like any other file.
This repo is where those blocks are authored and validated, not a
consumer of them.

## Commands

| Command | Description |
|---------|-------------|
| `python -m tools.sync sync <id...> --toolkit-root . --project-dir <path>` | Sync manifest entries into a project's `.claude/`. |
| `python -m tools.audit --toolkit-root .` | Lint: `paths:` overlap, 200-line rule cap, choice-group integrity, `vendor/` provenance, missing `summary:`. |
| `python -m pytest` | The test suite for `tools/`. |

No build step — markdown + YAML + two small Python packages under `tools/`.

## Repo layout

```
sync-manifest.yaml   # every syncable entry — single source of truth for tier/scope/summary/detect
common/              # the baseline block: rules + always-available skills
context-quality/  process/<none|light|full>/  tech-stacks/<lang>/
incubator/           # parked blocks, deliberately absent from the manifest
handbook/            # team reference on agentic coding (not synced, not toolkit docs)
docs/                # this toolkit's own documentation
tools/sync/  tools/audit/  templates/new-block/
```

## Invariants

- **`incubator/` and `handbook/` are never synced.** Nothing in them may be
  referenced by a manifest entry.
- **Copied third-party content carries a `SOURCE.md` beside it** — upstream,
  commit, license, import date — plus its `LICENSE` file. `tools/audit` fails
  without them (`common/skills/caveman/` is the current example).
- **A block's `rules/*.md` total 200 lines at most.** Skills and commands are
  uncapped; they load on demand.
- **A hook only runs if its block's `settings_patch` registers it**, and must
  stay silent when its check passes.
- **`common/` deploys to both `.claude/` and `~/.claude/`** — anything put
  there runs in every folder, including scratch ones. That's the constraint
  keeping `context-quality/` a separate block.

## Self-application

This repo does not sync its own blocks onto itself, and commits land
directly on `main` — deliberate, since it's the source these blocks are
authored and validated in, not a consumer of them. Don't apply
`common/rules/*` conventions (branch-per-feature, PR review, etc.) here
unless the user asks. It does, however, follow the doc map it publishes.

## Only if you need it

Don't preload these — open one only when the task actually calls for it.

- Adding, modifying, or deprecating a block →
  [`docs/developer-guide.md`](docs/developer-guide.md).
- Why a block/tier decision was made →
  [`docs/decisions.md`](docs/decisions.md).
- How blocks/tiers/rule-loading work → [`docs/architecture.md`](docs/architecture.md).
- Guarantees `tools/sync`/`tools/audit` must hold →
  [`docs/requirements.md`](docs/requirements.md).
- Adopting the toolkit in a project, block catalog →
  [`docs/user-guide.md`](docs/user-guide.md).
- Why this repo exists → [`docs/vision.md`](docs/vision.md).
- How the team is meant to work with an agent → [`handbook/`](handbook/).
