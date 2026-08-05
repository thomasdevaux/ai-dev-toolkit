# ai-dev-toolkit

Shared Claude Code configuration baseline for a multi-stack engineering
team, distributed as a **synced-and-committed toolkit**: you check out
this repo, run its sync tool against your own project, and the resulting
rules/skills/commands/hooks land as ordinary files under your project's
`.claude/` (or your `~/.claude/` for user-scope tools), committed to your
repo like any other file.

It ships two things:

- **Blocks** — the syncable conventions: a common baseline (rules, code
  navigation, output compression), project context (`AGENTS.md`), a process
  profile, and desktop-app architecture guidance per language.
- **A handbook** — [`handbook/`](handbook/), a team reference on working with
  an agentic coding tool. Never synced anywhere; written for people.

See [`docs/vision.md`](docs/vision.md) for why this exists.

## Quickstart

**Once per machine** — this is what makes opening a session anywhere useful:

```
python -m tools.sync sync --user --toolkit-root .
```

The common block, the status line, the drift check and the 13 official
language servers land in `~/.claude/`. A session opened in a scratch folder
then has all of it, and creates nothing.

**Per project**, in a git repository:

```
# what would be suggested here
python -m tools.sync detect --project-dir /path/to/your/project

# every tier:baseline entry at once
python -m tools.sync sync --toolkit-root . --project-dir /path/to/your/project

# exactly one process profile
python -m tools.sync sync process-light --toolkit-root . --project-dir /path/to/your/project
```

See [`docs/user-guide.md`](docs/user-guide.md) for the full quickstart and the
block catalog.

## What this repo is

`sync-manifest.yaml` lists every syncable **block** — a directory tree shaped
internally like `.claude/` itself (`rules/`, `skills/`, optionally
`commands/`, `agents/`, `hooks/`). `tools/sync` reads the manifest, diffs a
block's files against your project's `.claude/`, shows exactly what would
change, and only writes after you confirm.

The manifest deliberately exposes **only mature content**. Blocks written but
not yet validated on a real project live in [`incubator/`](incubator/) and
cannot be synced. Third-party content is **copied in plain text** with its
license and a `SOURCE.md` recording upstream and pinned commit, rather than
installed as a plugin — see
[`handbook/plugins-policy.md`](handbook/plugins-policy.md).

## Documentation

| Doc | For |
| --- | --- |
| [`handbook/`](handbook/) | Working with an agent, day to day. Written for the team, not the toolkit. |
| [`docs/vision.md`](docs/vision.md) | Why this toolkit exists and who it serves. |
| [`docs/architecture.md`](docs/architecture.md) | How blocks, tiers, and rule-loading actually work. |
| [`docs/decisions.md`](docs/decisions.md) | Why the non-obvious choices were made. |
| [`docs/requirements.md`](docs/requirements.md) | The guarantees `tools/sync`/`tools/audit` must hold. |
| [`docs/user-guide.md`](docs/user-guide.md) | Adopting this toolkit in your project. |
| [`docs/developer-guide.md`](docs/developer-guide.md) | Contributing — adding/modifying/deprecating a block. |

## Adding a new block

Use [`templates/new-block/SKILL.md`](templates/new-block/SKILL.md) (point
Claude at the file directly, or copy it into `.claude/skills/` locally to have
it auto-trigger). It asks for the block's topic, location, tier, and scope,
then generates a skeleton matching this repo's conventions and registers it in
`sync-manifest.yaml`. See
[`docs/developer-guide.md`](docs/developer-guide.md) for the full workflow.
