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


def _missing_lines(manifest: dict[str, SyncEntry], state: SyncState, scope: str = "project") -> tuple[list[str], bool]:
    """Project-scope entries only, by default. A user-scope baseline entry
    (the per-machine install) is missing from ~/.claude, not from this
    project — reporting it here would nag every project on this machine for
    something no project sync can fix."""
    lines = []
    has_missing_baseline = False
    reported_groups: set[str] = set()

    for entry_id in sorted(manifest):
        entry = manifest[entry_id]
        if entry.scope != scope:
            continue

        if entry.tier == "baseline":
            if entry_id not in state.entries:
                has_missing_baseline = True
                lines.append(f"[{entry_id}] recommended (baseline), not yet synced")
            continue

        group = entry.choice_group
        if group is None or group in reported_groups:
            continue
        members = sorted(e.id for e in manifest.values() if e.choice_group == group)
        if any(member in state.entries for member in members):
            continue  # the group is already satisfied by one of its members
        reported_groups.add(group)
        lines.append(f"[choice-group:{group}] pick exactly one, not yet synced: {', '.join(members)}")

    return lines, has_missing_baseline


def _suggested_lines(manifest: dict[str, SyncEntry], state: SyncState, scope: str) -> list[str]:
    """tier: suggested entries not yet synced — listed so a useful block is
    discoverable, never counted as drift and never blocking. tier: optional
    stays deliberately invisible here; that's the only difference between the
    two tiers."""
    pending = [
        manifest[entry_id]
        for entry_id in sorted(manifest)
        if manifest[entry_id].tier == "suggested"
        and manifest[entry_id].scope == scope
        and entry_id not in state.entries
    ]
    if not pending:
        return []
    lines = ["available, not installed (never synced automatically):"]
    for entry in pending:
        detail = f" - {entry.summary}" if entry.summary else ""
        lines.append(f"  - {entry.id}{detail}")
    return lines


def _is_onboardable(project_dir: Path, state: SyncState) -> bool:
    """A scratch folder — no git repo, nothing ever synced — gets a one-line
    mention instead of the full onboarding report. Opening a session anywhere
    to work on a throwaway script must not turn into a sync checklist; the
    common rules such a session needs come from ~/.claude (common-rules-user)
    rather than from a project .claude/ nobody asked for."""
    return (project_dir / ".git").exists() or bool(state.entries)


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

    if not _is_onboardable(project_dir, state):
        return (
            "toolkit: this folder isn't a git repository and has never been synced, "
            "nothing to report. Run 'toolkit-sync sync' here if it becomes a real project."
        )

    lines: list[str] = []
    lines.extend(_synced_lines(manifest, state, toolkit_root, claude_dir))
    missing_lines, has_missing_baseline = _missing_lines(manifest, state)
    lines.extend(missing_lines)
    if has_missing_baseline:
        # Uses the /toolkit-sync wrapper (repo root), not `python -m tools.sync`
        # directly, since this hint is meant to be copy-pasted from any cwd —
        # see toolkit-sync's docstring comment for why that matters.
        lines.append(
            f"hint: run '{toolkit_root}/toolkit-sync sync --toolkit-root {toolkit_root} "
            f"--project-dir {project_dir} --yes' with no entry_ids to sync every "
            "baseline entry above in one go. (on Windows cmd/PowerShell, use "
            f"{toolkit_root}\\toolkit-sync.cmd instead)"
        )
    lines.extend(_stack_lines(project_dir))
    lines.extend(_suggested_lines(manifest, state, scope="project"))

    if not lines:
        return "toolkit status: nothing synced, nothing recommended, no stacks detected."
    return "\n".join(lines)
