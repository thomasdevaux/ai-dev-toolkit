"""Lint checks for the toolkit's block layout: paths: overlap between
rule files, the character budgets on rules/*.md, and choice-group
integrity in sync-manifest.yaml."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.sync.manifest import VALID_SCOPES, SyncEntry, load_manifest

# Characters, not lines. A blank line or a re-wrapped paragraph costs a full
# line of budget but almost no context, so a line cap taxes readable
# formatting and rewards re-wrapping prose over actually cutting it.
MAX_RULE_FILE_CHARS = 4_000
MAX_SESSION_RULES_CHARS = 20_000

# A rule with `paths:` frontmatter is not paid at session start: the harness
# loads it only once Claude reads a file the pattern matches. So it belongs
# to a different budget than the always-on set — and to a larger one, since
# no single session pays more than the languages it actually touches, while
# the worst case below sums every tech-stack block at once. The cap still
# exists: a stack that accumulates scoped rules is spending a session's
# attention the moment that language is opened, which is most of them.
MAX_SCOPED_RULES_CHARS = 16_000

# A skill's body is uncapped on purpose — it loads on demand. Its
# `description:` does not: that line is what the harness reads to decide
# whether to offer the skill at all, so it sits in context for every session
# where the block is synced. It is the only part of a skill that behaves like
# a rule, and the only part worth budgeting.
MAX_SKILL_DESCRIPTION_CHARS = 500


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


def _rule_files(toolkit_root: Path, entry: SyncEntry) -> list[Path]:
    rules_dir = toolkit_root / entry.source / "rules"
    if not rules_dir.is_dir():
        return []
    return sorted(rules_dir.glob("*.md"))


def _split_chars(paths: list[Path]) -> tuple[int, int]:
    """Characters in a block's rules, split by how they load: rules with no
    `paths:` frontmatter (always-on, read at session start) and rules with
    it (read only when Claude opens a matching file)."""
    unscoped = scoped = 0
    for path in paths:
        size = len(path.read_text(encoding="utf-8"))
        if _read_frontmatter_paths(path):
            scoped += size
        else:
            unscoped += size
    return unscoped, scoped


def check_rule_file_size(toolkit_root: Path, result: AuditResult) -> None:
    """One cap per rule file, deliberately not per block. A cumulative block
    budget makes unrelated rules compete for room — an ADR rule trading lines
    against a git-workflow rule it has no editorial relationship with — which
    distorts what gets written without bounding what a session actually
    pays. That second job belongs to check_session_rules_size."""
    seen: set[str] = set()
    for entry in _block_entries(toolkit_root):
        if entry.source in seen:
            continue
        seen.add(entry.source)
        for md_file in _rule_files(toolkit_root, entry):
            size = len(md_file.read_text(encoding="utf-8"))
            if size > MAX_RULE_FILE_CHARS:
                rel = md_file.relative_to(toolkit_root).as_posix()
                result.add(
                    "rules-size",
                    f"{rel}: {size} chars, over the {MAX_RULE_FILE_CHARS}-char "
                    f"per-rule cap. A rule is read whole the moment it loads; "
                    f"move detail into a skill, which loads on demand.",
                )


@dataclass
class ScopeTotals:
    """Worst-case rule characters for one scope, split by how they load."""
    unscoped: int = 0
    scoped: int = 0
    # (block label, unscoped chars, scoped chars), largest contributors first
    # at report time.
    breakdown: list[tuple[str, int, int]] = field(default_factory=list)


def _scope_rules_total(toolkit_root: Path, scope: str) -> ScopeTotals:
    """Worst-case rules total for a single scope: every baseline/tech-stack
    block plus the largest member of each choice-group (exactly one is
    always adopted). The suggested tier is a deliberate opt-in and stays
    out of the worst case.

    A choice-group's largest member is picked on its always-on characters:
    that is the number the session-start budget defends, and no group has
    scoped rules today."""
    entries = [e for e in _block_entries(toolkit_root) if e.scope == scope]
    # A source appears once per scope even if two entries share it.
    seen: set[str] = set()
    totals = ScopeTotals()
    groups: dict[str, list[tuple[str, int, int]]] = {}

    for entry in entries:
        if entry.source in seen:
            continue
        unscoped, scoped = _split_chars(_rule_files(toolkit_root, entry))
        group = entry.choice_group
        if group:
            groups.setdefault(group, []).append((entry.id, unscoped, scoped))
            continue
        seen.add(entry.source)
        if (unscoped or scoped) and entry.tier in ("baseline", "tech-stack"):
            totals.unscoped += unscoped
            totals.scoped += scoped
            totals.breakdown.append((entry.id, unscoped, scoped))

    for group, members in sorted(groups.items()):
        worst_id, worst_unscoped, worst_scoped = max(members, key=lambda m: m[1])
        if worst_unscoped or worst_scoped:
            totals.unscoped += worst_unscoped
            totals.scoped += worst_scoped
            totals.breakdown.append(
                (f"{worst_id} (largest of '{group}')", worst_unscoped, worst_scoped)
            )

    return totals


def _budget_detail(scope_results: dict[str, ScopeTotals], scoped: bool) -> str:
    """Per-scope breakdown for one of the two budgets, blocks contributing
    nothing to it omitted."""
    parts = []
    for scope, totals in scope_results.items():
        contributors = [
            f"{name} {s if scoped else u}"
            for name, u, s in totals.breakdown
            if (s if scoped else u)
        ]
        total = totals.scoped if scoped else totals.unscoped
        parts.append(f"{scope!r} {total} ({', '.join(contributors)})")
    return "; ".join(parts)


def check_session_rules_size(toolkit_root: Path, result: AuditResult) -> None:
    """What a session pays is project scope *and* user scope, loaded
    together — not either one alone. A source deployed to both scopes
    (common/ is the current example) lands as separate bytes in two
    directories and both get read, so it is counted once per scope, i.e.
    twice in the combined total. The worst realistic combination per scope
    is computable from the manifest: every baseline block, plus the largest
    member of each choice-group (exactly one is always adopted), plus any
    tech-stack block (auto-detected, and a polyglot repo can pull several).
    The suggested tier is a deliberate opt-in and stays out of the worst
    case.

    Two budgets, because the two kinds of rule are not paid at the same
    time. Rules with no `paths:` are read at session start, every session,
    and are what MAX_SESSION_RULES_CHARS defends. Rules with `paths:` are
    read only when a matching file is opened, so summing every tech-stack
    block's worth of them describes a session nobody has — they get the
    looser MAX_SCOPED_RULES_CHARS instead. Keeping them in one number would
    make a Python style rule compete for room against a Go one it can never
    be loaded beside."""
    scope_results = {scope: _scope_rules_total(toolkit_root, scope) for scope in sorted(VALID_SCOPES)}
    unscoped_total = sum(t.unscoped for t in scope_results.values())
    scoped_total = sum(t.scoped for t in scope_results.values())

    if unscoped_total > MAX_SESSION_RULES_CHARS:
        result.add(
            "rules-size",
            f"combined session (project + user) worst-case always-on rule set "
            f"totals {unscoped_total} chars, over the {MAX_SESSION_RULES_CHARS}"
            f"-char session budget — {_budget_detail(scope_results, scoped=False)}.",
        )

    if scoped_total > MAX_SCOPED_RULES_CHARS:
        result.add(
            "rules-size",
            f"combined session (project + user) worst-case `paths:`-scoped rule "
            f"set totals {scoped_total} chars, over the {MAX_SCOPED_RULES_CHARS}"
            f"-char scoped budget — {_budget_detail(scope_results, scoped=True)}.",
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


VENDOR_SOURCE_FIELDS = ("upstream:", "commit:", "license:", "imported:")


def check_vendor_provenance(toolkit_root: Path, result: AuditResult) -> None:
    """Wherever a SOURCE.md sits, it is complete. Third-party content copied
    into a block is indistinguishable from content we wrote unless its
    provenance is recorded next to it — which is exactly what turns an import
    into a black box six months later.

    Scoped to blocks that are actually syncable, since that's the content that
    gets redistributed into other people's repositories."""
    for entry in _block_entries(toolkit_root):
        block_root = toolkit_root / entry.source
        if not block_root.is_dir():
            continue
        for source_md in sorted(block_root.rglob("SOURCE.md")):
            rel = source_md.relative_to(toolkit_root).as_posix()
            text = source_md.read_text(encoding="utf-8").lower()
            missing = [f.rstrip(":") for f in VENDOR_SOURCE_FIELDS if f not in text]
            if missing:
                result.add("vendor", f"{rel}: missing field(s) {', '.join(missing)}.")
            license_file = source_md.parent / "LICENSE"
            if "license:" in text and "mit" in text and not license_file.is_file():
                result.add(
                    "vendor",
                    f"{rel}: declares an MIT license but no LICENSE file sits beside it — "
                    f"MIT requires the notice to travel with every copy.",
                )


def check_version_banner(toolkit_root: Path, result: AuditResult) -> None:
    """VERSION is the toolkit's single source of truth for its own version
    number. self-check's companyAnnouncements banner quotes that number as
    plain text (the client renders it as-is, no templating available), so
    nothing enforces the two staying in sync except this check — catches a
    VERSION bump that forgot to touch the banner, or vice versa."""
    version_file = toolkit_root / "VERSION"
    if not version_file.is_file():
        result.add("version", "no VERSION file at toolkit root.")
        return
    version = version_file.read_text(encoding="utf-8").strip()
    if not version:
        result.add("version", "VERSION file is empty.")
        return

    marker = f"v{version}"
    manifest = load_manifest(toolkit_root)
    for entry in manifest.values():
        for text in entry.settings_patch.get("companyAnnouncements", []):
            if marker not in text:
                result.add(
                    "version",
                    f"{entry.id}: companyAnnouncements banner doesn't mention "
                    f"{marker} (from VERSION) — update it alongside VERSION bumps.",
                )


def check_summaries(toolkit_root: Path, result: AuditResult) -> None:
    """`summary:` is the single source for both the status report's suggested
    section and the user-guide catalog, so a missing one silently degrades
    both."""
    manifest = load_manifest(toolkit_root)
    for entry_id in sorted(manifest):
        if not manifest[entry_id].summary.strip():
            result.add("summary", f"{entry_id}: no 'summary:' in sync-manifest.yaml.")


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_FIELD_RE = re.compile(r"^(?P<key>[A-Za-z][\w-]*):\s*(?P<fold>[>|][-+]?)?[ \t]*(?P<inline>.*)$")


def read_frontmatter(md_path: Path) -> dict[str, str] | None:
    """Frontmatter as flat key -> string, enough for the scalar fields a
    SKILL.md declares. Folded/literal block scalars (`description: >`) are
    joined into one string, since `caveman` uses that form and a parser that
    only understood `key: value` would read its description as empty."""
    match = _FRONTMATTER_RE.match(md_path.read_text(encoding="utf-8"))
    if match is None:
        return None

    fields: dict[str, str] = {}
    key: str | None = None
    for line in match.group(1).splitlines():
        if line.strip() and not line[0].isspace():
            field_match = _FIELD_RE.match(line)
            if field_match is None:
                key = None
                continue
            key = field_match.group("key")
            fields[key] = field_match.group("inline").strip()
        elif key is not None and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def _skill_files(toolkit_root: Path) -> list[Path]:
    """Every SKILL.md in a syncable block — the ones redistributed into other
    people's repositories. incubator/ and handbook/ are never synced and are
    reached by no manifest entry, so they never appear here."""
    seen: set[str] = set()
    skills: list[Path] = []
    for entry in _block_entries(toolkit_root):
        if entry.source in seen:
            continue
        seen.add(entry.source)
        skills_dir = toolkit_root / entry.source / "skills"
        if skills_dir.is_dir():
            skills.extend(sorted(skills_dir.glob("*/SKILL.md")))
    return skills


def check_skills(toolkit_root: Path, result: AuditResult) -> None:
    """Nothing else validates a SKILL.md. The harness routes on the `name:`
    field while humans navigate by directory, so the two silently diverging
    means a rename that only half happened; a missing `description:` means a
    skill nothing can decide to invoke; and an obese one taxes every session
    the block is synced into."""
    names: dict[str, str] = {}
    for skill_md in _skill_files(toolkit_root):
        rel = skill_md.relative_to(toolkit_root).as_posix()
        directory = skill_md.parent.name
        fields = read_frontmatter(skill_md)
        if fields is None:
            result.add("skills", f"{rel}: no YAML frontmatter — the harness can't register it.")
            continue

        name = fields.get("name", "").strip()
        if not name:
            result.add("skills", f"{rel}: no 'name:' in frontmatter.")
        elif name != directory:
            result.add(
                "skills",
                f"{rel}: name '{name}' doesn't match its directory '{directory}' — "
                f"the harness routes on the name, humans navigate by directory.",
            )
        elif name in names:
            result.add(
                "skills",
                f"{rel}: skill name '{name}' is already declared by {names[name]} — "
                f"two skills with one name make invocation ambiguous.",
            )
        else:
            names[name] = rel

        description = fields.get("description", "").strip()
        if not description:
            result.add(
                "skills",
                f"{rel}: no 'description:' — that field is what decides whether the "
                f"skill is ever offered, so an empty one makes it unreachable.",
            )
        elif len(description) > MAX_SKILL_DESCRIPTION_CHARS:
            result.add(
                "skills",
                f"{rel}: description is {len(description)} chars, over the "
                f"{MAX_SKILL_DESCRIPTION_CHARS}-char cap. It sits in context for every "
                f"session the block is synced into — move the detail into the body, "
                f"which loads on demand.",
            )


def _block_md_files(toolkit_root: Path, subdir: str) -> list[Path]:
    """Every `<block>/<subdir>/*.md` in a syncable block. Same de-duplication
    as _skill_files: a block synced at both project and user scope appears
    twice in the manifest but is one directory on disk."""
    seen: set[str] = set()
    files: list[Path] = []
    for entry in _block_entries(toolkit_root):
        if entry.source in seen:
            continue
        seen.add(entry.source)
        directory = toolkit_root / entry.source / subdir
        if directory.is_dir():
            files.extend(sorted(directory.glob("*.md")))
    return files


def check_commands(toolkit_root: Path, result: AuditResult) -> None:
    """A command's `model:` is the whole point of checking commands at all.
    Omitting it doesn't fail loudly — the command silently runs on whatever
    the session is using, which is the most expensive model available. For the
    mechanical commands this toolkit ships (`/toolkit-sync` and friends) that
    is pure waste, so the field is required to be *present*, not required to
    be any particular value: pinning `sonnet` deliberately is fine, inheriting
    by omission is not."""
    for command_md in _block_md_files(toolkit_root, "commands"):
        rel = command_md.relative_to(toolkit_root).as_posix()
        fields = read_frontmatter(command_md)
        if fields is None:
            result.add("commands", f"{rel}: no YAML frontmatter — the harness can't register it.")
            continue
        if not fields.get("description", "").strip():
            result.add(
                "commands",
                f"{rel}: no 'description:' — that line is the whole of what the user "
                f"sees in the command list.",
            )
        if not fields.get("model", "").strip():
            result.add(
                "commands",
                f"{rel}: no 'model:' — a command without one inherits the session's "
                f"model, the most expensive default there is. State it explicitly, "
                f"whichever tier you pick (see docs/maintaining.md, "
                f"'Which model a block's entry point runs on').",
            )


def check_agents(toolkit_root: Path, result: AuditResult) -> None:
    """Same argument as check_commands for `model:`, plus the name/filename
    pairing check that check_skills makes for name/directory — the harness
    routes on the frontmatter name while humans navigate by filename, so the
    two diverging is a rename that only half happened."""
    names: dict[str, str] = {}
    for agent_md in _block_md_files(toolkit_root, "agents"):
        rel = agent_md.relative_to(toolkit_root).as_posix()
        fields = read_frontmatter(agent_md)
        if fields is None:
            result.add("agents", f"{rel}: no YAML frontmatter — the harness can't register it.")
            continue

        name = fields.get("name", "").strip()
        if not name:
            result.add("agents", f"{rel}: no 'name:' in frontmatter.")
        elif name != agent_md.stem:
            result.add(
                "agents",
                f"{rel}: name '{name}' doesn't match its filename '{agent_md.stem}' — "
                f"the harness routes on the name, humans navigate by the file.",
            )
        elif name in names:
            result.add(
                "agents",
                f"{rel}: agent name '{name}' is already declared by {names[name]} — "
                f"two agents with one name make delegation ambiguous.",
            )
        else:
            names[name] = rel

        description = fields.get("description", "").strip()
        if not description:
            result.add(
                "agents",
                f"{rel}: no 'description:' — that field is what decides whether the "
                f"agent is ever delegated to, so an empty one makes it unreachable.",
            )
        elif len(description) > MAX_SKILL_DESCRIPTION_CHARS:
            result.add(
                "agents",
                f"{rel}: description is {len(description)} chars, over the "
                f"{MAX_SKILL_DESCRIPTION_CHARS}-char cap. Like a skill's, it sits in "
                f"context for every session the block is synced into — move the detail "
                f"into the body.",
            )

        if not fields.get("model", "").strip():
            result.add(
                "agents",
                f"{rel}: no 'model:' — an agent exists to run a sub-task on a model "
                f"chosen for it, so leaving that to inheritance defeats the point "
                f"(see docs/maintaining.md, "
                f"'Which model a block's entry point runs on').",
            )


# Backticked tokens shaped like a manifest entry id. Narrow on purpose: a
# looser pattern would flag ordinary prose, and a check nobody trusts gets
# muted rather than fixed.
_ENTRY_ID_RE = re.compile(r"`((?:tech-stack|project-type|common)-[a-z0-9-]+)`")


def check_entry_id_references(toolkit_root: Path, result: AuditResult) -> None:
    """Markdown that names a block by id — a skill telling the user which
    block to sync next — must name one that exists. These handoffs are the
    first thing a block rename breaks, and the last thing anyone re-reads."""
    manifest = load_manifest(toolkit_root)
    seen: set[str] = set()
    for entry in _block_entries(toolkit_root):
        if entry.source in seen:
            continue
        seen.add(entry.source)
        block_root = toolkit_root / entry.source
        if not block_root.is_dir():
            continue
        for md_file in sorted(block_root.rglob("*.md")):
            rel = md_file.relative_to(toolkit_root).as_posix()
            referenced = set(_ENTRY_ID_RE.findall(md_file.read_text(encoding="utf-8")))
            for entry_id in sorted(referenced - set(manifest)):
                result.add(
                    "skills",
                    f"{rel}: references block '{entry_id}', which is not an entry id "
                    f"in sync-manifest.yaml.",
                )


def run_all(toolkit_root: Path) -> AuditResult:
    result = AuditResult()
    check_paths_overlap(toolkit_root, result)
    check_rule_file_size(toolkit_root, result)
    check_session_rules_size(toolkit_root, result)
    check_choice_groups(toolkit_root, result)
    check_vendor_provenance(toolkit_root, result)
    check_skills(toolkit_root, result)
    check_commands(toolkit_root, result)
    check_agents(toolkit_root, result)
    check_entry_id_references(toolkit_root, result)
    check_summaries(toolkit_root, result)
    check_version_banner(toolkit_root, result)
    return result
