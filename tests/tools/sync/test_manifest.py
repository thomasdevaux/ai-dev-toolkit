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
        "toolkit-self-check-user": _entry("toolkit-self-check-user", tier="suggested", scope="user"),
        "tech-stack-python": _entry("tech-stack-python", tier="tech-stack", scope="project"),
        "project-type-app": _entry("project-type-app", tier="choice-group:project-type", scope="project"),
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
        "  tier: choice-group:project-type\n",
        encoding="utf-8",
    )
    entries = load_manifest(tmp_path)
    assert entries["a"].tier == "suggested"
    assert entries["a"].summary == "one line"
    assert entries["b"].choice_group == "project-type"


def test_manifest_follows_includes_from_block_directories(tmp_path):
    """Each block directory owns its own manifest.yaml fragment; the root
    file is just an index of includes, so a project sees one entry per
    directory, not one file everyone edits."""
    (tmp_path / "sync-manifest.yaml").write_text(
        "- include: common/manifest.yaml\n- include: suggested/thing/manifest.yaml\n",
        encoding="utf-8",
    )
    (tmp_path / "common").mkdir()
    (tmp_path / "common" / "manifest.yaml").write_text(
        "- id: common-rules\n  type: file\n  source: common\n  target: .claude/\n"
        "  scope: project\n  tier: baseline\n  summary: one line\n",
        encoding="utf-8",
    )
    (tmp_path / "suggested" / "thing").mkdir(parents=True)
    (tmp_path / "suggested" / "thing" / "manifest.yaml").write_text(
        "- id: thing\n  type: official-plugin\n  plugin_ref: \"thing@marketplace\"\n"
        "  scope: user\n  tier: suggested\n  summary: one line\n",
        encoding="utf-8",
    )

    entries = load_manifest(tmp_path)

    assert set(entries) == {"common-rules", "thing"}
    assert entries["thing"].plugin_ref == "thing@marketplace"


def test_manifest_rejects_a_circular_include(tmp_path):
    (tmp_path / "sync-manifest.yaml").write_text("- include: a.yaml\n", encoding="utf-8")
    (tmp_path / "a.yaml").write_text("- include: sync-manifest.yaml\n", encoding="utf-8")

    with pytest.raises(ManifestError, match="circular include"):
        load_manifest(tmp_path)


def test_manifest_rejects_an_include_entry_with_extra_fields(tmp_path):
    (tmp_path / "sync-manifest.yaml").write_text(
        "- include: a.yaml\n  tier: baseline\n", encoding="utf-8"
    )

    with pytest.raises(ManifestError, match="no other fields"):
        load_manifest(tmp_path)
