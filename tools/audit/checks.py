"""Lint checks for the toolkit's block layout: paths: overlap between
rule files, the 200-cumulative-line cap on a block's rules/*.md, and
choice-group integrity in sync-manifest.yaml."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

from tools.sync.manifest import SyncEntry, load_manifest

MAX_RULES_LINES = 200


@dataclass
class Finding:
    check: str
    message: str


@dataclass
class AuditResult:
    findings: list[Finding] = field(default_factory=list)

    def add(self, check: str, message: str) -> None:
        self.findings.append(Finding(check, message))


def _collapse(pattern: str) -> str:
    return pattern.replace("**", "*")


def _sample(pattern: str) -> str:
    return _collapse(pattern).replace("*", "X")


def patterns_overlap(a: str, b: str) -> bool:
    """Approximate, deliberately over-inclusive glob-overlap check: a
    single '*' is treated as matching across '/' too (fnmatch has no
    path-separator concept), so this can flag pairs a stricter path-aware
    matcher wouldn't. That's the right direction for a lint tool meant to
    be reviewed by a human, per the original audit-plugins design."""
    collapsed_a, collapsed_b = _collapse(a), _collapse(b)
    sample_a, sample_b = _sample(a), _sample(b)
    return fnmatch.fnmatchcase(sample_a, collapsed_b) or fnmatch.fnmatchcase(sample_b, collapsed_a)


def _read_frontmatter_paths(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    frontmatter = text[3:end]
    paths: list[str] = []
    in_paths = False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith("paths:"):
            in_paths = True
            continue
        if in_paths:
            if stripped.startswith("- "):
                paths.append(stripped[2:].strip().strip('"').strip("'"))
                continue
            break
    return paths


def _block_entries(toolkit_root: Path) -> list[SyncEntry]:
    manifest = load_manifest(toolkit_root)
    return [e for e in manifest.values() if e.type == "file"]


def check_paths_overlap(toolkit_root: Path, result: AuditResult) -> None:
    # block id -> list of (rule file relpath, pattern)
    block_patterns: dict[str, list[tuple[str, str]]] = {}
    for entry in _block_entries(toolkit_root):
        rules_dir = toolkit_root / entry.source / "rules"
        if not rules_dir.is_dir():
            continue
        patterns = []
        for md_file in sorted(rules_dir.glob("*.md")):
            for pattern in _read_frontmatter_paths(md_file):
                patterns.append((md_file.name, pattern))
        if patterns:
            block_patterns[entry.id] = patterns

    block_ids = sorted(block_patterns)
    for i, block_a in enumerate(block_ids):
        for block_b in block_ids[i + 1:]:
            for file_a, pattern_a in block_patterns[block_a]:
                for file_b, pattern_b in block_patterns[block_b]:
                    if patterns_overlap(pattern_a, pattern_b):
                        result.add(
                            "paths-overlap",
                            f"{block_a}/rules/{file_a} ({pattern_a!r}) overlaps "
                            f"{block_b}/rules/{file_b} ({pattern_b!r}) — confirm the "
                            f"two rules don't contradict each other.",
                        )


def check_rules_size(toolkit_root: Path, result: AuditResult) -> None:
    for entry in _block_entries(toolkit_root):
        rules_dir = toolkit_root / entry.source / "rules"
        if not rules_dir.is_dir():
            continue
        total = 0
        for md_file in rules_dir.glob("*.md"):
            total += len(md_file.read_text(encoding="utf-8").splitlines())
        if total > MAX_RULES_LINES:
            result.add(
                "rules-size",
                f"{entry.id}: rules/*.md total {total} lines, over the "
                f"{MAX_RULES_LINES}-line cap.",
            )


def check_choice_groups(toolkit_root: Path, result: AuditResult) -> None:
    manifest = load_manifest(toolkit_root)
    groups: dict[str, list[str]] = {}
    for entry in manifest.values():
        group = entry.choice_group
        if group:
            groups.setdefault(group, []).append(entry.id)

    for group, members in groups.items():
        if len(members) < 2:
            result.add(
                "choice-group",
                f"choice-group '{group}' has only one member ({members[0]}) — "
                f"a choice group needs at least two mutually exclusive variants.",
            )


def run_all(toolkit_root: Path) -> AuditResult:
    result = AuditResult()
    check_paths_overlap(toolkit_root, result)
    check_rules_size(toolkit_root, result)
    check_choice_groups(toolkit_root, result)
    return result
