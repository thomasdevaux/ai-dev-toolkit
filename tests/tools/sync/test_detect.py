from pathlib import Path

import pytest

from tools.sync.detect import detect_stacks
from tools.sync.manifest import ManifestError

MANIFEST = """
- id: tech-stack-python
  type: file
  source: tech-stacks/python
  target: .claude/
  scope: project
  tier: tech-stack
  detect: ["pyproject.toml", "requirements.txt"]

- id: tech-stack-dotnet
  type: file
  source: tech-stacks/dotnet
  target: .claude/
  scope: project
  tier: tech-stack
  detect: ["*.csproj", "*.sln"]

- id: tech-stack-rust
  type: file
  source: tech-stacks/rust
  target: .claude/
  scope: project
  tier: tech-stack
  detect_all: ["Cargo.toml", "src-tauri"]

- id: some-rule
  type: file
  source: common
  target: .claude/
  scope: project
  tier: baseline
"""


def _make_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    toolkit_root.mkdir()
    (toolkit_root / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    return toolkit_root


def test_detects_plain_marker_file_at_root(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text("", encoding="utf-8")

    assert detect_stacks(project_dir, toolkit_root) == ["tech-stack-python"]


def test_detects_plain_marker_file_one_level_deep(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    sub = project_dir / "backend"
    sub.mkdir(parents=True)
    (sub / "requirements.txt").write_text("", encoding="utf-8")

    assert detect_stacks(project_dir, toolkit_root) == ["tech-stack-python"]


def test_entry_with_no_detect_field_is_never_suggested(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    assert detect_stacks(project_dir, toolkit_root) == []


def test_detects_glob_marker_within_bounded_depth(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    sub = project_dir / "src"
    sub.mkdir(parents=True)
    (sub / "app.csproj").write_text("", encoding="utf-8")

    assert detect_stacks(project_dir, toolkit_root) == ["tech-stack-dotnet"]


def test_glob_marker_beyond_bounded_depth_is_not_detected(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    deep = project_dir / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    (deep / "app.csproj").write_text("", encoding="utf-8")

    assert detect_stacks(project_dir, toolkit_root) == []


def test_glob_and_plain_markers_share_the_same_depth_bound(tmp_path):
    """A .csproj two levels down is a sub-project's, not the project's — the
    same verdict a requirements.txt at that depth already got. This repo's own
    demo/dotnet-tool/*.csproj is the case that made the mismatch visible."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / "demo" / "dotnet-tool").mkdir(parents=True)
    (project_dir / "demo" / "dotnet-tool" / "app.csproj").write_text("", encoding="utf-8")
    (project_dir / "tools" / "sync").mkdir(parents=True)
    (project_dir / "tools" / "sync" / "requirements.txt").write_text("", encoding="utf-8")

    assert detect_stacks(project_dir, toolkit_root) == []


def test_detect_all_requires_every_marker(tmp_path):
    """Cargo.toml alone is any crate — the block is Tauri-specific, so the
    framework marker has to be there too."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "Cargo.toml").write_text("", encoding="utf-8")

    assert detect_stacks(project_dir, toolkit_root) == []

    (project_dir / "src-tauri").mkdir()

    assert detect_stacks(project_dir, toolkit_root) == ["tech-stack-rust"]


def test_detect_all_markers_must_share_a_directory(tmp_path):
    """A crate in one subproject and a Tauri app in another are two different
    projects, not one Tauri app."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    (project_dir / "some-crate").mkdir(parents=True)
    (project_dir / "some-crate" / "Cargo.toml").write_text("", encoding="utf-8")
    (project_dir / "unrelated" / "src-tauri").mkdir(parents=True)

    assert detect_stacks(project_dir, toolkit_root) == []


def test_detect_all_matches_one_level_deep(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    app = project_dir / "app"
    (app / "src-tauri").mkdir(parents=True)
    (app / "Cargo.toml").write_text("", encoding="utf-8")

    assert detect_stacks(project_dir, toolkit_root) == ["tech-stack-rust"]


def test_glob_marker_under_excluded_dir_is_not_detected(tmp_path):
    """A vendored/nested .csproj under node_modules must not trigger a false
    suggestion, unlike the old unbounded project_dir.rglob() search."""
    toolkit_root = _make_toolkit(tmp_path)
    project_dir = tmp_path / "project"
    nested = project_dir / "node_modules" / "some-pkg"
    nested.mkdir(parents=True)
    (nested / "app.csproj").write_text("", encoding="utf-8")

    assert detect_stacks(project_dir, toolkit_root) == []


def test_detect_and_detect_all_on_the_same_entry_is_rejected(tmp_path):
    toolkit_root = tmp_path / "toolkit"
    toolkit_root.mkdir()
    (toolkit_root / "sync-manifest.yaml").write_text(
        """
- id: tech-stack-both
  type: file
  source: tech-stacks/both
  target: .claude/
  scope: project
  tier: tech-stack
  detect: ["go.mod"]
  detect_all: ["go.mod", "wails.json"]
""",
        encoding="utf-8",
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with pytest.raises(ManifestError, match="mutually exclusive"):
        detect_stacks(project_dir, toolkit_root)
