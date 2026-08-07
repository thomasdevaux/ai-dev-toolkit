"""Key-by-key merge of an entry's settings_patch into settings.json.

Never replaces settings.json wholesale — only the top-level keys named in
settings_patch are touched, and within those keys, nested dicts are merged
one level deep (enough for enabledPlugins/statusLine). A nested value that's
a list on both sides (e.g. hooks.SessionStart) is concatenated rather than
replaced, so two different blocks can each register their own SessionStart
hook without one clobbering the other; any other nested value is replaced
wholesale at the key it appears under.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_settings(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def merge_patch(existing: dict, patch: dict) -> dict:
    merged = dict(existing)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            for subkey, subvalue in value.items():
                existing_sub = nested.get(subkey)
                if isinstance(subvalue, list) and isinstance(existing_sub, list):
                    nested[subkey] = existing_sub + [item for item in subvalue if item not in existing_sub]
                else:
                    nested[subkey] = subvalue
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def diff_settings(existing: dict, merged: dict) -> str | None:
    before = json.dumps(existing, indent=2, sort_keys=True)
    after = json.dumps(merged, indent=2, sort_keys=True)
    if before == after:
        return None
    return f"settings.json before:\n{before}\n\nsettings.json after:\n{after}"


def save_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stale_plugin_refs(settings: dict, known_refs: set[str]) -> list[str]:
    enabled = settings.get("enabledPlugins", {})
    return sorted(ref for ref, value in enabled.items() if value and ref not in known_refs)


def remove_plugin(settings: dict, ref: str) -> dict:
    merged = dict(settings)
    enabled = dict(merged.get("enabledPlugins", {}))
    enabled.pop(ref, None)
    merged["enabledPlugins"] = enabled
    return merged


# A hook command the toolkit could have written always runs a script out of a
# .claude/hooks/ directory — `"$CLAUDE_PROJECT_DIR"/.claude/hooks/x.sh` at
# project scope, `"$HOME"/.claude/hooks/x.sh` at user scope. Anything else in
# settings.json is the consumer's own hook and is never a prune candidate,
# however orphaned it looks.
_MANAGED_HOOK_MARKER = "/.claude/hooks/"


def _iter_hook_commands(settings: dict):
    """Yield (event, group_index, hook_index, command) for every command-type
    hook registered in settings.json, tolerating the shapes a hand-edited
    file can take (a missing `hooks` list, a non-dict entry)."""
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                continue
            entries = group.get("hooks")
            if not isinstance(entries, list):
                continue
            for hook_index, hook in enumerate(entries):
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command")
                if isinstance(command, str):
                    yield event, group_index, hook_index, command


def declared_hook_commands(patches) -> set[str]:
    """Every hook command any of the given settings_patch dicts registers."""
    commands: set[str] = set()
    for patch in patches:
        commands.update(command for _e, _g, _h, command in _iter_hook_commands(patch))
    return commands


def stale_hook_commands(settings: dict, known_commands: set[str]) -> list[str]:
    """Hook commands settings.json still registers that no manifest entry
    declares any more — the residue of a hook deleted upstream. Files the
    sync copied are pruned separately; without this the orphaned settings
    entry survives its own script and fires against a missing path forever."""
    return sorted(
        {
            command
            for _e, _g, _h, command in _iter_hook_commands(settings)
            if _MANAGED_HOOK_MARKER in command and command not in known_commands
        }
    )


def remove_hook_command(settings: dict, command: str) -> dict:
    """Drop every registration of `command`, then drop whatever container it
    leaves empty — an empty group, then an empty event, then `hooks` itself.
    Leaving `{"hooks": {"SessionEnd": [{"hooks": []}]}}` behind would be
    inert, but it reads as a hook that exists and does nothing."""
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return settings

    pruned_events = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            pruned_events[event] = groups
            continue
        pruned_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                pruned_groups.append(group)
                continue
            kept = [
                hook
                for hook in group["hooks"]
                if not (isinstance(hook, dict) and hook.get("command") == command)
            ]
            if kept:
                pruned_groups.append({**group, "hooks": kept})
        if pruned_groups:
            pruned_events[event] = pruned_groups

    merged = dict(settings)
    if pruned_events:
        merged["hooks"] = pruned_events
    else:
        merged.pop("hooks", None)
    return merged
