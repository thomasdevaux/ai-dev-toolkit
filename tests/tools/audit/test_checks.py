from pathlib import Path

from tools.audit.checks import AuditResult, check_summaries, check_vendor_provenance

MANIFEST = """
- id: with-summary
  type: file
  source: a
  target: .claude/
  scope: project
  tier: baseline
  summary: does a thing

- id: without-summary
  type: file
  source: b
  target: .claude/
  scope: project
  tier: suggested
"""

BLOCK_MANIFEST = """
- id: block
  type: file
  source: block
  target: .claude/
  scope: project
  tier: baseline
  summary: a block
"""

COMPLETE_SOURCE_MD = """# SOURCE - x
- upstream: https://example.invalid/x
- commit: abc123
- license: MIT
- imported: 2026-08-05
"""


def _toolkit(tmp_path: Path) -> Path:
    (tmp_path / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    return tmp_path


def test_missing_summary_is_reported(tmp_path):
    result = AuditResult()
    check_summaries(_toolkit(tmp_path), result)
    messages = [f.message for f in result.findings]
    assert any("without-summary" in m for m in messages)
    assert not any("with-summary" in m for m in messages)


def _block_toolkit(tmp_path: Path) -> Path:
    """A toolkit whose single block is a syncable directory — provenance is
    only checked on content that actually gets redistributed."""
    (tmp_path / "sync-manifest.yaml").write_text(BLOCK_MANIFEST, encoding="utf-8")
    (tmp_path / "block" / "skills" / "third-party").mkdir(parents=True)
    return tmp_path / "block" / "skills" / "third-party"


def test_incomplete_source_md_names_the_missing_fields(tmp_path):
    skill = _block_toolkit(tmp_path)
    (skill / "SOURCE.md").write_text("- upstream: https://example.invalid/x\n", encoding="utf-8")
    result = AuditResult()
    check_vendor_provenance(tmp_path, result)
    message = result.findings[0].message
    assert "commit" in message and "license" in message and "imported" in message


def test_mit_content_without_a_license_file_is_reported(tmp_path):
    skill = _block_toolkit(tmp_path)
    (skill / "SOURCE.md").write_text(COMPLETE_SOURCE_MD, encoding="utf-8")
    result = AuditResult()
    check_vendor_provenance(tmp_path, result)
    assert "LICENSE" in result.findings[0].message


def test_complete_provenance_with_license_passes(tmp_path):
    skill = _block_toolkit(tmp_path)
    (skill / "SOURCE.md").write_text(COMPLETE_SOURCE_MD, encoding="utf-8")
    (skill / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    result = AuditResult()
    check_vendor_provenance(tmp_path, result)
    assert result.findings == []


def test_a_block_with_no_third_party_content_is_not_a_finding(tmp_path):
    _block_toolkit(tmp_path)
    result = AuditResult()
    check_vendor_provenance(tmp_path, result)
    assert result.findings == []
