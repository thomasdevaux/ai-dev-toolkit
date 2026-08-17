"""Read-only report of a project's sync status: drift on entries already
recorded in .toolkit-sync-state, baseline/choice-group entries not yet
synced, and detected-but-unsynced stacks. Never writes anything — reuses
the same diff engine sync_entries() uses to decide what it would change,
without applying any of it."""
from __future__ import annotations

from pathlib import Path

from .detect import detect_stacks
from .diffing import plan_file_changes
from .manifest import SyncEntry, baseline_entry_ids, load_manifest, official_plugin_refs, resolve_shared_files
from .settings_patch import diff_settings, load_settings, merge_patch, stale_plugin_refs
from .state import SyncState, is_onboardable_project, load_state
from .sync import _resolve_target

# Directories under .claude/ (or ~/.claude/) the toolkit ever writes into.
# Anything found here that isn't in state.files came from somewhere else —
# a hand-installed skill, a marketplace plugin's own files, a local hook.
_MANAGED_DIRS = ("skills", "agents", "commands", "hooks", "rules")


def _entry_drift(entry: SyncEntry, toolkit_root: Path, claude_dir: Path) -> str | None:
    file_changes = []
    if entry.type == "file":
        source_root = toolkit_root / entry.source
        target_root = _resolve_target(claude_dir, entry.target)
        file_changes = plan_file_changes(
            source_root, target_root, resolve_shared_files(entry, toolkit_root)
        )

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


def default_sync_entry_ids(
    manifest: dict[str, SyncEntry],
    state: SyncState,
    toolkit_root: Path,
    claude_dir: Path,
    scope: str,
) -> list[str]:
    """The entry set `sync` touches when called with no explicit entry_ids:
    every tier:baseline entry for the scope (the existing onboarding
    default), plus every entry already recorded in `state` — any tier —
    whose files or settings_patch have drifted. Without the second half, a
    'Sync now' answer never clears drift on an already-adopted
    choice-group/tech-stack/suggested entry (e.g. project-type-app picked up
    a source change): the CLI's own default silently ignored it, no matter
    how many times the question got answered. Adopting a *new*
    non-baseline entry still needs an explicit id (or `switch`, for a
    choice-group) — this only re-syncs what's already there."""
    ids = set(baseline_entry_ids(manifest, scope))
    for entry_id, recorded in state.entries.items():
        if recorded.get("scope") != scope:
            continue
        entry = manifest.get(entry_id)
        if entry is None:
            continue
        if _entry_drift(entry, toolkit_root, claude_dir) is not None:
            ids.add(entry_id)
    return sorted(ids)


def _synced_lines(
    manifest: dict[str, SyncEntry],
    state: SyncState,
    toolkit_root: Path,
    claude_dir: Path,
    include_clean: bool = True,
) -> list[str]:
    """`include_clean=False` drops the '[x] up to date' lines. The hook uses it:
    confirming every session that nothing changed is the noise D-08 forbids,
    while `tools.sync status` run deliberately should still show the whole
    picture — including what it checked and found fine."""
    lines = []
    for entry_id in sorted(state.entries):
        if entry_id not in manifest:
            lines.append(f"[{entry_id}] no longer in manifest")
            continue
        drift = _entry_drift(manifest[entry_id], toolkit_root, claude_dir)
        if drift is None:
            if include_clean:
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
    discoverable, never counted as drift and never blocking."""
    pending = [
        manifest[entry_id]
        for entry_id in sorted(manifest)
        if manifest[entry_id].tier == "suggested"
        and manifest[entry_id].scope == scope
        and entry_id not in state.entries
        and entry_id not in state.dismissed
    ]
    if not pending:
        return []
    lines = ["available, not installed (never synced automatically):"]
    for entry in pending:
        detail = f" - {entry.summary}" if entry.summary else ""
        lines.append(f"  - {entry.id}{detail}")
    return lines


def _unmanaged_file_entries(claude_dir: Path, state: SyncState) -> list[str]:
    """Top-level items under a toolkit-managed directory (a skill's folder, a
    lone hook script, ...) that the sync state never wrote. Reported whole
    rather than file-by-file: 'skills/frontend-tricks/' says more at a glance
    than every file inside it."""
    found = []
    for dirname in _MANAGED_DIRS:
        base = claude_dir / dirname
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir():
                relpaths = {
                    str(path.relative_to(claude_dir)).replace("\\", "/")
                    for path in child.rglob("*")
                    if path.is_file()
                }
                label = str(child.relative_to(claude_dir)).replace("\\", "/") + "/"
            else:
                relpaths = {str(child.relative_to(claude_dir)).replace("\\", "/")}
                label = next(iter(relpaths))
            if relpaths and not (relpaths & set(state.files)):
                found.append(label)
    return found


def _unmanaged_lines(claude_dir: Path, manifest: dict[str, SyncEntry], state: SyncState) -> list[str]:
    """Things sitting in this .claude/ that the toolkit never put there and
    never touches: a hand-installed skill, a marketplace plugin outside the
    manifest's own catalog. Purely informational — never a sync target,
    never pruned, never nagged about at session start."""
    settings = load_settings(claude_dir / "settings.json")
    foreign_plugins = stale_plugin_refs(settings, official_plugin_refs(manifest))
    foreign_files = _unmanaged_file_entries(claude_dir, state)
    if not foreign_plugins and not foreign_files:
        return []
    lines = ["installed outside the toolkit (not managed, never touched by sync):"]
    lines.extend(f"  - plugin: {ref}" for ref in foreign_plugins)
    lines.extend(f"  - {relpath}" for relpath in foreign_files)
    return lines


def _stack_lines(project_dir: Path, toolkit_root: Path, state: SyncState) -> list[str]:
    """A stack whose block is already synced — or explicitly dismissed — isn't
    'suggested for review' any more. Without these filters the report
    re-suggests tech-stack-python on every session of every Python project
    that already has it, or never wanted it — and this is one of the two
    sections the hook keeps printing ambiently, so a stale suggestion here is
    a permanent one."""
    stacks = [
        entry_id
        for entry_id in detect_stacks(project_dir, toolkit_root)
        if entry_id not in state.entries and entry_id not in state.dismissed
    ]
    if not stacks:
        return []
    lines = ["detected stack(s), suggested for review (not synced automatically):"]
    lines.extend(f"  - {stack}" for stack in stacks)
    return lines


def build_status_report(
    toolkit_root: Path,
    claude_dir: Path,
    project_dir: Path,
    for_hook: bool = False,
    scope: str = "project",
) -> str:
    """`for_hook=True` returns only what's worth interrupting a session for:
    drift, un-synced baseline/choice-group entries, and the two discovery
    sections (suggested blocks, detected stacks) the user asked to keep
    ambient. Everything else — the up-to-date roll call, the 'nothing to
    report' line — is dropped, so an empty string means say nothing at all.

    A non-git, never-synced folder is only exempt from the *ambient* hook —
    the project-type-none premise that a one-off script session shouldn't get
    nagged at every session start. An explicit status/`/toolkit-sync` call is
    a deliberate ask, not an ambient interruption, so it reports normally
    (and `sync` itself no longer refuses to write there either — see
    `sync.sync_entries`): otherwise the report and what `sync` can actually
    do would disagree, which is its own source of confusion.

    `scope="user"` reports on `~/.claude` instead: no git-repo/scratch-folder
    notion applies there (it's a machine, not a project), and stack detection
    is a project-only concept, so both are skipped."""
    manifest = load_manifest(toolkit_root)
    state = load_state(claude_dir)

    if scope == "project" and for_hook and not is_onboardable_project(project_dir, state):
        return ""

    lines: list[str] = []
    lines.extend(_synced_lines(manifest, state, toolkit_root, claude_dir, include_clean=not for_hook))
    missing_lines, has_missing_baseline = _missing_lines(manifest, state, scope=scope)
    lines.extend(missing_lines)
    if has_missing_baseline:
        # Uses the /toolkit-sync wrapper (repo root's bin/), not
        # `python -m tools.sync` directly, since this hint is meant to be
        # copy-pasted from any cwd — see toolkit-sync's docstring comment for
        # why that matters. No --toolkit-root: the wrapper already knows its
        # own location and defaults to it unless the caller overrides it.
        target_flag = "--user" if scope == "user" else f"--project-dir {project_dir}"
        lines.append(
            f"hint: run '{toolkit_root}/bin/toolkit-sync sync {target_flag} --yes' "
            "with no entry_ids to sync every baseline entry above in one go. "
            "(on Windows cmd/PowerShell, use "
            f"{toolkit_root}\\bin\\toolkit-sync.cmd instead)"
        )
    if scope == "project":
        lines.extend(_stack_lines(project_dir, toolkit_root, state))
    lines.extend(_suggested_lines(manifest, state, scope=scope))
    if not for_hook:
        lines.extend(_unmanaged_lines(claude_dir, manifest, state))

    if not lines:
        if for_hook:
            return ""
        if scope == "user":
            return "toolkit status (user scope): nothing synced, nothing recommended."
        return "toolkit status: nothing synced, nothing recommended, no stacks detected."
    return "\n".join(lines)


def build_hook_report(toolkit_root: Path, project_dir: Path) -> str:
    """The SessionStart hook's entry point: project scope (`.claude/`) and
    the machine-wide user scope (`~/.claude/`), evaluated together so the
    hook pays for one Python process per session instead of two — the
    hook fires in every session, so that cost is worth avoiding. A project
    that's a scratch folder still gets its user-scope drift reported: that
    drift is about the machine, not about this folder being a real project."""
    project_report = build_status_report(toolkit_root, project_dir / ".claude", project_dir, for_hook=True)
    user_report = build_status_report(toolkit_root, Path.home() / ".claude", project_dir, for_hook=True, scope="user")

    sections = [s for s in (project_report, user_report) if s]
    if not sections:
        return ""
    if not user_report:
        return project_report
    if not project_report:
        return user_report
    return f"{project_report}\n\n(user scope: ~/.claude)\n{user_report}"
