"""Orchestrates a single sync run: resolve entries, block on choice-group
conflicts, plan file/settings changes, confirm, apply, update state."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .diffing import (
    apply_file_changes,
    confirm,
    plan_file_changes,
    render_file_changes,
    sha256_bytes,
    source_relpaths,
)
from .manifest import SyncEntry, load_manifest, resolve_shared_files
from .settings_patch import (
    declared_hook_commands,
    diff_settings,
    load_settings,
    merge_patch,
    remove_hook_command,
    remove_plugin,
    save_settings,
    stale_hook_commands,
)
from .state import SyncState, is_onboardable_project, load_state, save_state


class SyncBlocked(RuntimeError):
    pass


def _toolkit_ref(toolkit_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=toolkit_root,
            capture_output=True,
            text=True,
            check=True,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=toolkit_root,
            capture_output=True,
            text=True,
            check=True,
        )
        if status.stdout.strip():
            return "local"
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "local"


def _check_choice_group(entry: SyncEntry, state) -> None:
    group = entry.choice_group
    if not group:
        return
    for other_id, other_meta in state.entries.items():
        if other_id == entry.id:
            continue
        if other_meta.get("tier") == entry.tier:
            raise SyncBlocked(
                f"entry '{entry.id}' belongs to choice-group '{group}', but "
                f"'{other_id}' is already synced for the same group. To adopt "
                f"'{entry.id}' instead, run: python -m tools.sync switch "
                f"{group} {entry.id}"
            )


def switch_choice_group(
    group: str,
    target_id: str,
    toolkit_root: Path,
    claude_dir: Path,
    auto_yes: bool = False,
) -> None:
    """Swap this project's adopted member of a choice-group.

    `_check_choice_group` refuses to sync a second member of the same group,
    and the only way past it is to stop tracking the current one — which used
    to mean hand-editing `.toolkit-sync-state`, the same file that carries the
    per-file hashes drift detection reads. Dropping the old entry here and
    handing over to `sync_entries` keeps that edit inside the tool: the old
    member's files fall out of the managed set and `_prune_orphaned_files`
    offers to delete them, on the same confirmation path as any other prune.
    """
    manifest = load_manifest(toolkit_root)
    members = sorted(e.id for e in manifest.values() if e.choice_group == group)
    if not members:
        raise SyncBlocked(f"no choice-group '{group}' in sync-manifest.yaml")
    if target_id not in manifest:
        raise SyncBlocked(f"unknown entry id '{target_id}' (not in sync-manifest.yaml)")
    if manifest[target_id].choice_group != group:
        raise SyncBlocked(
            f"entry '{target_id}' doesn't belong to choice-group '{group}' "
            f"(members: {', '.join(members)})"
        )

    tier = manifest[target_id].tier
    state = load_state(claude_dir)
    outgoing = sorted(
        entry_id
        for entry_id, meta in state.entries.items()
        if meta.get("tier") == tier and entry_id != target_id
    )
    for entry_id in outgoing:
        print(f"[switch] dropping '{entry_id}': no longer the adopted '{group}' member")
        state.entries.pop(entry_id)
    if outgoing:
        save_state(claude_dir, state)
    elif target_id in state.entries:
        print(f"[switch] '{target_id}' is already this project's '{group}' member")

    sync_entries([target_id], toolkit_root, claude_dir, auto_yes=auto_yes)


def _enabled_plugin_refs(entry: SyncEntry) -> set[str]:
    return {ref for ref, value in entry.settings_patch.get("enabledPlugins", {}).items() if value}


def _managed_plugin_refs(manifest: dict[str, SyncEntry], state: SyncState) -> set[str]:
    """Plugin refs a currently-synced entry still enables. An entry dropped
    from the manifest upstream contributes nothing here — its refs are only
    still prune candidates through `state.plugins`, same as an orphaned
    file's relpath survives in `state.files` after its entry disappears."""
    managed: set[str] = set()
    for entry_id in state.entries:
        entry = manifest.get(entry_id)
        if entry is not None:
            managed |= _enabled_plugin_refs(entry)
    return managed


def _prune_stale_plugins(manifest: dict[str, SyncEntry], state: SyncState, claude_dir: Path, auto_yes: bool) -> None:
    """Only ever removes a plugin the toolkit itself enabled (tracked in
    `state.plugins`) whose owning entry no longer enables it. A plugin the
    user installed by hand from a marketplace was never recorded there, so
    it's never a prune candidate — it's not the toolkit's to remove."""
    settings_path = claude_dir / "settings.json"
    settings = load_settings(settings_path)
    managed = _managed_plugin_refs(manifest, state)
    for ref in sorted(state.plugins):
        if ref in managed:
            continue
        if not settings.get("enabledPlugins", {}).get(ref):
            state.plugins.pop(ref, None)
            continue
        print(f"[prune] plugin '{ref}' was enabled by the toolkit but no synced entry enables it any more")
        if confirm(f"Remove '{ref}' from enabledPlugins?", auto_yes):
            settings = remove_plugin(settings, ref)
            save_settings(settings_path, settings)
            state.plugins.pop(ref, None)
            print(f"[prune] removed '{ref}'")
        else:
            print(f"[prune] kept '{ref}'")


def _prune_orphaned_files(
    manifest: dict[str, SyncEntry],
    state: SyncState,
    toolkit_root: Path,
    claude_dir: Path,
    auto_yes: bool,
) -> None:
    """Delete files this project got from the toolkit that no synced entry
    deploys any more.

    `plan_file_changes` only ever writes; a file dropped upstream — a hook
    retired, a skill moved to another block — therefore survives in the
    consumer's `.claude/` indefinitely, and a retired hook keeps running.
    The managed set is computed from the entries *this* project synced, not
    from the whole manifest: a skill that moved from `common` to another
    block still exists somewhere in the manifest, and only the per-entry
    view can tell that this project no longer receives it.
    """
    managed: set[str] = set()
    for entry_id in state.entries:
        entry = manifest.get(entry_id)
        if entry is None or entry.type != "file":
            # Unknown to the manifest: the block was deleted upstream, so
            # everything it left behind is orphaned. Nothing to add.
            continue
        managed |= source_relpaths(
            toolkit_root / entry.source, resolve_shared_files(entry, toolkit_root)
        )

    for relpath in sorted(set(state.files) - managed):
        target = claude_dir / relpath
        print(f"[prune] '{relpath}' is tracked by the sync state but no synced entry deploys it any more")
        if not confirm(f"Delete '{relpath}'?", auto_yes):
            print(f"[prune] kept '{relpath}'")
            continue
        if target.is_file():
            target.unlink()
            _remove_empty_parents(target.parent, claude_dir)
        state.files.pop(relpath, None)
        print(f"[prune] removed '{relpath}'")


def _remove_empty_parents(directory: Path, stop_at: Path) -> None:
    """Walk up from a just-emptied directory, removing each level that the
    deletion left empty, and never past `stop_at` (the .claude/ root)."""
    current = directory
    while current != stop_at and stop_at in current.parents:
        try:
            next(current.iterdir())
        except StopIteration:
            current.rmdir()
        except FileNotFoundError:
            return
        else:
            return
        current = current.parent


def _prune_stale_hooks(manifest: dict[str, SyncEntry], claude_dir: Path, auto_yes: bool) -> None:
    """Drop hook registrations from settings.json that no manifest entry
    declares any more. Keyed on the whole manifest rather than on the synced
    entries — the same forgiving rule `_prune_stale_plugins` uses — so a hook
    still shipped somewhere in the toolkit is never removed just because this
    project happened to receive it through a different entry."""
    settings_path = claude_dir / "settings.json"
    settings = load_settings(settings_path)
    known = declared_hook_commands(entry.settings_patch for entry in manifest.values())
    for command in stale_hook_commands(settings, known):
        print(f"[prune] hook '{command}' is registered in settings.json but no entry in sync-manifest.yaml declares it")
        if confirm("Remove it from settings.json?", auto_yes):
            settings = remove_hook_command(settings, command)
            save_settings(settings_path, settings)
            print("[prune] removed")
        else:
            print("[prune] kept")


def _is_user_tool(entry: SyncEntry) -> bool:
    return bool(entry.source) and entry.source.startswith("user-tools/")


def sync_entries(
    entry_ids: list[str],
    toolkit_root: Path,
    claude_dir: Path,
    auto_yes: bool = False,
    auto_yes_except_user_tools: bool = False,
) -> None:
    manifest = load_manifest(toolkit_root)
    state = load_state(claude_dir)
    project_dir = claude_dir.parent

    for entry_id in entry_ids:
        if entry_id not in manifest:
            raise SyncBlocked(f"unknown entry id '{entry_id}' (not in sync-manifest.yaml)")
        entry = manifest[entry_id]
        entry_auto_yes = auto_yes or (auto_yes_except_user_tools and not _is_user_tool(entry))

        if entry.scope == "project" and not is_onboardable_project(project_dir, state):
            raise SyncBlocked(
                f"'{project_dir}' isn't a git repository and has nothing synced yet — "
                f"project-scope entry '{entry.id}' won't be written here. The "
                "machine-wide user-scope entries (sync with --user) already cover a "
                "scratch session; run 'git init' first if this is meant to become a "
                "real project."
            )

        _check_choice_group(entry, state)

        file_changes = []
        if entry.type == "file":
            source_root = toolkit_root / entry.source
            target_root = _resolve_target(claude_dir, entry.target)
            file_changes = plan_file_changes(
                source_root, target_root, resolve_shared_files(entry, toolkit_root)
            )

        settings_path = claude_dir / "settings.json"
        existing_settings = load_settings(settings_path)
        merged_settings = merge_patch(existing_settings, entry.settings_patch) if entry.settings_patch else existing_settings
        settings_diff = diff_settings(existing_settings, merged_settings) if entry.settings_patch else None

        if not file_changes and not settings_diff:
            print(f"[{entry_id}] nothing to synchronize")
            state.entries[entry.id] = {"scope": entry.scope, "tier": entry.tier}
            for ref in _enabled_plugin_refs(entry):
                state.plugins[ref] = entry.id
            continue

        print(f"[{entry_id}] proposed changes:")
        if file_changes:
            print(render_file_changes(file_changes))
        if settings_diff:
            print(settings_diff)

        if not confirm(f"Apply changes for '{entry_id}'?", entry_auto_yes):
            print(f"[{entry_id}] cancelled, nothing written")
            continue

        apply_file_changes(file_changes)
        if settings_diff:
            save_settings(settings_path, merged_settings)

        for change in file_changes:
            state.files[change.relpath] = sha256_bytes(change.content)
        state.entries[entry.id] = {"scope": entry.scope, "tier": entry.tier}
        for ref in _enabled_plugin_refs(entry):
            state.plugins[ref] = entry.id
        # Adopting an entry answers the offer it was dismissed from, so the
        # dismissal has nothing left to suppress. Leaving it would silently
        # re-hide the entry the day it's unsynced again.
        if entry.id in state.dismissed:
            state.dismissed.remove(entry.id)
        state.ref = _toolkit_ref(toolkit_root)
        print(f"[{entry_id}] applied")

    prune_auto_yes = auto_yes or auto_yes_except_user_tools
    _prune_stale_plugins(manifest, state, claude_dir, prune_auto_yes)
    _prune_stale_hooks(manifest, claude_dir, prune_auto_yes)
    _prune_orphaned_files(manifest, state, toolkit_root, claude_dir, prune_auto_yes)
    save_state(claude_dir, state)


def _resolve_target(claude_dir: Path, target: str) -> Path:
    """target names a path anchored at .claude/ or ~/.claude/ — both forms
    resolve relative to claude_dir, which the caller already picked based
    on entry.scope (project's .claude/ or the user's ~/.claude/)."""
    remainder = target
    for prefix in ("~/.claude", ".claude"):
        if remainder == prefix or remainder == prefix + "/":
            return claude_dir
        if remainder.startswith(prefix + "/"):
            remainder = remainder[len(prefix) + 1:]
            break
    return claude_dir / remainder if remainder else claude_dir
