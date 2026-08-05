import pytest

from tools.sync.manifest import (
    ManifestError,
    SyncEntry,
    baseline_entry_ids,
    load_manifest,
    official_plugin_refs,
)


def _entry(
    id_: str,
    type_: str = "file",
    plugin_ref: str | None = None,
    scope: str = "project",
    tier: str = "baseline",
) -> SyncEntry:
    return SyncEntry(id=id_, type=type_, scope=scope, tier=tier, plugin_ref=plugin_ref)


def test_official_plugin_refs_collects_only_official_plugin_entries():
    entries = {
        "gitlab": _entry("gitlab", type_="official-plugin", plugin_ref="gitlab@claude-plugins-official"),
        "common": _entry("common", type_="file"),
    }
    assert official_plugin_refs(entries) == {"gitlab@claude-plugins-official"}


def test_official_plugin_refs_empty_when_none_declared():
    entries = {"common": _entry("common", type_="file")}
    assert official_plugin_refs(entries) == set()


def test_baseline_entry_ids_filters_by_tier_and_scope():
    entries = {
        "common-rules": _entry("common-rules", tier="baseline", scope="project"),
        "gitlab": _entry("gitlab", tier="baseline", scope="project"),
        "toolkit-self-check-user": _entry("toolkit-self-check-user", tier="optional", scope="user"),
        "tech-stack-python": _entry("tech-stack-python", tier="tech-stack", scope="project"),
        "process-light": _entry("process-light", tier="choice-group:process", scope="project"),
    }

    assert baseline_entry_ids(entries, "project") == ["common-rules", "gitlab"]
    assert baseline_entry_ids(entries, "user") == []


def test_manifest_rejects_an_unknown_tier(tmp_path):
    """A typo in `tier:` used to sync silently under a tier nothing looks at —
    the entry would simply never be reported or suggested again."""
    (tmp_path / "sync-manifest.yaml").write_text(
        "- id: x\n  type: file\n  source: a\n  target: .claude/\n  scope: project\n  tier: sugested\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="invalid tier"):
        load_manifest(tmp_path)


def test_manifest_accepts_suggested_and_choice_group_tiers(tmp_path):
    (tmp_path / "sync-manifest.yaml").write_text(
        "- id: a\n  type: file\n  source: a\n  target: .claude/\n  scope: project\n"
        "  tier: suggested\n  summary: one line\n"
        "- id: b\n  type: file\n  source: b\n  target: .claude/\n  scope: project\n"
        "  tier: choice-group:process\n",
        encoding="utf-8",
    )
    entries = load_manifest(tmp_path)
    assert entries["a"].tier == "suggested"
    assert entries["a"].summary == "one line"
    assert entries["b"].choice_group == "process"
