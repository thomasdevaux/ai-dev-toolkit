import json
from pathlib import Path

from tools.sync.manifest import SyncEntry
from tools.sync.state import SyncState
from tools.sync.status import _missing_lines, build_status_report

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

- id: stacks-nodejs
  type: file
  source: stacks/nodejs
  target: .claude/
  scope: project
  tier: stack
  detect: ["package.json"]
"""


def _make_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    toolkit_root.mkdir()
    (toolkit_root / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    common_dir = toolkit_root / "common" / "rules"
    common_dir.mkdir(parents=True)
    (common_dir / "style.md").write_text("# style\n", encoding="utf-8")
    (toolkit_root / "stacks" / "nodejs").mkdir(parents=True)
    return toolkit_root


def test_status_reports_missing_baseline_on_empty_project(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[common-rules] recommended (baseline), not yet synced" in report
    assert "[gitlab] recommended (baseline), not yet synced" in report
    assert f"sync --toolkit-root {toolkit_root} --project-dir {project_dir}" in report


def test_status_omits_hint_when_no_baseline_missing():
    manifest = {
        "process-light": SyncEntry(id="process-light", type="file", scope="project", tier="choice-group:process"),
        "process-full": SyncEntry(id="process-full", type="file", scope="project", tier="choice-group:process"),
    }

    lines, has_missing_baseline = _missing_lines(manifest, SyncState())

    assert lines == ["[choice-group:process] pick exactly one, not yet synced: process-full, process-light"]
    assert has_missing_baseline is False


def test_status_stops_flagging_the_other_choice_group_member_once_one_is_synced():
    manifest = {
        "process-light": SyncEntry(id="process-light", type="file", scope="project", tier="choice-group:process"),
        "process-full": SyncEntry(id="process-full", type="file", scope="project", tier="choice-group:process"),
    }
    state = SyncState(entries={"process-light": {"scope": "project", "tier": "choice-group:process"}})

    lines, has_missing_baseline = _missing_lines(manifest, state)

    assert lines == []
    assert has_missing_baseline is False


def test_status_reports_up_to_date_entry(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    (claude_dir / "rules").mkdir(parents=True)
    (claude_dir / "rules" / "style.md").write_text("# style\n", encoding="utf-8")
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc123",
                "files": {"rules/style.md": "irrelevant"},
                "entries": {"common-rules": {"scope": "project", "tier": "baseline"}},
            }
        ),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[common-rules] up to date" in report
    assert "[common-rules] recommended" not in report


def test_status_reports_drift_on_changed_file(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    (claude_dir / "rules").mkdir(parents=True)
    (claude_dir / "rules" / "style.md").write_text("# stale content\n", encoding="utf-8")
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc123",
                "files": {"rules/style.md": "irrelevant"},
                "entries": {"common-rules": {"scope": "project", "tier": "baseline"}},
            }
        ),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[common-rules] drift: 1 file(s) changed" in report


def test_status_reports_drift_on_changed_settings(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(json.dumps({}), encoding="utf-8")
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc123",
                "files": {},
                "entries": {"gitlab": {"scope": "project", "tier": "baseline"}},
            }
        ),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[gitlab] drift: settings changed" in report


def test_status_reports_detected_stacks(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "package.json").write_text("{}", encoding="utf-8")
    claude_dir = project_dir / ".claude"

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "detected stack(s), suggested for review (not synced automatically):" in report
    assert "  - nodejs" in report
