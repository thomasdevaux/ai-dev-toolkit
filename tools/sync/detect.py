"""Stack detection from marker files. Suggestions only — never synced
without explicit confirmation.

Only stacks that have a live sync-manifest.yaml entry belong here: suggesting
`embedded-c` when no such entry exists any more would send the user after an
id `tools/sync sync` rejects. Parked stacks live in incubator/ and are
deliberately undetected.
"""
from __future__ import annotations

from pathlib import Path

# stack name -> plain marker filenames looked up at root + one level deep
MARKER_FILES: dict[str, list[str]] = {
    "python": ["pyproject.toml", "requirements.txt", "setup.py"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
}

# stack name -> glob patterns searched recursively
MARKER_GLOBS: dict[str, list[str]] = {
    "dotnet": ["*.csproj", "*.sln"],
}


def _has_marker_file(project_dir: Path, filenames: list[str]) -> bool:
    for depth_dir in [project_dir, *(_dirs_one_level_deep(project_dir))]:
        for name in filenames:
            if (depth_dir / name).is_file():
                return True
    return False


def _dirs_one_level_deep(project_dir: Path):
    if not project_dir.is_dir():
        return []
    return [p for p in project_dir.iterdir() if p.is_dir()]


def _has_marker_glob(project_dir: Path, patterns: list[str]) -> bool:
    for pattern in patterns:
        if any(project_dir.rglob(pattern)):
            return True
    return False


def detect_stacks(project_dir: Path) -> list[str]:
    found = []
    for stack, filenames in MARKER_FILES.items():
        if _has_marker_file(project_dir, filenames):
            found.append(stack)
    for stack, patterns in MARKER_GLOBS.items():
        if _has_marker_glob(project_dir, patterns):
            found.append(stack)
    return sorted(found)
