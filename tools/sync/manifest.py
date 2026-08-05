"""Load and validate sync-manifest.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

VALID_TYPES = {"file", "official-plugin"}
VALID_SCOPES = {"project", "user"}
# Plain tier values, plus the "choice-group:<name>" family handled separately.
# `suggested` differs from `optional` only in visibility: a suggested entry is
# listed by `status` as available-but-not-installed, an optional one never is.
VALID_TIERS = {"baseline", "tech-stack", "suggested", "optional"}


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
    settings_patch: dict = field(default_factory=dict)

    @property
    def choice_group(self) -> str | None:
        if self.tier.startswith("choice-group:"):
            return self.tier.split(":", 1)[1]
        return None


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
        settings_patch=dict(raw.get("settings_patch", {})),
    )


def load_manifest(toolkit_root: Path) -> dict[str, SyncEntry]:
    manifest_path = toolkit_root / "sync-manifest.yaml"
    if not manifest_path.is_file():
        raise ManifestError(f"no sync-manifest.yaml found at {manifest_path}")

    raw_entries = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or []
    if not isinstance(raw_entries, list):
        raise ManifestError("sync-manifest.yaml must be a top-level list of entries")

    entries: dict[str, SyncEntry] = {}
    for raw in raw_entries:
        entry = _entry_from_dict(raw)
        if entry.id in entries:
            raise ManifestError(f"duplicate entry id '{entry.id}'")
        entries[entry.id] = entry

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
