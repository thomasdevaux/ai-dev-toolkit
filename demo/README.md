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
python -m tools.sync sync --toolkit-root . --project-dir demo/project-type-app-project
```

No entry ids syncs every `tier: baseline` entry at once. Expected:
`common-rules` writes `.claude/rules/{security,language,project-type-profile,
codegraph}.md` and the `desktop-app-architecture`, `commit-message-format`,
`caveman` and `codegraph-setup` skills; `context-quality` writes its rule, two skills, and
registers `context-check.sh`; `gitlab` patches
`enabledPlugins`; `toolkit-self-check` writes its hook and registers it.

Then ask Claude to "write a commit message" anywhere — the language rule
should surface unprompted, since it's unscoped and loads at launch.

## The quiet path: a scratch folder

The behaviour worth checking most, because it's the one that decides whether
people keep the toolkit installed:

```
mkdir /tmp/scratch && cd /tmp/scratch
```

Open a session there. Expected: **no `.claude/` is created, and the drift
check prints one line at most.** Then `git init` in the same folder and open a
session again — now the report is explicit about the missing baseline.

## project-type-app and the doc map

```
python -m tools.sync sync project-type-app --toolkit-root . --project-dir demo/project-type-app-project
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
- Seed a second ADR under `docs/adr/` that contradicts `0001` (or mark
  `0001` `Superseded` without naming a replacement), then ask Claude to run
  `adr-cleanup` — expected: it flags the contradiction or the dangling
  status, proposes a fix and a regenerated `INDEX.md`, and applies nothing
  on its own.
- Ask Claude to "improve the architecture" — expected: `improve-architecture`
  writes an HTML report to the OS temp directory (**never into the fixture**),
  summarises the three strongest candidates in the reply, and stops there.
  **The test that matters**: it must not touch a single source file before you
  pick one. A candidate contradicting an `Accepted` ADR should be listed with
  the conflict named, not silently omitted.
- Ask Claude to "write a commit message" — expected: the
  `commit-message-format` skill (subject/body conventions, no AI-attribution
  trailers) from `common`. On the `project-type-none` project below, the same
  skill should appear, since it is common to every profile.
- Ask Claude to start a new piece of work — expected: the `git-workflow-app`
  skill fires from this profile and **proposes** a branch name of the form
  `<type>/<slug>` rather than asking for one blind. Ask instead for tests on
  code that already shipped: it must land on `test/`, not `chore/`. Neither
  happens on the `project-type-none` project below.
- Ask Claude to change something while `HEAD` is on `main` — expected: it
  proposes a branch and a name *before* editing, not at commit time. Then ask
  it to commit straight onto `main` anyway — expected: the `git-workflow-app`
  *rule* refuses without the skill being loaded, and the `git-branch-guard`
  hook denies the `git commit` call outright even if the rule is ignored.
  Check the hook stays silent on a feature branch: it must print nothing at
  all when the commit is legitimate.

## project-type-none

```
python -m tools.sync sync project-type-none --toolkit-root . --project-dir <a scratch copy>
```

Expected: no docs discipline at all. Ask for a feature — Claude shouldn't
mention requirements or decisions. Then check the choice-group is enforced:
syncing `project-type-app` into the same project must fail, naming the conflict.

## context-quality

```
python -m tools.sync sync context-quality --toolkit-root . --project-dir demo/project-type-app-project
```

- `init-project-context` — expected: an `AGENTS.md` following the fixed
  skeleton, under 150 lines, and a `CLAUDE.md` reduced to `@AGENTS.md`.
- Break it on purpose: add a `| \`notarealcommand\` |` row to the Commands
  table, or point at a `docs/` file that doesn't exist. Open a new session —
  `context-check.sh` should name exactly that. Revert it: silence.

## stacks (desktop architecture)

`detect` now reads each stack's `detect:` markers straight from the manifest
(instead of a second, hand-kept list), so it needs `--toolkit-root` too:

```
python -m tools.sync detect --toolkit-root . --project-dir demo/python-tool
python -m tools.sync sync tech-stack-python --toolkit-root . --project-dir demo/python-tool
```

Expected: `detect` suggests `tech-stack-python`. Then ask "I want to build a
desktop app for this" *before* syncing any stack — the
`desktop-app-architecture` skill from `common` should tour the three
branches, ask what matters, and hand off with an explicit sync command
rather than answering the structural question itself.

The other three tech-stacks and the frontend-design plugin have their own
minimal fixtures, one marker file each:

```
python -m tools.sync detect --toolkit-root . --project-dir demo/go-tool
python -m tools.sync detect --toolkit-root . --project-dir demo/rust-tool
python -m tools.sync detect --toolkit-root . --project-dir demo/dotnet-tool
python -m tools.sync detect --toolkit-root . --project-dir demo/frontend-design-tool
```

Expected: `tech-stack-go`, `tech-stack-rust`, `tech-stack-dotnet` and
`tech-stack-frontend-design` respectively. `sync <id> --toolkit-root .
--project-dir demo/<fixture>` works the same way as the Python example
above for each.

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
