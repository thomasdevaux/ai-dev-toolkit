# Toolkit self-sync SessionStart hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any project (including a brand-new empty one) surface, at
Claude Code session start, whether it's onboarded onto `ai-dev-toolkit`
and whether its already-synced blocks have drifted — without a human
manually locating or cloning the toolkit checkout.

**Architecture:** A new read-only `python -m tools.sync status`
subcommand reuses the existing diff engine (`plan_file_changes`,
`diff_settings`) plus `detect_stacks` to report drift/missing-baseline
info for a project. A new bash `SessionStart` hook script
(`self-check/hooks/toolkit-drift-check.sh`) resolves the toolkit checkout
(env override, or an auto-cloned/pulled local cache with a 1h pull
throttle) and calls that subcommand, printing the report as session
context. Two manifest entries (`toolkit-self-check` at project/baseline
scope, `toolkit-self-check-user` at user/optional scope) distribute the
same script so it fires both per-project and — critically for the
empty-project case — on every session regardless of whether the current
project has been synced yet.

**Tech Stack:** Python 3.12 (`tools/sync`), pytest, Bash (Git Bash on
Windows, matching the existing `remind-testing-policy.sh` hook), YAML
manifest.

## Global Constraints

- Platform is Windows for all users today; the hook must be a `.sh`
  script runnable under Git Bash, no PowerShell — matches
  `process/light/hooks/remind-testing-policy.sh`'s existing convention.
- The hook must never block or fail session start: any resolution
  failure (offline, git missing, clone/pull error) is caught, a warning
  is printed, and the script exits `0`.
- `status` never writes anything — it only reads `.toolkit-sync-state`,
  `sync-manifest.yaml`, and the project's `.claude/` tree.
- The toolkit remote URL default lives in the hook script itself
  (`https://github.com/thomasdevaux/ai-dev-toolkit.git`), overridable via
  `AI_DEV_TOOLKIT_REMOTE`; `AI_DEV_TOOLKIT_ROOT` bypasses cloning
  entirely when set. No per-developer config is required by default.
- Network pulls are throttled to at most once per hour per cache
  directory, tracked via a timestamp file.

---

### Task 1: `python -m tools.sync status` subcommand

**Files:**
- Create: `tools/sync/status.py`
- Modify: `tools/sync/cli.py`
- Test: `tests/tools/sync/test_status.py`

**Interfaces:**
- Consumes: `load_manifest(toolkit_root: Path) -> dict[str, SyncEntry]`
  from `tools/sync/manifest.py`; `load_state(claude_dir: Path) ->
  SyncState` from `tools/sync/state.py`; `plan_file_changes(source_root:
  Path, target_root: Path) -> list[FileChange]`,
  `_resolve_target(claude_dir: Path, target: str) -> Path` from
  `tools/sync/sync.py`; `load_settings(path: Path) -> dict`,
  `merge_patch(existing: dict, patch: dict) -> dict`,
  `diff_settings(existing: dict, merged: dict) -> str | None` from
  `tools/sync/settings_patch.py`; `detect_stacks(project_dir: Path) ->
  list[str]` from `tools/sync/detect.py`.
- Produces: `build_status_report(toolkit_root: Path, claude_dir: Path,
  project_dir: Path) -> str` — the function Task 2's `status` CLI
  subcommand calls, and the one covered by this task's tests.

- [ ] **Step 1: Write the failing tests for `build_status_report`**

Create `tests/tools/sync/test_status.py`:

```python
import json
from pathlib import Path

from tools.sync.status import build_status_report

MANIFEST = """
- id: common-rules
  type: file
  source: common
  target: .claude/
  scope: project
  tier: baseline

- id: gitlab
  type: official-plugin
  plugin_ref: "gitlab@claude-plugins-official"
  scope: project
  tier: baseline
  settings_patch:
    enabledPlugins:
      "gitlab@claude-plugins-official": true

- id: stacks-nodejs
  type: file
  source: stacks/nodejs
  target: .claude/
  scope: project
  tier: stack
  detect: ["package.json"]
"""


def _make_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    toolkit_root.mkdir()
    (toolkit_root / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    common_dir = toolkit_root / "common" / "rules"
    common_dir.mkdir(parents=True)
    (common_dir / "style.md").write_text("# style\n", encoding="utf-8")
    (toolkit_root / "stacks" / "nodejs").mkdir(parents=True)
    return toolkit_root


def test_status_reports_missing_baseline_on_empty_project(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[common-rules] recommended (baseline), not yet synced" in report
    assert "[gitlab] recommended (baseline), not yet synced" in report


def test_status_reports_up_to_date_entry(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    (claude_dir / "rules").mkdir(parents=True)
    (claude_dir / "rules" / "style.md").write_text("# style\n", encoding="utf-8")
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc123",
                "files": {"rules/style.md": "irrelevant"},
                "entries": {"common-rules": {"scope": "project", "tier": "baseline"}},
            }
        ),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[common-rules] up to date" in report
    assert "[common-rules] recommended" not in report


def test_status_reports_drift_on_changed_file(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    (claude_dir / "rules").mkdir(parents=True)
    (claude_dir / "rules" / "style.md").write_text("# stale content\n", encoding="utf-8")
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc123",
                "files": {"rules/style.md": "irrelevant"},
                "entries": {"common-rules": {"scope": "project", "tier": "baseline"}},
            }
        ),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[common-rules] drift: 1 file(s) changed" in report


def test_status_reports_drift_on_changed_settings(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(json.dumps({}), encoding="utf-8")
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc123",
                "files": {},
                "entries": {"gitlab": {"scope": "project", "tier": "baseline"}},
            }
        ),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[gitlab] drift: settings changed" in report


def test_status_reports_detected_stacks(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "package.json").write_text("{}", encoding="utf-8")
    claude_dir = project_dir / ".claude"

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "detected stack(s), suggested for review (not synced automatically):" in report
    assert "  - nodejs" in report
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/tools/sync/test_status.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.sync.status'`

- [ ] **Step 3: Implement `tools/sync/status.py`**

```python
"""Read-only report of a project's sync status: drift on entries already
recorded in .toolkit-sync-state, baseline/choice-group entries not yet
synced, and detected-but-unsynced stacks. Never writes anything — reuses
the same diff engine sync_entries() uses to decide what it would change,
without applying any of it."""
from __future__ import annotations

from pathlib import Path

from .detect import detect_stacks
from .diffing import plan_file_changes
from .manifest import SyncEntry, load_manifest
from .settings_patch import diff_settings, load_settings, merge_patch
from .state import SyncState, load_state
from .sync import _resolve_target


def _entry_drift(entry: SyncEntry, toolkit_root: Path, claude_dir: Path) -> str | None:
    file_changes = []
    if entry.type == "file":
        source_root = toolkit_root / entry.source
        target_root = _resolve_target(claude_dir, entry.target)
        file_changes = plan_file_changes(source_root, target_root)

    settings_diff = None
    if entry.settings_patch:
        settings_path = claude_dir / "settings.json"
        existing_settings = load_settings(settings_path)
        merged_settings = merge_patch(existing_settings, entry.settings_patch)
        settings_diff = diff_settings(existing_settings, merged_settings)

    if not file_changes and not settings_diff:
        return None

    detail = []
    if file_changes:
        detail.append(f"{len(file_changes)} file(s) changed")
    if settings_diff:
        detail.append("settings changed")
    return ", ".join(detail)


def _synced_lines(manifest: dict[str, SyncEntry], state: SyncState, toolkit_root: Path, claude_dir: Path) -> list[str]:
    lines = []
    for entry_id in sorted(state.entries):
        if entry_id not in manifest:
            lines.append(f"[{entry_id}] no longer in manifest")
            continue
        drift = _entry_drift(manifest[entry_id], toolkit_root, claude_dir)
        if drift is None:
            lines.append(f"[{entry_id}] up to date")
        else:
            lines.append(f"[{entry_id}] drift: {drift}")
    return lines


def _missing_lines(manifest: dict[str, SyncEntry], state: SyncState) -> list[str]:
    lines = []
    for entry_id in sorted(manifest):
        if entry_id in state.entries:
            continue
        entry = manifest[entry_id]
        if entry.tier == "baseline" or entry.tier.startswith("choice-group:"):
            lines.append(f"[{entry_id}] recommended ({entry.tier}), not yet synced")
    return lines


def _stack_lines(project_dir: Path) -> list[str]:
    stacks = detect_stacks(project_dir)
    if not stacks:
        return []
    lines = ["detected stack(s), suggested for review (not synced automatically):"]
    lines.extend(f"  - {stack}" for stack in stacks)
    return lines


def build_status_report(toolkit_root: Path, claude_dir: Path, project_dir: Path) -> str:
    manifest = load_manifest(toolkit_root)
    state = load_state(claude_dir)

    lines: list[str] = []
    lines.extend(_synced_lines(manifest, state, toolkit_root, claude_dir))
    lines.extend(_missing_lines(manifest, state))
    lines.extend(_stack_lines(project_dir))

    if not lines:
        return "toolkit status: nothing synced, nothing recommended, no stacks detected."
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/tools/sync/test_status.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Wire the `status` subcommand into the CLI**

In `tools/sync/cli.py`, add the import and the new command function next
to `_cmd_detect`:

```python
from .status import build_status_report
```

```python
def _cmd_status(args: argparse.Namespace) -> int:
    toolkit_root = Path(args.toolkit_root).resolve()
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()
    claude_dir = project_dir / ".claude"
    try:
        report = build_status_report(toolkit_root, claude_dir, project_dir)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(report)
    return 0
```

And register the subparser in `build_parser`, right after the
`detect_parser` block:

```python
    status_parser = subparsers.add_parser("status", help="report sync drift and unsynced baseline/stack entries")
    status_parser.add_argument("--toolkit-root", required=True, help="path to the toolkit checkout")
    status_parser.add_argument("--project-dir", help="target project directory (default: cwd)")
    status_parser.set_defaults(func=_cmd_status)
```

- [ ] **Step 6: Manually verify the CLI end to end**

Run:

```bash
python -m tools.sync status --toolkit-root . --project-dir .
```

Expected: prints `[common-rules] recommended (baseline), not yet synced`
and similar lines for the other baseline/choice-group entries in this
repo's own `sync-manifest.yaml`, since this repo's own `.claude/` isn't
toolkit-managed (per `AGENTS.md`, this repo doesn't sync its own
blocks).

- [ ] **Step 7: Run the full test suite and commit**

Run: `python -m pytest tests/tools/sync -q`
Expected: all tests pass (15 total: 10 existing + 5 new)

```bash
git add tools/sync/status.py tools/sync/cli.py tests/tools/sync/test_status.py
git commit -m "Add python -m tools.sync status subcommand

Read-only report of drift on already-synced entries plus
baseline/choice-group entries and detected stacks not yet synced,
reusing the existing diff engine without writing anything."
```

---

### Task 2: `toolkit-self-check` hook block

**Files:**
- Create: `self-check/hooks/toolkit-drift-check.sh`
- Modify: `sync-manifest.yaml`
- Modify: `docs/architecture.md`
- Modify: `docs/user-guide.md`

**Interfaces:**
- Consumes: `python -m tools.sync status --toolkit-root <path>
  --project-dir <path>` (Task 1's CLI entry point) — the hook script's
  only Python-facing interface.
- Produces: nothing consumed by later tasks — this is the last task in
  the plan.

- [ ] **Step 1: Write the hook script**

Create `self-check/hooks/toolkit-drift-check.sh`:

```bash
#!/bin/bash
# SessionStart hook: resolves an ai-dev-toolkit checkout (env override,
# or an auto-cloned/pulled local cache) and prints this project's
# `tools.sync status` report as session context. Read-only and
# never blocks session start: any resolution failure is caught, a
# warning is printed instead, and the script always exits 0.
set -u

DEFAULT_REMOTE="https://github.com/thomasdevaux/ai-dev-toolkit.git"
REMOTE="${AI_DEV_TOOLKIT_REMOTE:-$DEFAULT_REMOTE}"
CACHE_DIR="$HOME/.cache/ai-dev-toolkit"
PULL_INTERVAL_SECONDS=3600

resolve_toolkit_root() {
    if [ -n "${AI_DEV_TOOLKIT_ROOT:-}" ]; then
        printf '%s\n' "$AI_DEV_TOOLKIT_ROOT"
        return 0
    fi

    if [ ! -d "$CACHE_DIR/.git" ]; then
        if ! git clone --quiet "$REMOTE" "$CACHE_DIR" >/dev/null 2>&1; then
            return 1
        fi
        date +%s > "$CACHE_DIR/.last-pull"
        printf '%s\n' "$CACHE_DIR"
        return 0
    fi

    local stamp_file="$CACHE_DIR/.last-pull"
    local now last=0
    now="$(date +%s)"
    if [ -f "$stamp_file" ]; then
        last="$(cat "$stamp_file")"
    fi
    if [ "$((now - last))" -ge "$PULL_INTERVAL_SECONDS" ]; then
        git -C "$CACHE_DIR" pull --ff-only --quiet >/dev/null 2>&1
        printf '%s\n' "$now" > "$stamp_file"
    fi

    printf '%s\n' "$CACHE_DIR"
    return 0
}

TOOLKIT_ROOT="$(resolve_toolkit_root)"
if [ -z "$TOOLKIT_ROOT" ] || [ ! -f "$TOOLKIT_ROOT/sync-manifest.yaml" ]; then
    echo "toolkit-drift-check: could not resolve an ai-dev-toolkit checkout (tried '$TOOLKIT_ROOT'); skipping drift check this session."
    exit 0
fi

echo "toolkit-drift-check: using toolkit checkout at $TOOLKIT_ROOT"
(cd "$TOOLKIT_ROOT" && python -m tools.sync status --toolkit-root "$TOOLKIT_ROOT" --project-dir "$CLAUDE_PROJECT_DIR") || true
exit 0
```

- [ ] **Step 2: Make it executable and verify it runs against a local fake remote**

This avoids hitting the real GitHub remote in verification. From the
toolkit checkout root:

```bash
chmod +x self-check/hooks/toolkit-drift-check.sh

# Set up a throwaway bare repo to stand in for the real remote:
rm -rf /tmp/fake-toolkit-remote.git /tmp/fake-toolkit-cache /tmp/fake-project
git clone --quiet --bare . /tmp/fake-toolkit-remote.git

# First run: cache doesn't exist yet, must clone.
mkdir -p /tmp/fake-project
AI_DEV_TOOLKIT_REMOTE=/tmp/fake-toolkit-remote.git \
HOME=/tmp/fake-toolkit-home \
CLAUDE_PROJECT_DIR=/tmp/fake-project \
bash self-check/hooks/toolkit-drift-check.sh
```

Expected: prints `toolkit-drift-check: using toolkit checkout at
/tmp/fake-toolkit-home/.cache/ai-dev-toolkit`, followed by a `status`
report listing this repo's baseline entries as `recommended ...,  not
yet synced` (since `/tmp/fake-project` has no `.claude/`).

Run it a second time immediately:

```bash
AI_DEV_TOOLKIT_REMOTE=/tmp/fake-toolkit-remote.git \
HOME=/tmp/fake-toolkit-home \
CLAUDE_PROJECT_DIR=/tmp/fake-project \
bash self-check/hooks/toolkit-drift-check.sh
```

Expected: same report, and `git -C
/tmp/fake-toolkit-home/.cache/ai-dev-toolkit log -1` shows no new
fetch/pull happened (the throttle skipped it — confirm by checking
`/tmp/fake-toolkit-home/.cache/ai-dev-toolkit/.last-pull`'s timestamp is
unchanged between the two runs).

Clean up:

```bash
rm -rf /tmp/fake-toolkit-remote.git /tmp/fake-toolkit-cache /tmp/fake-toolkit-home /tmp/fake-project
```

- [ ] **Step 3: Add the two manifest entries**

In `sync-manifest.yaml`, append after the last existing entry:

```yaml
- id: toolkit-self-check
  type: file
  source: self-check
  target: .claude/
  scope: project
  tier: baseline
  settings_patch:
    hooks:
      SessionStart:
        - hooks:
            - type: command
              command: "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/toolkit-drift-check.sh"

- id: toolkit-self-check-user
  type: file
  source: self-check
  target: ~/.claude/
  scope: user
  tier: optional
  settings_patch:
    hooks:
      SessionStart:
        - hooks:
            - type: command
              command: "\"$HOME\"/.claude/hooks/toolkit-drift-check.sh"
```

Note the two entries use different `command` paths: the project-scope
entry's hook ends up at `<project>/.claude/hooks/...` (referenced via
`$CLAUDE_PROJECT_DIR`, matching `process-light`'s existing convention),
while the user-scope entry's hook ends up at `~/.claude/hooks/...`
(referenced via `$HOME`, since it must resolve the same way regardless
of which project the session is in).

- [ ] **Step 4: Verify the manifest loads and the audit passes**

Run:

```bash
python -c "from tools.sync.manifest import load_manifest; from pathlib import Path; m = load_manifest(Path('.')); print('toolkit-self-check' in m, 'toolkit-self-check-user' in m)"
```

Expected: `True True`

Run: `python -m tools.audit --toolkit-root .`
Expected: `No issues found.`

- [ ] **Step 5: Verify a project-scope sync places and registers the hook correctly**

```bash
rm -rf /tmp/fake-sync-project
mkdir -p /tmp/fake-sync-project
python -m tools.sync sync toolkit-self-check --toolkit-root . --project-dir /tmp/fake-sync-project --yes
cat /tmp/fake-sync-project/.claude/settings.json
ls -l /tmp/fake-sync-project/.claude/hooks/toolkit-drift-check.sh
rm -rf /tmp/fake-sync-project
```

Expected: `settings.json` contains a `hooks.SessionStart` entry running
`"$CLAUDE_PROJECT_DIR"/.claude/hooks/toolkit-drift-check.sh`, and the
hook file is present and executable (`-rwxr-xr-x` or equivalent).

- [ ] **Step 6: Document the new block**

In `docs/architecture.md`, add a short paragraph after the "Blocks and
the manifest" section's existing block-source list, noting `self-check/`
as a fifth top-level block-source location alongside `common/`,
`process/<variant>/`, `stacks/<topic>/`, and `user-tools/<topic>/`, and
describing the project/user dual-entry pattern this block uses (pointing
at the existing "mirrored entry" convention already documented for a
stack + its official-plugin dependency).

In `docs/user-guide.md`, add a short section describing the one-time,
per-developer setup:

```
python -m tools.sync sync toolkit-self-check-user --user --toolkit-root <checkout> --yes
```

and what happens afterward: every Claude Code session, in any project,
prints a sync-status report at start; if it shows missing baseline
entries or drift, ask Claude to run the sync and it will (with your
confirmation) run the corresponding `python -m tools.sync sync` command
itself.

- [ ] **Step 7: Run the full test suite and commit**

Run: `python -m pytest tests/tools/sync -q && python -m tools.audit --toolkit-root .`
Expected: all tests pass, audit reports `No issues found.`

```bash
git add self-check/hooks/toolkit-drift-check.sh sync-manifest.yaml docs/architecture.md docs/user-guide.md
git commit -m "Add toolkit-self-check SessionStart hook block

Resolves the toolkit checkout (env override or an auto-cloned/pulled
throttled local cache) and reports sync status at session start, at
both project (baseline) and user (optional, one-time) scope so the
empty-project case is covered without a manual bootstrap step."
```
