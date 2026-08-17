"""Read/write .toolkit-sync-state (JSON), the sync's only source of truth
for which files and entries are toolkit-managed."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

STATE_FILENAME = ".toolkit-sync-state"


@dataclass
class SyncState:
    ref: str | None = None
    files: dict[str, str] = field(default_factory=dict)  # target path -> sha256
    entries: dict[str, dict] = field(default_factory=dict)  # entry id -> {scope, tier}
    # Plugin ref -> id of the entry whose settings_patch enabled it. The only
    # record of "the toolkit itself turned this plugin on" — without it,
    # pruning can't tell a plugin it enabled and later stopped declaring
    # apart from one the user enabled by hand from a marketplace, and used to
    # nag to remove the latter on every sync. See sync._prune_stale_plugins.
    plugins: dict[str, str] = field(default_factory=dict)
    # Entry ids the project has been offered and declined. Purely a reporting
    # filter — a dismissed entry can still be synced by id at any time, and
    # syncing one clears it. Without this, the discovery sections re-offer the
    # same never-wanted block every single session forever, which is how the
    # whole report gets tuned out. Committed with the rest of the state, so
    # the decision is the team's, not each machine's.
    dismissed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ref": self.ref,
            "files": self.files,
            "entries": self.entries,
            "plugins": self.plugins,
            "dismissed": sorted(self.dismissed),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncState":
        return cls(
            ref=data.get("ref"),
            files=dict(data.get("files", {})),
            entries=dict(data.get("entries", {})),
            plugins=dict(data.get("plugins", {})),
            dismissed=list(data.get("dismissed", [])),
        )


def state_path(claude_dir: Path) -> Path:
    return claude_dir / STATE_FILENAME


def load_state(claude_dir: Path) -> SyncState:
    path = state_path(claude_dir)
    if not path.is_file():
        return SyncState()
    return SyncState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_state(claude_dir: Path, state: SyncState) -> None:
    path = state_path(claude_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_onboardable_project(project_dir: Path, state: SyncState) -> bool:
    """A scratch folder — no git repo, nothing ever synced — isn't a project
    the toolkit should write project-scope entries into: the process-none
    profile's whole premise is that the machine-wide user-scope entries
    already cover a one-shot session, with nothing project-local to
    maintain. `git init` first if this folder is meant to become a real
    project. Shared by status.py (whether to report) and sync.py (whether
    to actually write)."""
    return (project_dir / ".git").exists() or bool(state.entries)
