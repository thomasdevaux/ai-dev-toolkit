from tools.sync.settings_patch import merge_patch, remove_plugin, stale_plugin_refs


def test_stale_plugin_refs_filters_known_and_falsy():
    settings = {
        "enabledPlugins": {
            "gitlab@claude-plugins-official": True,
            "old-plugin@some-marketplace": True,
            "disabled-plugin@x": False,
        }
    }
    known = {"gitlab@claude-plugins-official"}
    assert stale_plugin_refs(settings, known) == ["old-plugin@some-marketplace"]


def test_stale_plugin_refs_sorted_when_multiple():
    settings = {
        "enabledPlugins": {
            "zzz@x": True,
            "aaa@x": True,
        }
    }
    assert stale_plugin_refs(settings, set()) == ["aaa@x", "zzz@x"]


def test_stale_plugin_refs_no_enabled_plugins_key():
    assert stale_plugin_refs({}, {"gitlab@claude-plugins-official"}) == []


def test_remove_plugin_deletes_key_only():
    settings = {
        "enabledPlugins": {
            "gitlab@claude-plugins-official": True,
            "old-plugin@some-marketplace": True,
        },
        "otherKey": "untouched",
    }

    result = remove_plugin(settings, "old-plugin@some-marketplace")

    assert result == {
        "enabledPlugins": {"gitlab@claude-plugins-official": True},
        "otherKey": "untouched",
    }
    assert "old-plugin@some-marketplace" in settings["enabledPlugins"]  # original untouched


def test_remove_plugin_missing_key_is_noop():
    settings = {"enabledPlugins": {"gitlab@claude-plugins-official": True}}
    result = remove_plugin(settings, "not-there@x")
    assert result == settings


def test_merge_patch_concatenates_hooks_session_start_from_two_blocks():
    existing = {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "process-light hook"}]},
            ]
        }
    }
    patch = {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "toolkit-self-check hook"}]},
            ]
        }
    }

    merged = merge_patch(existing, patch)

    assert merged["hooks"]["SessionStart"] == [
        {"hooks": [{"type": "command", "command": "process-light hook"}]},
        {"hooks": [{"type": "command", "command": "toolkit-self-check hook"}]},
    ]


def test_merge_patch_is_idempotent_for_hooks_session_start():
    existing = {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "toolkit-self-check hook"}]},
            ]
        }
    }
    patch = {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "toolkit-self-check hook"}]},
            ]
        }
    }

    merged = merge_patch(existing, patch)

    assert merged["hooks"]["SessionStart"] == [
        {"hooks": [{"type": "command", "command": "toolkit-self-check hook"}]},
    ]


def test_merge_patch_still_replaces_non_list_nested_values():
    existing = {"statusLine": {"type": "command", "command": "old"}}
    patch = {"statusLine": {"type": "command", "command": "new"}}

    merged = merge_patch(existing, patch)

    assert merged["statusLine"] == {"type": "command", "command": "new"}
