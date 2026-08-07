from pathlib import Path

import pytest

from tools.sync.diffing import apply_file_changes, plan_file_changes, source_relpaths


def test_plan_file_changes_ignores_crlf_vs_lf_differences(tmp_path: Path):
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()

    (source_root / "rule.md").write_bytes(b"line one\nline two\n")
    (target_root / "rule.md").write_bytes(b"line one\r\nline two\r\n")

    changes = plan_file_changes(source_root, target_root)

    assert changes == []


def test_plan_file_changes_skips_the_blocks_own_manifest_yaml(tmp_path: Path):
    """manifest.yaml is the block's sync-entry definition, not deployable
    content — several blocks share target: ~/.claude/, so copying it would
    make each block's sync overwrite the others' manifest.yaml in turn."""
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()

    (source_root / "manifest.yaml").write_bytes(b"- id: some-entry\n")
    (source_root / "rule.md").write_bytes(b"line one\n")

    changes = plan_file_changes(source_root, target_root)

    assert [c.relpath for c in changes] == ["rule.md"]


def test_plan_file_changes_still_detects_real_content_changes(tmp_path: Path):
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()

    (source_root / "rule.md").write_bytes(b"line one\nline two\n")
    (target_root / "rule.md").write_bytes(b"line one\r\nline THREE\r\n")

    changes = plan_file_changes(source_root, target_root)

    assert len(changes) == 1
    assert changes[0].relpath == "rule.md"
    assert not changes[0].is_new


def test_plan_file_changes_deploys_shared_files_into_the_block(tmp_path: Path):
    """A shared_files entry lives once in the checkout and lands inside the
    block's target tree — react-conventions.md is deployed into both webview
    stacks this way, so neither block carries a copy that could drift."""
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    shared_dir = tmp_path / "shared"
    source_root.mkdir()
    target_root.mkdir()
    shared_dir.mkdir()

    (source_root / "SKILL.md").write_bytes(b"skill\n")
    (shared_dir / "react-conventions.md").write_bytes(b"conventions\n")
    shared = [(shared_dir / "react-conventions.md", "references/react-conventions.md")]

    changes = plan_file_changes(source_root, target_root, shared)

    assert sorted(c.relpath for c in changes) == [
        "SKILL.md",
        "references/react-conventions.md",
    ]

    apply_file_changes(changes)
    assert (target_root / "references" / "react-conventions.md").read_bytes() == b"conventions\n"
    assert plan_file_changes(source_root, target_root, shared) == []


def test_shared_files_relpaths_are_tracked_for_pruning(tmp_path: Path):
    source_root = tmp_path / "source"
    shared_dir = tmp_path / "shared"
    source_root.mkdir()
    shared_dir.mkdir()
    (source_root / "SKILL.md").write_bytes(b"skill\n")
    (shared_dir / "react-conventions.md").write_bytes(b"conventions\n")

    relpaths = source_relpaths(
        source_root,
        [(shared_dir / "react-conventions.md", "references/react-conventions.md")],
    )

    assert relpaths == {"SKILL.md", "references/react-conventions.md"}


def test_missing_shared_file_source_is_an_error(tmp_path: Path):
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()
    (source_root / "SKILL.md").write_bytes(b"skill\n")

    with pytest.raises(FileNotFoundError):
        plan_file_changes(
            source_root,
            target_root,
            [(tmp_path / "gone.md", "references/react-conventions.md")],
        )
