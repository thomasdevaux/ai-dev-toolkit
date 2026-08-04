from tools.sync.manifest import SyncEntry, baseline_entry_ids, official_plugin_refs


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
        "stacks-python": _entry("stacks-python", tier="stack", scope="project"),
        "process-light": _entry("process-light", tier="choice-group:process", scope="project"),
    }

    assert baseline_entry_ids(entries, "project") == ["common-rules", "gitlab"]
    assert baseline_entry_ids(entries, "user") == []
