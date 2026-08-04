# Design: self-syncing SessionStart hook for `ai-dev-toolkit`

## Problem

Adopting this toolkit in a consumer project today requires a human to
manually clone `ai-dev-toolkit`, `cd` into it, and run
`python -m tools.sync sync <ids> --toolkit-root <checkout> --project-dir
<path>`. There's no way to bootstrap a brand-new, empty project directly
from inside that project, and no ongoing signal when a project's synced
`.claude/` content has drifted from the manifest (new baseline entries
added, existing blocks changed upstream, etc).

## Goal

Let a developer open Claude Code in any project — including a brand-new
empty one — and have the session itself surface: "this project isn't
onboarded yet" or "these already-synced blocks are stale", then offer to
run the sync, with the developer's consent, without them ever having to
locate or clone the toolkit checkout by hand.

Target platform: Windows, for all users today. Claude Code hooks already
run through Git Bash on this platform (see the existing
`process/light/hooks/remind-testing-policy.sh`), so the new hook follows
the same convention — a `.sh` script, `$HOME`-relative paths, no
PowerShell.

## Architecture

Three additions to this repo:

### 1. Auto-resolution of the toolkit checkout

A resolution block at the top of the new hook script. No new Python
module — this logic only needs to run once per hook invocation, in bash.

- If `AI_DEV_TOOLKIT_ROOT` is set (a dev already has a local checkout,
  e.g. someone working on the toolkit itself) → use it as-is, no
  network access.
- Otherwise, resolve to a cache directory: `~/.cache/ai-dev-toolkit`
  (via Git Bash's `$HOME`, which maps to the Windows user profile).
  - If absent: `git clone --quiet "$remote" "$cache_dir"`.
  - If present: `git -C "$cache_dir" pull --ff-only --quiet`, but only
    if the last pull was more than an hour ago (tracked via a timestamp
    file inside the cache dir) — avoids a network round-trip on every
    single session start.
- The remote URL defaults to a value hardcoded in the script
  (`https://github.com/thomasdevaux/ai-dev-toolkit.git` today),
  overridable via `AI_DEV_TOOLKIT_REMOTE`. Because this script is itself
  distributed through `tools/sync`, changing the default in this repo
  and re-syncing the `toolkit-self-check` block propagates the new URL
  to every project and developer — no per-developer config to maintain
  if/when the repo moves.
- Any failure (offline, clone/pull error, git not found) is caught: the
  script prints a one-line warning and exits `0`. The hook must never
  block or fail a session start.

### 2. `python -m tools.sync status`

A new subcommand, alongside `sync` and `detect`, that reports without
writing anything:

- Loads `.toolkit-sync-state` from the target `.claude/` (empty state if
  the project has never been synced — the brand-new-project case).
- For each entry already recorded in the state: recomputes
  `plan_file_changes` / `diff_settings` against the current manifest
  (reusing the existing `diffing.py` machinery, no new diff logic) and
  reports drift per entry (`up to date` / `N file(s) changed` /
  `settings changed`).
- Reuses `detect_stacks` plus a scan of `baseline` /
  `choice-group:*` manifest entries not yet present in the state, to
  surface "recommended but not yet synced" — the same information
  `detect` gives today, folded into one report.
- Exit code is always `0`; this command is purely informational.

### 3. New manifest block: `toolkit-self-check`

A new block directory (e.g. `self-check/hooks/toolkit-drift-check.sh`),
registered as **two** manifest entries sharing that one source file,
mirroring the existing pattern of a stack + its official-plugin
dependency being two entries over related content:

| id | scope | tier | target | settings_patch |
|---|---|---|---|---|
| `toolkit-self-check` | `project` | `baseline` | `.claude/` | registers the script under `hooks.SessionStart` |
| `toolkit-self-check-user` | `user` | `optional` | `~/.claude/` | same |

- The **project** entry is baseline: every project that syncs the
  baseline gets it, so it's enforced for all contributors going
  forward, not dependent on each developer's personal setup.
- The **user** entry is a one-time, per-developer, opt-in install
  (`sync ... --user`). It's what makes the empty-project case work at
  all: it fires on every Claude Code session regardless of whether the
  current project has any `.claude/` yet, since it lives in
  `~/.claude/settings.json` rather than the project's.
- Both entries point at the same script; the resolution/throttle logic
  in §1 is identical either way.

## Hook behavior

`toolkit-drift-check.sh` (invoked as a `SessionStart` hook):

1. Resolve the toolkit checkout (§1).
2. If resolution failed → print the warning, exit `0`.
3. Otherwise run `python -m tools.sync status --toolkit-root
   <resolved> --project-dir "$CLAUDE_PROJECT_DIR"` and print its output.

That output becomes session context for Claude, the same way
`remind-testing-policy.sh`'s reminder does today. The hook itself never
prompts or writes — it only reports. On seeing a report that shows
missing baseline entries or drifted ones, Claude tells the user and asks
whether to sync now or defer, per the user's explicit instruction that
the hook must inform rather than act unilaterally.

If the user agrees, Claude runs the sync itself:

```
python -m tools.sync sync <ids> --toolkit-root <path already given by the hook's status output> --project-dir . --yes
```

`--yes` is required here, not optional: `sync_entries`'s confirmation
step calls `input()`, which would hang or read EOF when invoked
non-interactively through the Bash tool. Consent was already obtained
conversationally: Claude asking the user via the chat interface before
running the command is the actual confirmation step. `--yes` only skips
the *shell's* redundant second prompt.

## Error handling

- No network / clone or pull fails → hook warns and exits 0; `status`
  is simply not run that session. No project state is touched.
- `status` never mutates anything — the diff engine it reuses
  (`plan_file_changes`, `diff_settings`) is already read-only by
  construction (`sync_entries` is the only caller that writes).
- A project with a corrupted or unreadable `.toolkit-sync-state` should
  behave like a project with no state (empty `SyncState`), consistent
  with `load_state`'s existing behavior for a missing file.

## Testing

- Unit tests for `status` under `tools/sync/tests/` (or wherever the
  existing `sync`/`detect` tests live), covering: empty project (no
  state), fully up-to-date project, and a project with drifted files
  and drifted settings.
- The bash resolution/throttle logic is small enough to verify by
  inspection plus a manual run rather than a dedicated test harness,
  consistent with `remind-testing-policy.sh` today having no test
  coverage of its own.

## Docs

- `docs/user-guide.md`: add the one-time `--user` setup step for a new
  developer's machine, and describe what the hook will do afterward.
- `docs/architecture.md`: document the `toolkit-self-check` block
  alongside the existing four-tier and mirrored-entry conventions it
  reuses.

## Out of scope

- No PowerShell variant of the hook script — Git Bash is confirmed
  sufficient for the existing hook and this one follows suit.
- No packaged/PATH-installed CLI wrapper. The hook script is
  self-contained; there's no need for a separate binary to invoke sync
  from an arbitrary shell outside of a Claude Code session.
- No auto-sync-without-asking mode. Every write still goes through an
  explicit user "yes" surfaced by Claude in-session.
