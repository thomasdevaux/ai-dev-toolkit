import json
from pathlib import Path

import pytest

from tools.sync.sync import SyncBlocked, sync_entries

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
    """A git repo — sync_entries() refuses to write project-scope entries
    anywhere else, see test_sync_refuses_project_scope_entry_in_a_scratch_folder."""
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps({"enabledPlugins": enabled_plugins}), encoding="utf-8"
    )
    return claude_dir


def test_sync_never_touches_a_plugin_it_never_enabled(tmp_path):
    """A plugin the user installed by hand from a marketplace was never
    recorded in state.plugins, so it's not the toolkit's to remove — even
    with auto_yes, which used to prune it unconditionally."""
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
    assert settings["enabledPlugins"] == {
        "gitlab@claude-plugins-official": True,
        "old-plugin@some-marketplace": True,
    }


def test_sync_prunes_a_plugin_it_enabled_once_the_entry_stops_declaring_it(tmp_path):
    """The other half: a plugin the toolkit itself turned on, whose owning
    entry has since dropped it, is still a genuine prune candidate."""
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path, {"gitlab@claude-plugins-official": True})

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    # The manifest entry stops enabling the plugin (e.g. upstream retired it).
    (toolkit_root / "sync-manifest.yaml").write_text(
        """
- id: gitlab
  type: official-plugin
  plugin_ref: "gitlab@claude-plugins-official"
  scope: project
  tier: baseline
""",
        encoding="utf-8",
    )

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {}
    state = json.loads((claude_dir / ".toolkit-sync-state").read_text(encoding="utf-8"))
    assert "gitlab@claude-plugins-official" not in state["plugins"]


def test_sync_no_prune_output_when_nothing_stale(tmp_path, capsys):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path, {"gitlab@claude-plugins-official": True})

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    assert "[prune]" not in capsys.readouterr().out


FILE_MANIFEST = """
- id: block
  type: file
  source: block
  target: .claude/
  scope: project
  tier: baseline
  settings_patch:
    hooks:
      SessionStart:
        - hooks:
            - type: command
              command: "\\"$CLAUDE_PROJECT_DIR\\"/.claude/hooks/kept.sh"
"""


def _make_file_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    block = toolkit_root / "block" / "hooks"
    block.mkdir(parents=True)
    (block / "kept.sh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    (toolkit_root / "sync-manifest.yaml").write_text(FILE_MANIFEST, encoding="utf-8")
    return toolkit_root


def test_sync_prunes_a_file_the_block_no_longer_ships(tmp_path):
    """A hook deleted upstream must not survive in the consumer's .claude/:
    plan_file_changes only ever writes, so without the prune the retired
    script stays on disk and keeps firing."""
    toolkit_root = _make_file_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)
    claude_dir = project_dir / ".claude"

    sync_entries(["block"], toolkit_root, claude_dir, auto_yes=True)

    retired = claude_dir / "hooks" / "retired.sh"
    retired.write_text("#!/bin/bash\necho noise\n", encoding="utf-8")
    state = json.loads((claude_dir / ".toolkit-sync-state").read_text(encoding="utf-8"))
    state["files"]["hooks/retired.sh"] = "deadbeef"
    (claude_dir / ".toolkit-sync-state").write_text(json.dumps(state), encoding="utf-8")

    sync_entries(["block"], toolkit_root, claude_dir, auto_yes=True)

    assert not retired.exists()
    assert (claude_dir / "hooks" / "kept.sh").is_file()
    state = json.loads((claude_dir / ".toolkit-sync-state").read_text(encoding="utf-8"))
    assert "hooks/retired.sh" not in state["files"]


def test_sync_keeps_an_orphaned_file_when_declined(tmp_path, monkeypatch):
    toolkit_root = _make_file_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)
    claude_dir = project_dir / ".claude"

    sync_entries(["block"], toolkit_root, claude_dir, auto_yes=True)

    retired = claude_dir / "hooks" / "retired.sh"
    retired.write_text("#!/bin/bash\n", encoding="utf-8")
    state_path = claude_dir / ".toolkit-sync-state"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["files"]["hooks/retired.sh"] = "deadbeef"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    sync_entries(["block"], toolkit_root, claude_dir, auto_yes=False)

    assert retired.is_file()
    assert "hooks/retired.sh" in json.loads(state_path.read_text(encoding="utf-8"))["files"]


def test_sync_prunes_a_hook_registration_no_entry_declares(tmp_path):
    toolkit_root = _make_file_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionEnd": [
                        {"hooks": [{"type": "command", "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/retired.sh'}]}
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    sync_entries(["block"], toolkit_root, claude_dir, auto_yes=True)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert "SessionEnd" not in settings["hooks"]
    assert settings["hooks"]["SessionStart"]


def test_sync_leaves_a_consumers_own_hook_alone(tmp_path):
    """Only scripts under a .claude/hooks/ path could have come from the
    toolkit; anything else in settings.json belongs to the consumer."""
    toolkit_root = _make_file_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps({"hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": "./scripts/mine.sh"}]}]}}),
        encoding="utf-8",
    )

    sync_entries(["block"], toolkit_root, claude_dir, auto_yes=True)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["hooks"]["SessionEnd"][0]["hooks"][0]["command"] == "./scripts/mine.sh"


def test_sync_writes_a_project_scope_entry_in_a_scratch_folder(tmp_path):
    """No .git, nothing ever synced: sync no longer requires a repo to write
    project-scope entries — asking it to sync somewhere is itself the
    deliberate signal, same as `git init` used to be. The ambient
    SessionStart hook still stays quiet there (see status.py's
    build_status_report), only sync's own refusal is gone."""
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = tmp_path / "scratch" / ".claude"

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {"gitlab@claude-plugins-official": True}


def test_sync_allows_project_scope_entry_once_a_git_repo(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)
    claude_dir = project_dir / ".claude"

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {"gitlab@claude-plugins-official": True}
