# ai-dev-toolkit

A shared Claude Code configuration for a multi-stack engineering team:
security/git rules, a process discipline, and per-language architecture
guidance — authored once here, pulled into each project on purpose.

## How it's deployed and maintained

**Synced and committed, not installed.** A project runs `tools/sync`
against a checkout of this repo. The result — rules, skills, hooks —
lands as ordinary files under the project's own `.claude/`, reviewed as
a diff and committed like any other change. From then on the project
owns those files; this repo doesn't need to be present or reachable for
them to keep working. Re-running `sync` later pulls in updates,
explicitly, on the project's own schedule.

**Why not an internal plugin marketplace.** Claude Code supports
installing plugins from a marketplace — one command, auto-updating,
nothing to read. We deliberately don't distribute this way. The team is
still learning to work with an agent, and a rule file you can open,
question, and edit teaches that; a plugin install does not. Sync-and-
commit costs a bit more ("pull the update yourself") in exchange for
every convention being visible, readable, and owned by the project it's
in.

## Deploying to a new project

Once per machine:

```
python -m tools.sync sync --user --toolkit-root .
```

This puts the common rules, the status line, the drift check and the
language servers in `~/.claude/`, so any folder you open already has
them.

Then, per project, from inside that project's git repository:

```
python -m tools.sync sync --toolkit-root <checkout> --project-dir .
python -m tools.sync sync process-light --toolkit-root <checkout> --project-dir .
```

The first line syncs everything expected on every project. The second
picks the process profile (`process-none` / `process-light` /
`process-full` — pick one). Each command shows exactly what it would
write and asks before touching anything. Review the diff, commit it.

That's the whole workflow. For the full command reference and block-by-
block catalog, see [`docs/user-guide.md`](docs/user-guide.md).

## What it covers

| Layer | Applies to | What you get |
| --- | --- | --- |
| **Common** | every project | Security and git-workflow rules, the process-profile prompt, code navigation, output compression. |
| **Context** | every project | `AGENTS.md` as the one context file — fixed skeleton, init/audit skills, a session-start freshness check. |
| **Process** | every project (pick one) | `none` for scripts, `light` for a real tool or app (doc map, requirements, ADR log), `full` for critical software (stub, defers to `light` today). |
| **Tech stack** | projects matching a marker file | Desktop-app architecture per language: Python, Rust, Go, .NET. |
| **User tools** | your machine | Status line, session-start drift check, official language servers — installed once, working everywhere. |

## Documentation

| Doc | For |
| --- | --- |
| [`docs/user-guide.md`](docs/user-guide.md) | The full command reference and block catalog. |
| [`docs/architecture.md`](docs/architecture.md) | How blocks, tiers, and rule-loading work. |
| [`docs/decisions.md`](docs/decisions.md) | Why the non-obvious choices were made. |
| [`docs/requirements.md`](docs/requirements.md) | The guarantees `tools/sync`/`tools/audit` must hold. |
| [`docs/developer-guide.md`](docs/developer-guide.md) | Contributing — adding, changing, or deprecating a block. |
| [`handbook/`](handbook/) | Working with an agent day to day — for the team, not about the toolkit. |

## Adding a new block

Point Claude at [`templates/new-block/SKILL.md`](templates/new-block/SKILL.md)
(or copy it into `.claude/skills/` to have it auto-trigger). It asks for
the block's topic, location, tier and scope, then scaffolds it and
registers it in `sync-manifest.yaml`. See
[`docs/developer-guide.md`](docs/developer-guide.md) for the full
workflow.
