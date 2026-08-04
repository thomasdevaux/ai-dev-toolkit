# User guide: adopting this toolkit in your project

For teams syncing this toolkit's conventions into their own project. See
[`vision.md`](vision.md) for why this exists and [`architecture.md`](architecture.md)
for how it works internally.

## Quickstart

```
# from inside a checkout of this repo
python -m tools.sync detect --project-dir /path/to/your/project

# sync every tier:baseline entry in one go — common-rules, its two
# official-plugin dependencies, and the toolkit-self-check hook
python -m tools.sync sync --toolkit-root . --project-dir /path/to/your/project

# pick exactly one process profile
python -m tools.sync sync process-light --toolkit-root . --project-dir /path/to/your/project

# sync whichever stacks tools/sync detect suggested
python -m tools.sync sync stacks-python --toolkit-root . --project-dir /path/to/your/project

# one-time per developer machine: get an automatic onboarding/drift
# report in every Claude Code session, in every project
python -m tools.sync sync toolkit-self-check-user --user --toolkit-root .
```

Each `sync` call prints the files it would create or change (and any
`settings.json` key it would patch) and asks for confirmation before
writing anything. Review the diff, commit the result in your project
like any other change. Re-running the same command later is idempotent
— it reports "nothing to synchronize" if your project already matches.

Running `sync` with no entry IDs, as in the baseline step above, syncs
every `tier: baseline` manifest entry for the target scope at once —
new baseline entries (like `toolkit-self-check` was, when it was added)
are picked up automatically, without updating this Quickstart. Pass
explicit entry IDs (`process-light`, `stacks-python`, …) for anything
that isn't baseline — those always require a deliberate choice.

For the optional per-user statusline: `python -m tools.sync sync
user-statusline --toolkit-root . --user` (see
[`user-tools/statusline/README.md`](../user-tools/statusline/README.md)).

See [`../demo/README.md`](../demo/README.md) for dummy projects to try
this against without touching a real one.

## Automatic drift checks (toolkit-self-check)

The `toolkit-self-check` block's `SessionStart` hook reports, at the
start of every Claude Code session, whether the project is missing any
baseline/choice-group entries or has drifted from what's synced — no
manual toolkit checkout needed. It resolves its own copy:
`AI_DEV_TOOLKIT_ROOT`, if set, is used as-is; otherwise it clones/pulls a
cache at `~/.cache/ai-dev-toolkit` (at most once an hour).

Every project gets the check automatically once it syncs the baseline.
The Quickstart's `toolkit-self-check-user --user` step covers the one
case a project-level hook can't: a brand-new, not-yet-synced project —
install it once per developer machine and it fires in every project,
synced or not.

The report is read-only; it never writes anything. If it shows something
pending, tell Claude to sync it — either the bare `sync` command from the
Quickstart for baseline gaps, or the specific entry id for a
choice-group/stack pick. The deployed hook file is a thin stub: it only
resolves the checkout and hands off to that checkout's own
`tools/hooks/toolkit-drift-check-impl.sh`, so behavior fixes there reach
every project on their next throttled `git pull` — no re-sync needed.
Only changes to the stub's own resolution logic (rare) require one.

## Block catalog

| Manifest id(s) | Tier | Scope | What it is |
| --- | --- | --- | --- |
| `common-rules` | baseline | project | Org-wide rules: security, git workflow, language, process-profile pointer. |
| `gitlab`, `claude-md-management` | baseline | project | Official Anthropic plugins kept as `common`'s dependencies. See [Official plugin catalog](#official-plugin-catalog) below. |
| `process-light` / `process-full` | choice-group:process | project | Mutually exclusive process discipline — pick exactly one. `process-light` also carries the `remind-testing-policy.sh` proof-of-concept `SessionStart` hook. |
| `stacks-python` | stack (`pyproject.toml`, `requirements.txt`, `setup.py`) | project | Python packaging/style rules, `quick-script`/`ship-tool` skills, a `haiku`-pinned quick-fix subagent. |
| `stacks-nodejs`, `frontend-design` | stack (`package.json`) | project | Node.js/web packaging/style rules, `ship-web` skill, plus the official `frontend-design` plugin. |
| `stacks-rust`, `rust-analyzer-lsp` | stack (`Cargo.toml`) | project | Rust packaging/style rules, `ship-rust` skill, a `haiku`-pinned quick-fix subagent, plus the official `rust-analyzer-lsp` plugin. |
| `stacks-embedded-c` | stack (`Makefile`/`CMakeLists.txt` + `.c`/`.h`) | project | MISRA baseline + stricter `src/safety/**` rules, `build-toolchain` skill, an `opus`-pinned safety-review subagent. |
| `stacks-model-based-design` | stack (`*.slx`/`*.mdl`) | project | Model naming/traceability conventions, `check-model-conventions` and `generate-code-review` skills. |
| `user-statusline` | optional | user | The status line shown in every session's prompt (model, context usage, rate limits). |
| `toolkit-self-check` / `toolkit-self-check-user` | baseline / optional | project / user | `SessionStart` hook reporting onboarding/drift status every session. See [Automatic drift checks](#automatic-drift-checks-toolkit-self-check) below. |

Every id above is a literal `sync-manifest.yaml` entry — pass one or
more to `python -m tools.sync sync`. `tools/sync detect` only ever
*suggests* `stack`-tier ids from marker files; nothing syncs without an
explicit command.

## Multi-tech example: an automotive repo

A real automotive project combines firmware, a Simulink model, and a
Python flashing tool in one repo:

```
python -m tools.sync sync --toolkit-root . --project-dir /path/to/automotive-repo
python -m tools.sync sync process-full stacks-embedded-c stacks-model-based-design stacks-python \
  --toolkit-root . --project-dir /path/to/automotive-repo
```

Their scoped rules don't collide because their `paths:` globs are
disjoint — `stacks/embedded-c`'s stricter rule scopes to `src/safety/**`,
`stacks/model-based-design` scopes to `model/**`/`**/*.slx`/`**/*.mdl`,
`stacks/python`'s packaging rule scopes to `pyproject.toml`, and
`common`'s rules are unscoped and apply everywhere on top of the others.
See `../demo/multi-tech-automotive/` for a working example, and run
`python -m tools.audit --toolkit-root .` whenever you add a new block,
to check for `paths:` overlap across every block at once.

## Process profile: full vs. light

`process-light` and `process-full` are a
[choice-group](architecture.md#mutual-exclusion): every project syncs
**exactly one of the two**, alongside whichever `stacks-*` block(s)
match its language. `tools/sync` refuses to sync the second one while
the first is still registered.

- `process-light`: the default, real process discipline for most
  projects. Keeps `README.md`, `docs/architecture.md`,
  `docs/decisions.md`, `docs/user-manual.md`, `docs/developer-guide.md`,
  `docs/build-and-release.md`, and `docs/testing-strategy.md` current;
  tracks features in a flat `docs/requirements.md`; requires at least one
  test on the main path for any non-trivial feature/bugfix (also nudged
  by its `SessionStart` hook); and offers an on-demand `audit-docs` skill
  to check all of the above for staleness.
- `process-full`: reserved for core, critical, or certified projects that
  will eventually need more rigor than `process-light` (e.g. regulatory
  traceability, formal audit trails) — but that extra rigor **hasn't been
  designed yet**. It's currently a stub that just tells Claude to follow
  `process-light`'s rules in the meantime.

If neither is synced yet, `common/rules/process-profile.md` prompts
Claude to ask which one applies before non-trivial work proceeds — the
tool only enforces "not both," not "at least one."

## Official plugin catalog

### common's dependencies: kept vs. dropped

`common`'s baseline depends on two official Anthropic plugins, reviewed
and chosen individually rather than bundled as a fixed set:

| Plugin | Decision | Manifest entry |
| --- | --- | --- |
| `gitlab` | Kept, `tier: baseline` | `gitlab` |
| `claude-md-management` | Kept, `tier: baseline` | `claude-md-management` |

A project that wants some other official plugin installs it directly
(`/plugin install <name>`) without going through this toolkit's sync.
Revisit this list if the team's tooling needs change.

### Per-stack dependencies

Each tech stack that depends on an official plugin carries its own
`tier: stack` entry, synced alongside the stack's file entry (see
[`architecture.md`](architecture.md) for why it's a separate entry
rather than a nested dependency):

| Stack | Official plugin | Manifest entry | `detect` |
| --- | --- | --- | --- |
| `stacks/nodejs` | `frontend-design` | `frontend-design` | `package.json` |
| `stacks/rust` | `rust-analyzer-lsp` | `rust-analyzer-lsp` | `Cargo.toml` |

Sync both ids together to get "installing the stack also installs its
LSP":

```
python -m tools.sync sync stacks-rust rust-analyzer-lsp --toolkit-root . --project-dir .
```

### Installing an official plugin without the sync tool

If you only want one specific official plugin — say, `rust-analyzer-lsp`
on a project that isn't otherwise adopting this toolkit — install it
directly, the plain Claude Code way:

```
/plugin install rust-analyzer-lsp@claude-plugins-official
```

Syncing an `official-plugin` entry through `tools/sync` is just a
convenience that patches `enabledPlugins` for you and pairs it with the
matching stack's rules — it doesn't do anything a direct
`/plugin install` couldn't.

### Pruning stale plugins

Every `sync` run also checks the target `settings.json` for
`enabledPlugins` entries that no `type: official-plugin` entry in
`sync-manifest.yaml` references anymore — regardless of marketplace,
and regardless of whether that entry was ever synced to this project.
It offers to remove each one, plugin by plugin; declining leaves that
plugin as-is and moves on to the next. `--yes` auto-confirms removals
the same way it auto-confirms every other proposed change.

### Adding a new official-plugin entry

1. Add a `type: official-plugin` entry to `sync-manifest.yaml`:
   `plugin_ref: "<name>@claude-plugins-official"`, a `tier` matching
   whatever it supports, and a `settings_patch.enabledPlugins` key
   setting `"<name>@claude-plugins-official": true`.
2. If it supports a specific stack, give it the same `detect` list as
   that stack's own entry, so `tools/sync detect` suggests both together.
3. Add a row to the tables above.

## Enforcing model/effort by task type

Three blocks illustrate a pattern worth reusing: pinning a subagent's
model and effort level to the *task type* it handles, rather than
restricting models per person or team.

- `stacks/embedded-c` ships `agents/safety-review.md`, pinned to a
  stronger model (`opus`) and higher effort (`high`) for safety-critical
  code review, where mistakes are expensive.
- `stacks/python` ships `agents/python-quick-fix.md`, pinned to a lighter
  model (`haiku`) and lower effort (`low`) for small, low-risk fixes,
  where a heavier model would just be slower and more expensive for no
  benefit.
- `stacks/rust` ships `agents/rust-quick-fix.md`, pinned to the same
  lighter model (`haiku`) and lower effort (`low`) for small, low-risk
  Rust fixes, for the same reason.

## Language

Code, comments, commit messages, and all written documentation in this
repo (and any project that syncs `common-rules`) are always written in
English. Conversation with Claude itself can happen in any language —
this rule governs what gets written into a repository, not how you talk
to Claude. See `common/rules/language.md` for the full rule.

## Pointing a project's CLAUDE.md back at this toolkit

Once a project has synced content from this repo, its `CLAUDE.md` should
say so, so a future session (or a new teammate) knows where the
conventions come from and how to check what's current:

```markdown
## Toolkit conventions
This project syncs its conventions from `ai-dev-toolkit`
(<repo-url>), currently at ref `<git-sha-or-tag>`. See
`.claude/.toolkit-sync-state` for exactly which blocks and files are
toolkit-managed. Re-run `python -m tools.sync sync <ids>
--toolkit-root <checkout> --project-dir .` to pick up updates.
```

The ref/state-file pointer is the source of truth for what's synced —
there's no single fixed name to point at instead.
