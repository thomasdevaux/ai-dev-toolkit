from pathlib import Path

from tools.audit.checks import (
    MAX_RULE_FILE_CHARS,
    AuditResult,
    MAX_SCOPED_RULES_CHARS,
    MAX_SKILL_DESCRIPTION_CHARS,
    check_agents,
    check_commands,
    check_entry_id_references,
    check_rule_file_size,
    check_session_rules_size,
    check_skills,
    check_summaries,
    check_vendor_provenance,
)

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


RULES_MANIFEST = """
- id: base
  type: file
  source: base
  target: .claude/
  scope: project
  tier: baseline
  summary: baseline rules

- id: base-user
  type: file
  source: base
  target: ~/.claude/
  scope: user
  tier: baseline
  summary: the same rules, user scope

- id: light
  type: file
  source: light
  target: .claude/
  scope: project
  tier: choice-group:project-type
  summary: the small profile

- id: heavy
  type: file
  source: heavy
  target: .claude/
  scope: project
  tier: choice-group:project-type
  summary: the large profile

- id: stack-a
  type: file
  source: stack-a
  target: .claude/
  scope: project
  tier: tech-stack
  detect: ["a.toml"]
  summary: one language's block

- id: stack-b
  type: file
  source: stack-b
  target: .claude/
  scope: project
  tier: tech-stack
  detect: ["b.toml"]
  summary: another language's block
"""

SCOPED = '---\npaths:\n  - "**/*.py"\n---\n'


def _rules_toolkit(tmp_path: Path, files: dict[str, str]) -> Path:
    (tmp_path / "sync-manifest.yaml").write_text(RULES_MANIFEST, encoding="utf-8")
    for relpath, content in files.items():
        path = tmp_path / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def test_oversized_rule_file_is_reported(tmp_path):
    _rules_toolkit(tmp_path, {"base/rules/big.md": "x" * (MAX_RULE_FILE_CHARS + 1)})
    result = AuditResult()
    check_rule_file_size(tmp_path, result)
    assert "base/rules/big.md" in result.findings[0].message


def test_blank_lines_and_wrapping_do_not_consume_the_budget(tmp_path):
    """The budget is in characters precisely so that readable formatting is
    free: this file would blow any per-block line cap while costing almost
    no context at all."""
    _rules_toolkit(tmp_path, {"base/rules/airy.md": "- a rule\n\n" * 400})
    result = AuditResult()
    check_rule_file_size(tmp_path, result)
    assert result.findings == []


def test_session_budget_sums_across_blocks_and_takes_the_largest_profile(tmp_path):
    """No single block is over any cap; what breaks the budget is the set a
    project actually syncs — which the old per-block cap could not see."""
    _rules_toolkit(
        tmp_path,
        {
            "base/rules/a.md": "x" * 11_000,
            "light/rules/b.md": "x" * 4_000,
            "heavy/rules/c.md": "x" * 12_000,
        },
    )
    result = AuditResult()
    check_session_rules_size(tmp_path, result)
    message = next(f.message for f in result.findings if "'project'" in f.message)
    assert "23000" in message
    assert "heavy" in message and "light" not in message


def test_session_budget_counts_a_shared_source_once_per_scope(tmp_path):
    """`base` is synced to both scopes from one source (common/ does this in
    production): the same bytes land in two directories and both get read,
    so the combined session total counts them twice — once per scope. Each
    scope alone stays under budget; only the sum trips it."""
    _rules_toolkit(
        tmp_path,
        {
            "base/rules/a.md": "x" * 11_000,
            "light/rules/b.md": "x" * 1_000,
            "heavy/rules/c.md": "x" * 1_000,
        },
    )
    result = AuditResult()
    check_session_rules_size(tmp_path, result)
    assert len(result.findings) == 1
    message = result.findings[0].message
    assert "23000" in message
    assert "'project'" in message and "'user'" in message


def test_a_scoped_rule_is_not_charged_to_the_session_start_budget(tmp_path):
    """A rule with `paths:` is read only once Claude opens a matching file,
    so it must not compete for room with what loads at every session start.
    Here the two totals together would trip the old single budget; the
    always-on half alone does not."""
    _rules_toolkit(
        tmp_path,
        {
            "base/rules/a.md": "x" * 9_000,
            "stack-a/rules/style.md": SCOPED + "x" * 6_000,
        },
    )
    result = AuditResult()
    check_session_rules_size(tmp_path, result)
    assert result.findings == []


def test_scoped_rules_sum_into_their_own_budget(tmp_path):
    """The scoped budget still bounds accumulation: no session loads two
    languages' style rules at once, but the cap keeps any one of them from
    growing without limit."""
    _rules_toolkit(
        tmp_path,
        {
            "base/rules/a.md": "x" * 1_000,
            "stack-a/rules/style.md": SCOPED + "x" * (MAX_SCOPED_RULES_CHARS // 2),
            "stack-b/rules/style.md": SCOPED + "x" * (MAX_SCOPED_RULES_CHARS // 2),
        },
    )
    result = AuditResult()
    check_session_rules_size(tmp_path, result)
    assert len(result.findings) == 1
    message = result.findings[0].message
    assert "scoped" in message
    # `base` contributes only always-on characters, so it stays out of this
    # budget's breakdown entirely.
    assert "stack-a" in message and "stack-b" in message and "base" not in message


# --- skills ---------------------------------------------------------------

SKILLS_MANIFEST = """
- id: block
  type: file
  source: block
  target: .claude/
  scope: project
  tier: baseline
  summary: a block

- id: tech-stack-python
  type: file
  source: stack
  target: .claude/
  scope: project
  tier: tech-stack
  summary: a stack
"""


def _skill(tmp_path: Path, directory: str, frontmatter: str, body: str = "\n# x\n") -> Path:
    (tmp_path / "sync-manifest.yaml").write_text(SKILLS_MANIFEST, encoding="utf-8")
    skill_dir = tmp_path / "block" / "skills" / directory
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return skill_dir


def _messages(result: AuditResult) -> list[str]:
    return [f.message for f in result.findings]


def test_skill_name_matching_its_directory_passes(tmp_path):
    _skill(tmp_path, "good-skill", "name: good-skill\ndescription: does a thing")
    result = AuditResult()
    check_skills(tmp_path, result)
    assert result.findings == []


def test_skill_name_diverging_from_its_directory_is_reported(tmp_path):
    _skill(tmp_path, "on-disk", "name: in-frontmatter\ndescription: does a thing")
    result = AuditResult()
    check_skills(tmp_path, result)
    assert any("doesn't match its directory" in m for m in _messages(result))


def test_skill_without_a_description_is_reported(tmp_path):
    _skill(tmp_path, "mute", "name: mute")
    result = AuditResult()
    check_skills(tmp_path, result)
    assert any("no 'description:'" in m for m in _messages(result))


def test_oversized_skill_description_is_reported(tmp_path):
    _skill(tmp_path, "verbose", f"name: verbose\ndescription: {'x' * (MAX_SKILL_DESCRIPTION_CHARS + 1)}")
    result = AuditResult()
    check_skills(tmp_path, result)
    assert any("over the" in m for m in _messages(result))


def test_folded_block_description_is_read_not_treated_as_empty(tmp_path):
    """`description: >` is how caveman declares its own — a parser that only
    understood `key: value` would report it as missing."""
    _skill(tmp_path, "folded", "name: folded\ndescription: >\n  first line\n  second line")
    result = AuditResult()
    check_skills(tmp_path, result)
    assert result.findings == []


def test_skill_without_frontmatter_is_reported(tmp_path):
    (tmp_path / "sync-manifest.yaml").write_text(SKILLS_MANIFEST, encoding="utf-8")
    skill_dir = tmp_path / "block" / "skills" / "bare"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# just a heading\n", encoding="utf-8")
    result = AuditResult()
    check_skills(tmp_path, result)
    assert any("no YAML frontmatter" in m for m in _messages(result))


def test_duplicate_skill_names_across_directories_are_reported(tmp_path):
    _skill(tmp_path, "twin", "name: twin\ndescription: one")
    stack_dir = tmp_path / "stack" / "skills" / "twin"
    stack_dir.mkdir(parents=True)
    (stack_dir / "SKILL.md").write_text("---\nname: twin\ndescription: two\n---\n", encoding="utf-8")
    result = AuditResult()
    check_skills(tmp_path, result)
    assert any("already declared by" in m for m in _messages(result))


def _block_md(tmp_path: Path, subdir: str, filename: str, frontmatter: str) -> Path:
    (tmp_path / "sync-manifest.yaml").write_text(SKILLS_MANIFEST, encoding="utf-8")
    directory = tmp_path / "block" / subdir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(f"---\n{frontmatter}\n---\n\nbody\n", encoding="utf-8")
    return path


def test_command_with_a_description_and_a_model_passes(tmp_path):
    _block_md(tmp_path, "commands", "thing.md", "description: does a thing\nmodel: haiku")
    result = AuditResult()
    check_commands(tmp_path, result)
    assert result.findings == []


def test_command_without_a_model_is_reported(tmp_path):
    _block_md(tmp_path, "commands", "thing.md", "description: does a thing")
    result = AuditResult()
    check_commands(tmp_path, result)
    assert any("no 'model:'" in m for m in _messages(result))


def test_command_pinned_to_a_non_haiku_model_passes(tmp_path):
    """The check requires the field to be stated, not to hold any given value:
    a deliberate `sonnet` is a decision, an omission is an accident."""
    _block_md(tmp_path, "commands", "thing.md", "description: does a thing\nmodel: sonnet")
    result = AuditResult()
    check_commands(tmp_path, result)
    assert result.findings == []


def test_command_without_a_description_is_reported(tmp_path):
    _block_md(tmp_path, "commands", "thing.md", "model: haiku")
    result = AuditResult()
    check_commands(tmp_path, result)
    assert any("no 'description:'" in m for m in _messages(result))


def test_command_without_frontmatter_is_reported(tmp_path):
    (tmp_path / "sync-manifest.yaml").write_text(SKILLS_MANIFEST, encoding="utf-8")
    directory = tmp_path / "block" / "commands"
    directory.mkdir(parents=True)
    (directory / "bare.md").write_text("# just a heading\n", encoding="utf-8")
    result = AuditResult()
    check_commands(tmp_path, result)
    assert any("no YAML frontmatter" in m for m in _messages(result))


def test_agent_matching_its_filename_passes(tmp_path):
    _block_md(tmp_path, "agents", "linter.md", "name: linter\ndescription: lints\nmodel: haiku")
    result = AuditResult()
    check_agents(tmp_path, result)
    assert result.findings == []


def test_agent_name_diverging_from_its_filename_is_reported(tmp_path):
    _block_md(tmp_path, "agents", "on-disk.md", "name: in-frontmatter\ndescription: x\nmodel: haiku")
    result = AuditResult()
    check_agents(tmp_path, result)
    assert any("doesn't match its filename" in m for m in _messages(result))


def test_agent_without_a_model_is_reported(tmp_path):
    _block_md(tmp_path, "agents", "linter.md", "name: linter\ndescription: lints")
    result = AuditResult()
    check_agents(tmp_path, result)
    assert any("no 'model:'" in m for m in _messages(result))


def test_oversized_agent_description_is_reported(tmp_path):
    _block_md(
        tmp_path,
        "agents",
        "verbose.md",
        f"name: verbose\nmodel: haiku\ndescription: {'x' * (MAX_SKILL_DESCRIPTION_CHARS + 1)}",
    )
    result = AuditResult()
    check_agents(tmp_path, result)
    assert any("over the" in m for m in _messages(result))


def test_duplicate_agent_names_across_blocks_are_reported(tmp_path):
    _block_md(tmp_path, "agents", "twin.md", "name: twin\ndescription: one\nmodel: haiku")
    stack_dir = tmp_path / "stack" / "agents"
    stack_dir.mkdir(parents=True)
    (stack_dir / "twin.md").write_text(
        "---\nname: twin\ndescription: two\nmodel: haiku\n---\n", encoding="utf-8"
    )
    result = AuditResult()
    check_agents(tmp_path, result)
    assert any("already declared by" in m for m in _messages(result))


def test_reference_to_a_real_block_id_passes(tmp_path):
    _skill(tmp_path, "router", "name: router\ndescription: routes", "\nSync `tech-stack-python` next.\n")
    result = AuditResult()
    check_entry_id_references(tmp_path, result)
    assert result.findings == []


def test_reference_to_an_unknown_block_id_is_reported(tmp_path):
    _skill(tmp_path, "router", "name: router\ndescription: routes", "\nSync `tech-stack-elixir` next.\n")
    result = AuditResult()
    check_entry_id_references(tmp_path, result)
    assert any("tech-stack-elixir" in m for m in _messages(result))
