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
| `python -m tools.sync switch <group> <id> --toolkit-root . --project-dir <path>` | Adopt a different member of a choice-group (e.g. `project-type`). |
| `python -m tools.audit --toolkit-root .` | Lint: `paths:` overlap, rule character budgets, choice-group integrity, third-party provenance, missing `summary:`, skill/command/agent frontmatter. |
| `python -m pytest` | The test suite for `tools/`. |

No build step — markdown + YAML + two small Python packages under `tools/`.

## Layout

```
sync-manifest.yaml   # index of `- include:` lines, one per block's own manifest.yaml
plugins.yaml          # official-plugin entries with no block directory of their own
common/              # the baseline block: rules + always-available skills
context-quality/  project-type/<none|app|embedded-fccu>/  tech-stacks/<lang>/
tech-stacks/shared/  # files several stacks deploy verbatim, via `shared_files:`
self-check/          # a block too: the /toolkit-sync, -features, -help commands
toolkit-status(.cmd)  toolkit-help(.cmd)  # same, no Claude Code needed
user-tools/          # blocks deployed to ~/.claude/ rather than a project
suggested/<topic>/   # tier: suggested blocks — useful, opt-in, never imposed
incubator/           # parked blocks, deliberately absent from the manifest
handbook/            # team reference on agentic coding (not synced, not toolkit docs)
docs/                # this toolkit's own documentation
tools/sync/  tools/audit/  templates/new-block/  tests/  demo/
```

## Invariants

- **`incubator/` and `handbook/` are never synced.** Nothing in them may be
  referenced by a manifest entry.
- **Copied third-party content carries a `SOURCE.md` beside it** — upstream,
  commit, license, import date — plus its `LICENSE` file. `tools/audit` fails
  without them (`common/skills/caveman/` is the current example).
- **Rules are budgeted in characters, per file and per session.** No single
  `rules/*.md` exceeds 4,000 chars. Beyond that the worst-case set a project
  syncs (baseline + the largest project-type profile + tech-stacks) is
  budgeted twice over, because the two kinds of rule are not paid at the same
  time: rules with no `paths:` load at session start and stay under 20,000;
  rules with `paths:` load only when a matching file is opened and stay under
  16,000. Characters, not lines: a line budget taxes blank lines and rewards
  re-wrapping prose over cutting it. Skills and commands are uncapped; they
  load on demand.
- **A hook only runs if its block's `settings_patch` registers it**, and must
  stay silent when its check passes.
- **Every `commands/*.md` and `agents/*.md` states its `model:`.** Only those
  two file kinds can name one; omitting it silently inherits the session's
  model, the most expensive default. `tools/audit` fails without it.
- **`common/` deploys to both `.claude/` and `~/.claude/`** — anything put
  there runs in every folder, including scratch ones. That's the constraint
  keeping `context-quality/` a separate block.

## Self-application

`.claude/` in this repo is committed, real `tools/sync` output — this repo
dogfoods its own sync mechanism rather than special-casing itself out of it.
That's separate from where blocks are *authored*: `common/`, `tech-stacks/`,
`project-type/`, etc. remain the edited source; `.claude/` is the synced
artifact kept in sync with them, not a place to hand-edit. Don't apply
`common/rules/*` conventions (branch-per-feature, PR review, etc.) to this
repo's own workflow unless the user asks — that's a separate decision from
syncing the files. It does, however, follow the doc map it publishes.

## Only if you need it

Don't preload these — open one only when the task actually calls for it.

- Blocks, tiers, rule-loading, and the add/change/deprecate workflow →
  [`docs/maintaining.md`](docs/maintaining.md).
- Adopting the toolkit in a project → [`README.md`](README.md).
- How the team is meant to work with an agent → [`handbook/`](handbook/).
