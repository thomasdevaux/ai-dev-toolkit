# Demo: validating the ai-dev-toolkit blocks

This folder holds dummy sub-projects, just enough fake source to trigger
each block's scoped rules and let you invoke each workflow skill/subagent
for real, without needing an actual project.

All commands below assume you're running them from this repo's root (the
toolkit checkout), passing a `demo/` fixture as `--project-dir`. Nothing
here is destructive: `tools/sync` always shows a diff and asks for
confirmation before writing, so you can dry-run any command below and
answer no.

## common

```
python -m tools.sync sync --toolkit-root . --project-dir demo/process-light-project
```

No entry IDs syncs every `tier: baseline` entry at once. Expected:
`common-rules` writes `.claude/rules/{security,git-workflow,
language,process-profile}.md`; `gitlab` and `claude-md-management` patch
`enabledPlugins` in `.claude/settings.json`; `toolkit-self-check` writes
`.claude/hooks/toolkit-drift-check.sh` and registers it under
`hooks.SessionStart`. Ask Claude to "write a commit message" anywhere in
this repo — the git-workflow and language rules should surface
unprompted, since they're unscoped and load at launch.

## process-light

```
python -m tools.sync sync process-light --toolkit-root . --project-dir demo/process-light-project
```

- Ask Claude to add a small feature anywhere in this repo — expected: the
  process-light rules activate and Claude mentions updating
  `docs/requirements.md`, logging a decision in `docs/decisions.md` if the
  choice is non-obvious, and adding a test on the main path.
- A new session opened in `demo/process-light-project/` should print the
  `remind-testing-policy.sh` `SessionStart` hook's reminder.
- In `demo/process-light-project/`, ask Claude to "audit the docs" —
  expected: the `audit-docs` skill reports `docs/architecture.md`,
  `docs/user-manual.md`, `docs/developer-guide.md`,
  `docs/build-and-release.md`, and `docs/testing-strategy.md` as missing
  (this fixture only ships `README.md`, `docs/decisions.md`, and
  `docs/requirements.md`), and checks the existing `docs/requirements.md`
  and `docs/decisions.md` entries for valid statuses/ids.

## process-full

```
python -m tools.sync sync process-full --toolkit-root . --project-dir demo/process-light-project
```

Run this against a *different* scratch copy of the fixture — `tools/sync`
blocks syncing `process-full` while `process-light` is already registered
in the same project's `.toolkit-sync-state` (that block is itself worth
demonstrating: try both in the same `--project-dir` and confirm the
error). Expected once synced: ask Claude the same "add a small feature"
question as `process-light` above — the `full-process-stub.md` rule
states it is currently just following `process-light`'s rules, since the
extra core/critical/certified-grade rigor hasn't been designed yet.

## stacks-python

```
python -m tools.sync sync stacks-python --toolkit-root . --project-dir demo/python-tool
```

- Open `demo/python-tool/pyproject.toml` and ask Claude to review it —
  expected: the packaging rule activates (its `paths:` matches
  `pyproject.toml`).
- Ask Claude to run `quick-script` on a one-line print script — expected:
  no test/packaging requirement imposed.
- Ask Claude to run `ship-tool` on `demo/python-tool/` — expected: Claude
  states it needs to check lint, format, tests, packaging, and build
  before calling it done.
- Ask Claude to fix a small typo in `demo/python-tool/demo_flash_tool/cli.py`
  — expected: the `python-quick-fix` subagent (pinned to `haiku`/`low`
  effort) handles it.

## stacks-nodejs

```
python -m tools.sync sync stacks-nodejs frontend-design --toolkit-root . --project-dir demo/node-web
```

- Open `demo/node-web/index.ts` and ask Claude to review it — expected:
  the web-style rule activates for the `.ts` file.
- Ask Claude to run `ship-web` on `demo/node-web/` — expected: Claude
  states it needs eslint, tsc, tests, and build to pass.

## stacks-rust

```
python -m tools.sync sync stacks-rust rust-analyzer-lsp --toolkit-root . --project-dir demo/rust-tool
```

- Open `demo/rust-tool/Cargo.toml` and ask Claude to review it —
  expected: the packaging rule activates (its `paths:` matches
  `Cargo.toml`).
- Open `demo/rust-tool/src/main.rs` and ask Claude to review it —
  expected: the style rule activates for the `.rs` file.
- Ask Claude to fix the typo in `greet()`'s format string (`"Helllo"`) in
  `demo/rust-tool/src/main.rs` — expected: the `rust-quick-fix` subagent
  (pinned to `haiku`/`low` effort) handles it.

## stacks-embedded-c

```
python -m tools.sync sync stacks-embedded-c --toolkit-root . --project-dir demo/embedded-c
```

- Open `demo/embedded-c/main.c` and ask Claude to review it — expected:
  only the MISRA rule activates (this file is outside `src/safety/**`).
- Open `demo/embedded-c/src/safety/brake_limit.c` and ask Claude to
  review it — expected: **both** the MISRA and safety-critical rules
  activate, and Claude should suggest invoking the `safety-review`
  subagent (pinned to `opus`/`high` effort) before merging.
- Ask Claude to run `build-toolchain` on `demo/embedded-c/` — expected: a
  build/static-analysis/flash/test procedure, noting the safety-critical
  check for `src/safety/**`.

## stacks-model-based-design

```
python -m tools.sync sync stacks-model-based-design --toolkit-root . --project-dir demo/model-based-design
```

- Open `demo/model-based-design/model/brake_controller.slx` — expected:
  the mbd-conventions rule activates (path matches `model/**` and
  `**/*.slx`).
- Ask Claude to run `check-model-conventions` on
  `demo/model-based-design/model/` — expected: it checks naming,
  annotations, and config location.
- Ask Claude to run `generate-code-review` on
  `demo/model-based-design/generated/brake_controller.c` against
  `demo/model-based-design/model/brake_controller.slx` — expected: it
  cross-checks the generated C against the model, not just C style.

## Detection

```
python -m tools.sync detect --project-dir demo/multi-tech-automotive
```

Expected: suggests `model-based-design` and `python` (this fixture has no
`Makefile`/`CMakeLists.txt`, so `embedded-c` isn't suggested even though
it has `.c` files under `src/` — sync it manually below to exercise it
anyway).

## Combined multi-tech example: `demo/multi-tech-automotive/`

```
python -m tools.sync sync --toolkit-root . --project-dir demo/multi-tech-automotive
python -m tools.sync sync process-full stacks-embedded-c stacks-model-based-design stacks-python \
  --toolkit-root . --project-dir demo/multi-tech-automotive
```

This mirrors a real automotive repo: embedded C firmware, a Simulink
model, and a Python flashing tool in one project.

- `src/safety/watchdog.c` → MISRA + safety-critical rules + `safety-review`
  subagent.
- `src/diagnostics.c` → MISRA rule only.
- `model/engine_map.slx` → mbd-conventions rule.
- `tools/pyproject.toml` → packaging rule.

Expected: no `paths:` glob collides across blocks — `src/safety/**`,
`model/**` / `**/*.slx`, and `pyproject.toml` are disjoint, so each file
triggers exactly the rules meant for its tech, and `common`'s unscoped
rules apply throughout. Run `python -m tools.audit --toolkit-root .` to
confirm this programmatically.

## user-statusline

```
python -m tools.sync sync user-statusline --toolkit-root . --user
```

This is `scope: user`, so it targets `~/.claude/` regardless of
`--project-dir` — see
[`user-tools/statusline/README.md`](../user-tools/statusline/README.md).

## Scaffolding a new block

```
python -m tools.audit --toolkit-root .
```

Use [`templates/new-block/SKILL.md`](../templates/new-block/SKILL.md) to
scaffold a throwaway block (e.g. a `stacks/go` skeleton) and confirm
`tools/audit` reports no `paths:` overlap, size, or choice-group issues
against the real blocks. Delete the throwaway block afterward unless you
actually want to keep it — don't commit a demo scaffold.

**Whenever you rename or delete a block**, run `python -m tools.audit
--toolkit-root .` before committing, and grep this file, `README.md`,
and `CONTRIBUTING.md` for stale mentions of the old block name — there's
no CI enforcing this yet, so it only catches drift if you actually run it.
