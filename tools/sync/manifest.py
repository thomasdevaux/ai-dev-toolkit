"""Load and validate sync-manifest.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

VALID_TYPES = {"file", "official-plugin"}
VALID_SCOPES = {"project", "user"}
# Plain tier values, plus the "choice-group:<name>" family handled separately.
# `suggested` is the only opt-in, never-imposed tier: `status` lists it as
# available-but-not-installed until someone syncs it by id. A former
# `optional` tier (invisible everywhere) was folded into this one — the
# visibility was the only real difference, and invisible-by-default just
# meant nobody found the entry to opt into it.
VALID_TIERS = {"baseline", "tech-stack", "suggested"}


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class SyncEntry:
    id: str
    type: str
    scope: str
    tier: str
    source: str | None = None
    target: str | None = None
    plugin_ref: str | None = None
    summary: str = ""
    detect: list[str] = field(default_factory=list)
    detect_all: list[str] = field(default_factory=list)
    shared_files: tuple[tuple[str, str], ...] = ()
    settings_patch: dict = field(default_factory=dict)

    @property
    def choice_group(self) -> str | None:
        if self.tier.startswith("choice-group:"):
            return self.tier.split(":", 1)[1]
        return None


def _shared_files_from_raw(entry_id: str, raw_shared) -> tuple[tuple[str, str], ...]:
    """`shared_files:` deploys a file that several blocks ship identically —
    `tech-stacks/shared/react-conventions.md` goes to both the Tauri and the
    Wails skill. One copy in the checkout, so the two can't drift; still a real
    file inside each block once synced, so a project that syncs one stack gets
    a self-contained skill. `source` is relative to the toolkit root, `target`
    to the entry's own target root."""
    if not isinstance(raw_shared, list):
        raise ManifestError(f"entry '{entry_id}': 'shared_files' must be a list")
    pairs = []
    for item in raw_shared:
        if not isinstance(item, dict) or not item.get("source") or not item.get("target"):
            raise ManifestError(
                f"entry '{entry_id}': each shared_files item needs 'source' and 'target', got {item!r}"
            )
        pairs.append((item["source"], item["target"]))
    return tuple(pairs)


def _entry_from_dict(raw: dict) -> SyncEntry:
    entry_id = raw.get("id")
    if not entry_id:
        raise ManifestError(f"manifest entry missing required field 'id': {raw}")

    entry_type = raw.get("type", "file")
    if entry_type not in VALID_TYPES:
        raise ManifestError(f"entry '{entry_id}': invalid type '{entry_type}'")

    scope = raw.get("scope")
    if scope not in VALID_SCOPES:
        raise ManifestError(f"entry '{entry_id}': invalid scope '{scope}'")

    tier = raw.get("tier")
    if not tier:
        raise ManifestError(f"entry '{entry_id}': missing required field 'tier'")
    if tier not in VALID_TIERS and not tier.startswith("choice-group:"):
        raise ManifestError(
            f"entry '{entry_id}': invalid tier '{tier}' "
            f"(expected one of {sorted(VALID_TIERS)} or 'choice-group:<name>')"
        )

    # One detection shape per entry: `detect:` is "any marker is enough",
    # `detect_all:` is "every marker, in the same directory". Declaring both
    # would leave the combination ambiguous to a reader of the manifest, which
    # is the file people reason about — so it's rejected rather than resolved.
    if raw.get("detect") and raw.get("detect_all"):
        raise ManifestError(
            f"entry '{entry_id}': 'detect' and 'detect_all' are mutually exclusive"
        )

    if entry_type == "file":
        if not raw.get("source") or not raw.get("target"):
            raise ManifestError(
                f"entry '{entry_id}': type 'file' requires 'source' and 'target'"
            )
    elif entry_type == "official-plugin":
        if not raw.get("plugin_ref"):
            raise ManifestError(
                f"entry '{entry_id}': type 'official-plugin' requires 'plugin_ref'"
            )
        if raw.get("shared_files"):
            raise ManifestError(
                f"entry '{entry_id}': 'shared_files' only applies to type 'file'"
            )

    return SyncEntry(
        id=entry_id,
        type=entry_type,
        scope=scope,
        tier=tier,
        source=raw.get("source"),
        target=raw.get("target"),
        plugin_ref=raw.get("plugin_ref"),
        summary=raw.get("summary", ""),
        detect=list(raw.get("detect", [])),
        detect_all=list(raw.get("detect_all", [])),
        shared_files=_shared_files_from_raw(entry_id, raw.get("shared_files", [])),
        settings_patch=dict(raw.get("settings_patch", {})),
    )


def _load_manifest_file(
    manifest_path: Path,
    toolkit_root: Path,
    entries: dict[str, SyncEntry],
    seen_files: set[Path],
) -> None:
    """A manifest file is a list of either entry dicts or `{include: <path>}`
    directives, `<path>` relative to `toolkit_root`. Each block directory
    (common/, tech-stacks/<lang>/, suggested/<topic>/, ...) owns its own
    fragment; the root sync-manifest.yaml just includes them, so the file
    tree stays the single legible index instead of one growing flat list."""
    resolved = manifest_path.resolve()
    if resolved in seen_files:
        raise ManifestError(f"circular include: {manifest_path}")
    if not manifest_path.is_file():
        raise ManifestError(f"no manifest file found at {manifest_path}")
    seen_files.add(resolved)

    raw_items = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or []
    if not isinstance(raw_items, list):
        raise ManifestError(f"{manifest_path} must be a top-level list of entries")

    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ManifestError(f"{manifest_path}: entries must be mappings, got {raw!r}")
        if "include" in raw:
            if len(raw) != 1:
                raise ManifestError(f"{manifest_path}: 'include' entries take no other fields, got {raw!r}")
            _load_manifest_file(toolkit_root / raw["include"], toolkit_root, entries, seen_files)
            continue
        entry = _entry_from_dict(raw)
        if entry.id in entries:
            raise ManifestError(f"duplicate entry id '{entry.id}'")
        entries[entry.id] = entry


def _read_version(toolkit_root: Path) -> str:
    version_path = toolkit_root / "VERSION"
    if not version_path.is_file():
        raise ManifestError(
            f"a manifest uses {{{{VERSION}}}} but no VERSION file exists at {version_path}"
        )
    return version_path.read_text(encoding="utf-8").strip()


def _substitute(value, replacements: dict[str, str]):
    """Expand `{{NAME}}` placeholders in every string of a settings_patch,
    at any depth. Only `VERSION` is defined today: the startup banner names
    the toolkit version, and a version written by hand in a manifest is one
    nobody remembers to bump — it just quietly starts lying. Resolved at load
    time, so `status`, the diff and `sync` all see the same expanded value and
    a version bump surfaces as ordinary drift."""
    if isinstance(value, str):
        for name, replacement in replacements.items():
            value = value.replace("{{" + name + "}}", replacement)
        return value
    if isinstance(value, dict):
        return {key: _substitute(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_substitute(item, replacements) for item in value]
    return value


def load_manifest(toolkit_root: Path) -> dict[str, SyncEntry]:
    manifest_path = toolkit_root / "sync-manifest.yaml"
    if not manifest_path.is_file():
        raise ManifestError(f"no sync-manifest.yaml found at {manifest_path}")

    entries: dict[str, SyncEntry] = {}
    _load_manifest_file(manifest_path, toolkit_root, entries, set())

    # Read VERSION only if something actually asks for it, so a toolkit
    # checkout without the file keeps working until it uses a placeholder.
    if any("{{VERSION}}" in yaml.safe_dump(e.settings_patch) for e in entries.values()):
        replacements = {"VERSION": _read_version(toolkit_root)}
        entries = {
            entry_id: replace(entry, settings_patch=_substitute(entry.settings_patch, replacements))
            for entry_id, entry in entries.items()
        }
    return entries


def official_plugin_refs(entries: dict[str, SyncEntry]) -> set[str]:
    """Every plugin_ref declared by a type: official-plugin entry, regardless
    of whether that entry has been synced to any given project."""
    return {e.plugin_ref for e in entries.values() if e.type == "official-plugin"}


def baseline_entry_ids(entries: dict[str, SyncEntry], scope: str) -> list[str]:
    """Every entry with tier: baseline whose scope matches the given target
    ('project' or 'user') — the default entry set `sync` uses when called
    with no explicit entry_ids, so the team's non-negotiable baseline is
    always synced together rather than one entry at a time."""
    return sorted(e.id for e in entries.values() if e.tier == "baseline" and e.scope == scope)


def resolve_shared_files(entry: SyncEntry, toolkit_root: Path) -> list[tuple[Path, str]]:
    """An entry's `shared_files:` as (absolute source, relpath under the entry's
    target root) — the shape diffing works in, so a shared file is planned,
    written, hashed and pruned exactly like a file of the block's own tree."""
    return [
        (toolkit_root / source, target.replace("\\", "/"))
        for source, target in entry.shared_files
    ]
