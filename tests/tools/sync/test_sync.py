import json
from pathlib import Path

from tools.sync.sync import sync_entries

MANIFEST = """
- id: gitlab
  type: official-plugin
  plugin_ref: "gitlab@claude-plugins-official"
  scope: project
  tier: baseline
  settings_patch:
    enabledPlugins:
      "gitlab@claude-plugins-official": true
"""


def _make_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    toolkit_root.mkdir()
    (toolkit_root / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    return toolkit_root


def _make_project(tmp_path: Path, enabled_plugins: dict) -> Path:
    claude_dir = tmp_path / "project" / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps({"enabledPlugins": enabled_plugins}), encoding="utf-8"
    )
    return claude_dir


def test_sync_prunes_stale_plugin_with_auto_yes(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(
        tmp_path,
        {
            "gitlab@claude-plugins-official": True,
            "old-plugin@some-marketplace": True,
        },
    )

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {"gitlab@claude-plugins-official": True}


def test_sync_keeps_stale_plugin_when_declined(tmp_path, monkeypatch):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(
        tmp_path,
        {
            "gitlab@claude-plugins-official": True,
            "old-plugin@some-marketplace": True,
        },
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=False)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {
        "gitlab@claude-plugins-official": True,
        "old-plugin@some-marketplace": True,
    }


def test_sync_no_prune_output_when_nothing_stale(tmp_path, capsys):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path, {"gitlab@claude-plugins-official": True})

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    assert "[prune]" not in capsys.readouterr().out
