from pathlib import Path

from tools.sync.cli import main

MANIFEST = """
- id: common-rules
  type: file
  source: common
  target: .claude/
  scope: project
  tier: baseline

- id: gitlab
  type: official-plugin
  plugin_ref: "gitlab@claude-plugins-official"
  scope: project
  tier: baseline
  settings_patch:
    enabledPlugins:
      "gitlab@claude-plugins-official": true

- id: tech-stack-nodejs
  type: file
  source: tech-stacks/nodejs
  target: .claude/
  scope: project
  tier: tech-stack
  detect: ["package.json"]
"""


def _make_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    toolkit_root.mkdir()
    (toolkit_root / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    common_dir = toolkit_root / "common" / "rules"
    common_dir.mkdir(parents=True)
    (common_dir / "style.md").write_text("# style\n", encoding="utf-8")
    (toolkit_root / "tech-stacks" / "nodejs").mkdir(parents=True)
    return toolkit_root


def test_sync_with_no_entry_ids_syncs_every_baseline_entry(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)

    exit_code = main(
        [
            "sync",
            "--toolkit-root",
            str(toolkit_root),
            "--project-dir",
            str(project_dir),
            "--yes",
        ]
    )

    assert exit_code == 0
    assert (project_dir / ".claude" / "rules" / "style.md").is_file()

    import json

    settings = json.loads((project_dir / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {"gitlab@claude-plugins-official": True}

    state = json.loads((project_dir / ".claude" / ".toolkit-sync-state").read_text(encoding="utf-8"))
    assert set(state["entries"]) == {"common-rules", "gitlab"}


def test_sync_with_no_entry_ids_also_re_syncs_a_drifted_already_adopted_entry(tmp_path):
    """The regression a real session hit: answering 'Sync now' ran `sync`
    with no ids, which only ever re-synced tier:baseline entries — drift on
    an already-adopted non-baseline entry (e.g. project-type-app) was
    reported by `status` but never actually cleared, no matter how many
    times the question got answered."""
    import json

    toolkit_root = _make_toolkit(tmp_path)
    (toolkit_root / "tech-stacks" / "nodejs" / "rules").mkdir(parents=True)
    (toolkit_root / "tech-stacks" / "nodejs" / "rules" / "node.md").write_text(
        "# node\n", encoding="utf-8"
    )
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "rules").mkdir()
    (claude_dir / "rules" / "node.md").write_text("# stale\n", encoding="utf-8")
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc123",
                "files": {"rules/node.md": "irrelevant"},
                "entries": {"tech-stack-nodejs": {"scope": "project", "tier": "tech-stack"}},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "sync",
            "--toolkit-root",
            str(toolkit_root),
            "--project-dir",
            str(project_dir),
            "--yes",
        ]
    )

    assert exit_code == 0
    assert (claude_dir / "rules" / "node.md").read_text(encoding="utf-8") == "# node\n"

    state = json.loads((claude_dir / ".toolkit-sync-state").read_text(encoding="utf-8"))
    assert set(state["entries"]) == {"common-rules", "gitlab", "tech-stack-nodejs"}


def test_sync_with_explicit_entry_id_still_syncs_only_that_entry(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)

    exit_code = main(
        [
            "sync",
            "tech-stack-nodejs",
            "--toolkit-root",
            str(toolkit_root),
            "--project-dir",
            str(project_dir),
            "--yes",
        ]
    )

    assert exit_code == 0

    import json

    state = json.loads((project_dir / ".claude" / ".toolkit-sync-state").read_text(encoding="utf-8"))
    assert set(state["entries"]) == {"tech-stack-nodejs"}
