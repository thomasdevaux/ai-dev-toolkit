"""Stack detection from marker files, driven by each manifest entry's own
`detect:`/`detect_all:` fields — the manifest is the single source of truth for
what marks a stack, instead of a second, hand-kept list here. Suggestions only
— never synced without explicit confirmation.

Two shapes, because two kinds of stack exist:

- `detect:` — any one marker is enough. Right when the marker names a
  language and the block is that language's entry point (`pyproject.toml`,
  `*.csproj`).
- `detect_all:` — every marker must be present, in the same directory. Right
  when the block is about one framework inside a language, where the language
  marker alone would fire on every project (`Cargo.toml` **and** `src-tauri/`).

Both are searched at the project root and one level below it, and nowhere
deeper: a marker two levels down belongs to a sub-project, not to the project
being scanned.
"""
from __future__ import annotations

from pathlib import Path

from .manifest import SyncEntry, load_manifest

# Directories the search never looks inside: build output and vendored
# dependencies that could otherwise bury an unrelated marker file and trigger
# a false-positive suggestion.
_EXCLUDED_DIR_NAMES = {
    "node_modules", "vendor", ".git", "bin", "obj", "dist", "build",
    "__pycache__", ".venv", "venv",
}


def _candidate_dirs(project_dir: Path) -> list[Path]:
    """The project root plus its immediate subdirectories — the only places a
    marker counts. Markers of a `detect_all:` set are required to sit in the
    same candidate directory, so a Cargo.toml in one subproject and a
    src-tauri/ in another never combine into a false match."""
    if not project_dir.is_dir():
        return []
    subdirs = [
        p for p in project_dir.iterdir()
        if p.is_dir() and p.name not in _EXCLUDED_DIR_NAMES
    ]
    return [project_dir, *subdirs]


def _marker_in_dir(directory: Path, marker: str) -> bool:
    """A marker is a filename, a glob, or a directory name — `src-tauri/` marks
    a Tauri app exactly as `wails.json` marks a Wails one, so existence is what
    is tested, not file-ness."""
    if "*" in marker:
        return any(directory.glob(marker))
    return (directory / marker).exists()


def _matches(project_dir: Path, entry: SyncEntry) -> bool:
    for directory in _candidate_dirs(project_dir):
        if entry.detect and any(_marker_in_dir(directory, m) for m in entry.detect):
            return True
        if entry.detect_all and all(_marker_in_dir(directory, m) for m in entry.detect_all):
            return True
    return False


def detect_stacks(project_dir: Path, toolkit_root: Path) -> list[str]:
    entries = load_manifest(toolkit_root)
    found = [
        entry.id
        for entry in entries.values()
        if (entry.detect or entry.detect_all) and _matches(project_dir, entry)
    ]
    return sorted(found)
