# ai-dev-toolkit

Shared Claude Code configuration baseline for a multi-stack engineering
team, distributed as a **synced-and-committed toolkit**: you check out
this repo, run its sync tool against your own project, and the resulting
rules/skills/agents/hooks land as ordinary files under your project's
`.claude/` (or your `~/.claude/` for user-scope tools), committed to your
repo like any other file. It bundles conventions for Python, Node.js/web,
Rust, embedded C, and Simulink/MATLAB model-based design, plus meta-
tooling for maintaining this repo itself.

See [`docs/vision.md`](docs/vision.md) for why this exists.

## What this repo is

`sync-manifest.yaml` lists every syncable **block** — a directory tree
under `common/`, `process/<variant>/`, `stacks/<topic>/`,
`user-tools/<topic>/`, or `self-check/`, each internally shaped like `.claude/` itself
(`rules/`, `skills/`, optionally `agents/` and `hooks/`). `tools/sync`
reads the manifest, diffs a block's files against your project's
`.claude/`, shows you exactly what would change, and only writes after
you confirm. See [`docs/architecture.md`](docs/architecture.md) for how
this works internally.

## Quickstart

```
# from inside a checkout of this repo
python -m tools.sync detect --project-dir /path/to/your/project

# sync every tier:baseline entry in one go (rules, its two official-plugin
# dependencies, and the toolkit-self-check drift-check hook)
python -m tools.sync sync --toolkit-root . --project-dir /path/to/your/project

# pick exactly one process profile
python -m tools.sync sync process-light --toolkit-root . --project-dir /path/to/your/project

# sync whichever stacks tools/sync detect suggested
python -m tools.sync sync stacks-python --toolkit-root . --project-dir /path/to/your/project
```

See [`docs/user-guide.md`](docs/user-guide.md) for the full quickstart,
block catalog, process-profile choice, and multi-tech example.

## Documentation

| Doc | For |
| --- | --- |
| [`docs/vision.md`](docs/vision.md) | Why this toolkit exists and who it serves. |
| [`docs/architecture.md`](docs/architecture.md) | How blocks, tiers, and rule-loading actually work. |
| [`docs/requirements.md`](docs/requirements.md) | The guarantees `tools/sync`/`tools/audit` must hold. |
| [`docs/user-guide.md`](docs/user-guide.md) | Adopting this toolkit in your project — quickstart, block catalog, official plugins. |
| [`docs/developer-guide.md`](docs/developer-guide.md) | Contributing to this repo — adding/modifying/deprecating a block, gotchas. |

## Adding a new block

Don't duplicate the scaffolding steps here — use
[`templates/new-block/SKILL.md`](templates/new-block/SKILL.md) (point
Claude at the file directly, or copy it into `.claude/skills/` locally
to have it auto-trigger). It asks for the block's topic, location, tier,
and scope, then generates a skeleton matching this repo's conventions
and registers it in `sync-manifest.yaml`. See
[`docs/developer-guide.md`](docs/developer-guide.md) for the full
add/modify/deprecate workflow.
