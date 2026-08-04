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
