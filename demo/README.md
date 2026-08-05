# Demo: validating the ai-dev-toolkit blocks

Dummy sub-projects, just enough fake source to trigger each block's rules and
let you invoke each skill for real, without touching an actual project.

Run everything from this repo's root, passing a `demo/` fixture as
`--project-dir`. Nothing here is destructive: `tools/sync` always shows a diff
and asks before writing, so any command below can be dry-run by answering no.

Fixtures for the parked blocks (embedded C, model-based design, Node.js, the
Rust CLI) moved to [`../incubator/demo/`](../incubator/demo/) along with the
blocks themselves — they can't be synced, so they can't be demoed.

## Baseline

```
python -m tools.sync sync --toolkit-root . --project-dir demo/process-light-project
```

No entry ids syncs every `tier: baseline` entry at once. Expected:
`common-rules` writes `.claude/rules/{security,git-workflow,language,process-profile}.md`;
`context-quality` writes its rule, two skills, the `revise-agents-md` command
and registers `context-check.sh`; `gitlab` patches `enabledPlugins`;
`toolkit-self-check` writes its hook and registers it.

Then ask Claude to "write a commit message" anywhere — the git-workflow and
language rules should surface unprompted, since they're unscoped and load at
launch.

## The quiet path: a scratch folder

The behaviour worth checking most, because it's the one that decides whether
people keep the toolkit installed:

```
mkdir /tmp/scratch && cd /tmp/scratch
```

Open a session there. Expected: **no `.claude/` is created, and the drift
check prints one line at most.** Then `git init` in the same folder and open a
session again — now the report is explicit about the missing baseline.

## process-light and the doc map

```
python -m tools.sync sync process-light --toolkit-root . --project-dir demo/process-light-project
```

- Ask Claude to run `init-project-docs` — expected: it fills `README.md`,
  `docs/architecture.md`, `docs/adr/`, `docs/requirements.md` from
  what the fixture actually contains, and creates five stubs
  (`vision`, `user-guide`, `developer-guide`, `build-and-release`,
  `testing-strategy`) each carrying its own guard line.
- **The test that matters**: ask for something touching packaging, then check
  that `docs/build-and-release.md` is *still a stub*. An agent that fills it
  because it looks empty is the failure mode the guard line exists to prevent.
- Ask Claude to "audit the docs" — expected: `audit-docs` reports the map
  state, whether any trigger has fired, requirement statuses, and content
  routing. It should propose, not apply.
- Seed a second ADR under `docs/adr/active/` that contradicts `0001` (or
  mark `0001` `Superseded` without moving its file to `docs/adr/archive/`),
  then ask Claude to run `adr-cleanup` — expected: it flags the
  contradiction or the misplaced file, proposes a fix and a regenerated
  `INDEX.md`, and applies nothing on its own.

## process-none

```
python -m tools.sync sync process-none --toolkit-root . --project-dir <a scratch copy>
```

Expected: no docs discipline at all. Ask for a feature — Claude shouldn't
mention requirements or decisions. Then check the choice-group is enforced:
syncing `process-light` into the same project must fail, naming the conflict.

## context-quality

```
python -m tools.sync sync context-quality --toolkit-root . --project-dir demo/process-light-project
```

- `init-project-context` — expected: an `AGENTS.md` following the fixed
  skeleton, under 150 lines, and a `CLAUDE.md` reduced to `@AGENTS.md`.
- Break it on purpose: add a `| \`notarealcommand\` |` row to the Commands
  table, or point at a `docs/` file that doesn't exist. Open a new session —
  `context-check.sh` should name exactly that. Revert it: silence.

## stacks (desktop architecture)

```
python -m tools.sync detect --project-dir demo/python-tool
python -m tools.sync sync tech-stack-python --toolkit-root . --project-dir demo/python-tool
```

Expected: `detect` suggests `python`. Then ask "I want to build a desktop app
for this" *before* syncing any stack — the `desktop-app-architecture` skill
from `process-light` should tour the three branches, ask what matters, and
hand off with an explicit sync command rather than answering the structural
question itself.

## Code navigation and output compression

Both ship in the baseline, so they arrive with `common-rules`. Neither does
anything until asked:

- `codegraph-freshness.sh` exits immediately when CodeGraph isn't installed —
  open a session and confirm it says nothing.
- The `codegraph` rule is written to apply only when `codegraph_explore` is
  actually available. Ask "who calls this function" on a project without it
  and confirm Claude reaches for grep without mentioning a graph.
- Ask for `/caveman` and confirm the answers get terser while code blocks and
  error strings stay verbatim.
