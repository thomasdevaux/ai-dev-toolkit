"""Orchestrates a single sync run: resolve entries, block on choice-group
conflicts, plan file/settings changes, confirm, apply, update state."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .diffing import apply_file_changes, confirm, plan_file_changes, render_file_changes, sha256_bytes
from .manifest import SyncEntry, load_manifest, official_plugin_refs
from .settings_patch import diff_settings, load_settings, merge_patch, remove_plugin, save_settings, stale_plugin_refs
from .state import load_state, save_state


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
                f"'{other_id}' is already synced for the same group. "
                f"Remove '{other_id}' before syncing '{entry.id}'."
            )


def _prune_stale_plugins(manifest: dict[str, SyncEntry], claude_dir: Path, auto_yes: bool) -> None:
    settings_path = claude_dir / "settings.json"
    settings = load_settings(settings_path)
    known = official_plugin_refs(manifest)
    for ref in stale_plugin_refs(settings, known):
        print(f"[prune] plugin '{ref}' is enabled but not referenced by any entry in sync-manifest.yaml")
        if confirm(f"Remove '{ref}' from enabledPlugins?", auto_yes):
            settings = remove_plugin(settings, ref)
            save_settings(settings_path, settings)
            print(f"[prune] removed '{ref}'")
        else:
            print(f"[prune] kept '{ref}'")


def sync_entries(
    entry_ids: list[str],
    toolkit_root: Path,
    claude_dir: Path,
    auto_yes: bool = False,
) -> None:
    manifest = load_manifest(toolkit_root)
    state = load_state(claude_dir)

    for entry_id in entry_ids:
        if entry_id not in manifest:
            raise SyncBlocked(f"unknown entry id '{entry_id}' (not in sync-manifest.yaml)")
        entry = manifest[entry_id]

        _check_choice_group(entry, state)

        file_changes = []
        if entry.type == "file":
            source_root = toolkit_root / entry.source
            target_root = _resolve_target(claude_dir, entry.target)
            file_changes = plan_file_changes(source_root, target_root)

        settings_path = claude_dir / "settings.json"
        existing_settings = load_settings(settings_path)
        merged_settings = merge_patch(existing_settings, entry.settings_patch) if entry.settings_patch else existing_settings
        settings_diff = diff_settings(existing_settings, merged_settings) if entry.settings_patch else None

        if not file_changes and not settings_diff:
            print(f"[{entry_id}] nothing to synchronize")
            state.entries[entry.id] = {"scope": entry.scope, "tier": entry.tier}
            continue

        print(f"[{entry_id}] proposed changes:")
        if file_changes:
            print(render_file_changes(file_changes))
        if settings_diff:
            print(settings_diff)

        if not confirm(f"Apply changes for '{entry_id}'?", auto_yes):
            print(f"[{entry_id}] cancelled, nothing written")
            continue

        apply_file_changes(file_changes)
        if settings_diff:
            save_settings(settings_path, merged_settings)

        for change in file_changes:
            state.files[change.relpath] = sha256_bytes(change.content)
        state.entries[entry.id] = {"scope": entry.scope, "tier": entry.tier}
        state.ref = _toolkit_ref(toolkit_root)
        print(f"[{entry_id}] applied")

    _prune_stale_plugins(manifest, claude_dir, auto_yes)
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
