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
| `python -m tools.audit --toolkit-root .` | Lint: `paths:` overlap, 200-line rule cap, choice-group integrity. |

No build step — markdown + YAML + two small Python packages under `tools/`.

## Repo layout

```
sync-manifest.yaml   # every syncable entry — single source of truth for tier/scope/detect
common/               process/<light|full>/          stacks/<topic>/
tools/sync/           tools/audit/                    templates/new-block/
```

## Self-application

This repo does not sync its own blocks onto itself, and commits land
directly on `main` — deliberate, since it's the source these blocks are
authored and validated in, not a consumer of them. Don't apply
`common/rules/*` conventions (branch-per-feature, PR review, etc.) here
unless the user asks.

## Only if you need it

Don't preload these — open one only when the task actually calls for it.

- Adding, modifying, or deprecating a block →
  [`docs/developer-guide.md`](docs/developer-guide.md).
- Why a block/tier decision was made, non-obvious tool/sync behaviors →
  [`docs/developer-guide.md`](docs/developer-guide.md#gotchas).
- How blocks/tiers/rule-loading work → [`docs/architecture.md`](docs/architecture.md).
- Guarantees `tools/sync`/`tools/audit` must hold →
  [`docs/requirements.md`](docs/requirements.md).
- Adopting the toolkit in a project, block catalog, official plugins →
  [`docs/user-guide.md`](docs/user-guide.md).
- Why this repo exists → [`docs/vision.md`](docs/vision.md).
