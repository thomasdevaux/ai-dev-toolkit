"""The choice-group swap: `sync` refuses a second member, `switch` is the
supported way past it — see switch_choice_group's docstring."""
import json
from pathlib import Path

import pytest

from tools.sync.sync import SyncBlocked, switch_choice_group, sync_entries

MANIFEST = """
- id: profile-none
  type: file
  source: profile-none
  target: .claude/
  scope: project
  tier: choice-group:profile

- id: profile-app
  type: file
  source: profile-app
  target: .claude/
  scope: project
  tier: choice-group:profile

- id: unrelated
  type: file
  source: unrelated
  target: .claude/
  scope: project
  tier: baseline
"""


def _make_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    for block, filename in (
        ("profile-none", "no-profile.md"),
        ("profile-app", "app-docs.md"),
        ("unrelated", "shared.md"),
    ):
        rules = toolkit_root / block / "rules"
        rules.mkdir(parents=True)
        (rules / filename).write_text(f"# {filename}\n", encoding="utf-8")
    (toolkit_root / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    return toolkit_root


def _make_project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)
    return project_dir / ".claude"


def _entries(claude_dir: Path) -> dict:
    return json.loads((claude_dir / ".toolkit-sync-state").read_text(encoding="utf-8"))["entries"]


def test_sync_still_refuses_a_second_member_and_names_the_switch_command(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path)
    sync_entries(["profile-none"], toolkit_root, claude_dir, auto_yes=True)

    with pytest.raises(SyncBlocked) as excinfo:
        sync_entries(["profile-app"], toolkit_root, claude_dir, auto_yes=True)

    assert "switch profile profile-app" in str(excinfo.value)


def test_switch_swaps_the_adopted_member_and_prunes_the_old_files(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path)
    sync_entries(["profile-none"], toolkit_root, claude_dir, auto_yes=True)

    switch_choice_group("profile", "profile-app", toolkit_root, claude_dir, auto_yes=True)

    assert (claude_dir / "rules" / "app-docs.md").is_file()
    assert not (claude_dir / "rules" / "no-profile.md").exists()
    state = json.loads((claude_dir / ".toolkit-sync-state").read_text(encoding="utf-8"))
    assert set(state["entries"]) == {"profile-app"}
    assert "rules/no-profile.md" not in state["files"]


def test_switch_leaves_entries_outside_the_group_alone(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path)
    sync_entries(["unrelated", "profile-none"], toolkit_root, claude_dir, auto_yes=True)

    switch_choice_group("profile", "profile-app", toolkit_root, claude_dir, auto_yes=True)

    assert set(_entries(claude_dir)) == {"unrelated", "profile-app"}
    assert (claude_dir / "rules" / "shared.md").is_file()


def test_switch_declined_prune_keeps_the_old_file_but_still_adopts(tmp_path, monkeypatch):
    """Declining the prune is not declining the switch: the state must still
    name the new member, or the next sync would re-raise the conflict."""
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path)
    sync_entries(["profile-none"], toolkit_root, claude_dir, auto_yes=True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y" if "Apply changes" in _prompt else "n")

    switch_choice_group("profile", "profile-app", toolkit_root, claude_dir, auto_yes=False)

    assert (claude_dir / "rules" / "no-profile.md").is_file()
    assert set(_entries(claude_dir)) == {"profile-app"}


def test_switch_with_nothing_adopted_yet_is_a_plain_sync(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path)

    switch_choice_group("profile", "profile-app", toolkit_root, claude_dir, auto_yes=True)

    assert (claude_dir / "rules" / "app-docs.md").is_file()
    assert set(_entries(claude_dir)) == {"profile-app"}


def test_switch_rejects_an_unknown_group(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path)

    with pytest.raises(SyncBlocked, match="no choice-group 'nope'"):
        switch_choice_group("nope", "profile-app", toolkit_root, claude_dir, auto_yes=True)


def test_switch_rejects_an_entry_from_another_group(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path)

    with pytest.raises(SyncBlocked) as excinfo:
        switch_choice_group("profile", "unrelated", toolkit_root, claude_dir, auto_yes=True)

    assert "profile-app, profile-none" in str(excinfo.value)
