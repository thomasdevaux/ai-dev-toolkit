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

    def to_dict(self) -> dict:
        return {"ref": self.ref, "files": self.files, "entries": self.entries}

    @classmethod
    def from_dict(cls, data: dict) -> "SyncState":
        return cls(
            ref=data.get("ref"),
            files=dict(data.get("files", {})),
            entries=dict(data.get("entries", {})),
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
