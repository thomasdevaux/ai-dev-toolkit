"""File-tree diffing and the confirm-before-apply prompt."""
from __future__ import annotations

import difflib
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# Relpaths matching this pattern get chmod +x on write, since the source
# checkout's own executable bit isn't reliable across platforms (notably
# Windows) to mirror directly.
_EXECUTABLE_SUFFIXES = (".sh",)


def _wants_executable(relpath: str) -> bool:
    return relpath.startswith("hooks/") and relpath.endswith(_EXECUTABLE_SUFFIXES)


@dataclass
class FileChange:
    target_path: Path  # absolute path in the consumer project/home
    relpath: str  # path relative to the target root, for display + state keys
    is_new: bool
    content: bytes
    diff_text: str | None  # None for new files (full content shown instead)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalize_newlines(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _iter_source_files(source_root: Path, shared_files: Sequence[tuple[Path, str]] = ()):
    """Every (file, relpath) pair a block deploys: its own tree, plus any
    `shared_files:` the entry declares — a file living once in the checkout and
    landing inside several blocks' target trees (see manifest.shared_files)."""
    for shared_source, relpath in shared_files:
        if not shared_source.is_file():
            raise FileNotFoundError(f"shared_files source does not exist: {shared_source}")
        yield shared_source, relpath

    if source_root.is_file():
        yield source_root, source_root.name
        return
    for path in sorted(source_root.rglob("*")):
        if path.is_file():
            relpath = str(path.relative_to(source_root)).replace("\\", "/")
            # manifest.yaml is the block's own sync-entry definition, living
            # next to its deployable content since the per-directory split
            # (0e61696) — never content to deploy itself. Skipping it here
            # matters because several blocks share target: ~/.claude/ (or
            # .claude/): without this, whichever block synced last would
            # overwrite the destination with its own manifest.yaml, and the
            # next sync of a different block would flip it right back —
            # each sync reporting the others as freshly drifted forever.
            if relpath == "manifest.yaml":
                continue
            yield path, relpath


def source_relpaths(source_root: Path, shared_files: Sequence[tuple[Path, str]] = ()) -> set[str]:
    """Every relpath a block currently deploys — the same keys plan_file_changes
    records in the sync state, so the two can be compared to spot state entries
    whose source file no longer exists."""
    return {relpath for _path, relpath in _iter_source_files(source_root, shared_files)}


def plan_file_changes(
    source_root: Path,
    target_root: Path,
    shared_files: Sequence[tuple[Path, str]] = (),
) -> list[FileChange]:
    """Compare every file under source_root to its counterpart under
    target_root. Returns only files that differ (new or changed) —
    identical files are omitted, which is what drives idempotence.
    Equality ignores CRLF-vs-LF differences, since a source checkout's
    line endings depend on local git config (core.autocrlf) and editor
    behavior, not on actual content changes."""
    changes: list[FileChange] = []
    for source_file, relpath in _iter_source_files(source_root, shared_files):
        content = source_file.read_bytes()
        target_file = target_root / relpath

        if not target_file.is_file():
            changes.append(FileChange(target_file, relpath, True, content, None))
            continue

        existing = target_file.read_bytes()
        if _normalize_newlines(existing) == _normalize_newlines(content):
            continue

        diff_text = "".join(
            difflib.unified_diff(
                existing.decode("utf-8", errors="replace").splitlines(keepends=True),
                content.decode("utf-8", errors="replace").splitlines(keepends=True),
                fromfile=f"a/{relpath}",
                tofile=f"b/{relpath}",
            )
        )
        changes.append(FileChange(target_file, relpath, False, content, diff_text))

    return changes


def render_file_changes(changes: list[FileChange]) -> str:
    lines = []
    for change in changes:
        if change.is_new:
            lines.append(f"NEW  {change.relpath}")
        else:
            lines.append(f"DIFF {change.relpath}")
            lines.append(change.diff_text.rstrip("\n"))
    return "\n".join(lines)


def apply_file_changes(changes: list[FileChange]) -> None:
    for change in changes:
        change.target_path.parent.mkdir(parents=True, exist_ok=True)
        change.target_path.write_bytes(change.content)
        if _wants_executable(change.relpath):
            change.target_path.chmod(change.target_path.stat().st_mode | 0o111)


def confirm(prompt: str, auto_yes: bool) -> bool:
    if auto_yes:
        return True
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer == "y"
