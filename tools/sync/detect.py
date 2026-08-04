"""Stack detection from marker files. Suggestions only — never synced
without explicit confirmation."""
from __future__ import annotations

from pathlib import Path

# stack name -> plain marker filenames looked up at root + one level deep
MARKER_FILES: dict[str, list[str]] = {
    "python": ["pyproject.toml", "requirements.txt", "setup.py"],
    "nodejs": ["package.json"],
    "rust": ["Cargo.toml"],
}

# stack name -> glob patterns searched recursively
MARKER_GLOBS: dict[str, list[str]] = {
    "model-based-design": ["*.slx", "*.mdl"],
}

EMBEDDED_C_BUILD_MARKERS = ["Makefile", "CMakeLists.txt"]


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


def _has_embedded_c(project_dir: Path) -> bool:
    if not _has_marker_file(project_dir, EMBEDDED_C_BUILD_MARKERS):
        return False
    return any(project_dir.rglob("*.c")) or any(project_dir.rglob("*.h"))


def detect_stacks(project_dir: Path) -> list[str]:
    found = []
    for stack, filenames in MARKER_FILES.items():
        if _has_marker_file(project_dir, filenames):
            found.append(stack)
    for stack, patterns in MARKER_GLOBS.items():
        if _has_marker_glob(project_dir, patterns):
            found.append(stack)
    if _has_embedded_c(project_dir):
        found.append("embedded-c")
    return sorted(found)
