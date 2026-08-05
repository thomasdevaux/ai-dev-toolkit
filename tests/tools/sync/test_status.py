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

- id: tech-stack-python
  type: file
  source: tech-stacks/python
  target: .claude/
  scope: project
  tier: tech-stack
  detect: ["pyproject.toml"]

- id: some-tool
  type: file
  source: some-tool
  target: .claude/
  scope: project
  tier: suggested
  summary: A useful extra.
"""


def _make_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    toolkit_root.mkdir()
    (toolkit_root / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    common_dir = toolkit_root / "common" / "rules"
    common_dir.mkdir(parents=True)
    (common_dir / "style.md").write_text("# style\n", encoding="utf-8")
    (toolkit_root / "tech-stacks" / "python").mkdir(parents=True)
    (toolkit_root / "some-tool").mkdir(parents=True)
    return toolkit_root


def _make_project(tmp_path: Path) -> Path:
    """A project the report is allowed to speak about: a git repository.
    A folder that is neither a repo nor synced gets a one-line mention
    instead, so opening a session in a scratch directory stays quiet."""
    project_dir = tmp_path / "project"
    (project_dir / ".git").mkdir(parents=True)
    return project_dir


def test_status_reports_missing_baseline_on_empty_project(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = _make_project(tmp_path)
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
    project_dir = _make_project(tmp_path)
    (project_dir / "pyproject.toml").write_text("", encoding="utf-8")
    claude_dir = project_dir / ".claude"

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "detected stack(s), suggested for review (not synced automatically):" in report
    assert "  - python" in report


def test_status_stays_quiet_in_a_scratch_folder(tmp_path):
    """No .git, nothing ever synced: a session opened here to poke at a script
    must not turn into an onboarding checklist."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "scratch"
    project_dir.mkdir()

    report = build_status_report(toolkit_root, project_dir / ".claude", project_dir)

    assert "isn't a git repository" in report
    assert "recommended (baseline)" not in report
    assert "choice-group" not in report


def test_status_speaks_in_a_synced_folder_even_without_git(tmp_path):
    """Once something has been synced, the folder is a project whatever git
    thinks of it — drift on what's already there still has to surface."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps({"ref": "abc123", "files": {}, "entries": {"gitlab": {"scope": "project", "tier": "baseline"}}}),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[common-rules] recommended (baseline), not yet synced" in report


def test_status_lists_suggested_entries_without_pressing(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = _make_project(tmp_path)
    claude_dir = project_dir / ".claude"

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "available, not installed (never synced automatically):" in report
    assert "  - some-tool - A useful extra." in report
    # A suggested entry is never phrased as missing, and never blocks.
    assert "[some-tool] recommended" not in report


def test_status_drops_a_suggested_entry_once_synced(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = _make_project(tmp_path)
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps({"ref": "abc", "files": {}, "entries": {"some-tool": {"scope": "project", "tier": "suggested"}}}),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "available, not installed" not in report


USER_SCOPE_MANIFEST = """
- id: project-thing
  type: file
  source: common
  target: .claude/
  scope: project
  tier: baseline
  summary: a project block

- id: machine-thing
  type: file
  source: common
  target: ~/.claude/
  scope: user
  tier: baseline
  summary: a per-machine install
"""


def test_status_never_reports_a_user_scope_entry_as_missing_from_a_project(tmp_path):
    """A user-scope baseline entry lives in ~/.claude. Reporting it in a
    project's report would nag for something no project sync can fix."""
    toolkit_root = tmp_path / "toolkit"
    (toolkit_root / "common" / "rules").mkdir(parents=True)
    (toolkit_root / "common" / "rules" / "r.md").write_text("# r\n", encoding="utf-8")
    (toolkit_root / "sync-manifest.yaml").write_text(USER_SCOPE_MANIFEST, encoding="utf-8")
    project_dir = _make_project(tmp_path)

    report = build_status_report(toolkit_root, project_dir / ".claude", project_dir)

    assert "[project-thing] recommended (baseline), not yet synced" in report
    assert "machine-thing" not in report


def _fully_synced_project(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A project with nothing pending: both baseline entries synced and clean,
    a process choice made, and no suggested entry left to offer."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = _make_project(tmp_path)
    claude_dir = project_dir / ".claude"
    (claude_dir / "rules").mkdir(parents=True)
    (claude_dir / "rules" / "style.md").write_text("# style\n", encoding="utf-8")
    (claude_dir / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"gitlab@claude-plugins-official": True}}), encoding="utf-8"
    )
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc123",
                "files": {"rules/style.md": "irrelevant"},
                "entries": {
                    "common-rules": {"scope": "project", "tier": "baseline"},
                    "gitlab": {"scope": "project", "tier": "baseline"},
                    "some-tool": {"scope": "project", "tier": "suggested"},
                },
            }
        ),
        encoding="utf-8",
    )
    return toolkit_root, project_dir, claude_dir


def test_hook_report_is_empty_when_nothing_needs_saying(tmp_path):
    """The whole point of for_hook: an empty string is the signal to print
    nothing at all, not even which checkout was resolved."""
    toolkit_root, project_dir, claude_dir = _fully_synced_project(tmp_path)

    assert build_status_report(toolkit_root, claude_dir, project_dir, for_hook=True) == ""


def test_hook_report_drops_the_up_to_date_roll_call_but_status_keeps_it(tmp_path):
    toolkit_root, project_dir, claude_dir = _fully_synced_project(tmp_path)
    (claude_dir / "rules" / "style.md").write_text("# drifted\n", encoding="utf-8")

    hook_report = build_status_report(toolkit_root, claude_dir, project_dir, for_hook=True)
    full_report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "[common-rules] drift: 1 file(s) changed" in hook_report
    assert "up to date" not in hook_report
    assert "[gitlab] up to date" in full_report


def test_hook_report_keeps_the_two_discovery_sections(tmp_path):
    """Suggested blocks and detected stacks stay ambient — they're the only
    way someone finds out a block exists without going looking for it."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = _make_project(tmp_path)
    (project_dir / "pyproject.toml").write_text("", encoding="utf-8")

    report = build_status_report(toolkit_root, project_dir / ".claude", project_dir, for_hook=True)

    assert "  - python" in report
    assert "  - some-tool - A useful extra." in report


def test_hook_report_stays_empty_in_a_scratch_folder(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "scratch"
    project_dir.mkdir()

    assert build_status_report(toolkit_root, project_dir / ".claude", project_dir, for_hook=True) == ""


def test_status_stops_suggesting_a_stack_once_its_block_is_synced(tmp_path):
    """Otherwise the suggestion is permanent: it's printed every session of
    every Python project, including the ones that already took it."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = _make_project(tmp_path)
    (project_dir / "pyproject.toml").write_text("", encoding="utf-8")
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / ".toolkit-sync-state").write_text(
        json.dumps(
            {
                "ref": "abc",
                "files": {},
                "entries": {"tech-stack-python": {"scope": "project", "tier": "tech-stack"}},
            }
        ),
        encoding="utf-8",
    )

    report = build_status_report(toolkit_root, claude_dir, project_dir)

    assert "detected stack(s)" not in report
