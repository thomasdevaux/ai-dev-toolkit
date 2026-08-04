from pathlib import Path

from tools.sync.diffing import plan_file_changes


def test_plan_file_changes_ignores_crlf_vs_lf_differences(tmp_path: Path):
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()

    (source_root / "rule.md").write_bytes(b"line one\nline two\n")
    (target_root / "rule.md").write_bytes(b"line one\r\nline two\r\n")

    changes = plan_file_changes(source_root, target_root)

    assert changes == []


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
