# Prune Stale Plugins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python -m tools.sync sync ...` detects `enabledPlugins` entries in the target `settings.json` that no `type: official-plugin` entry in `sync-manifest.yaml` references, and offers to remove each one, plugin by plugin.

**Architecture:** Two small pure-function additions (`manifest.official_plugin_refs`, `settings_patch.stale_plugin_refs` / `settings_patch.remove_plugin`) feed a new orchestration step in `sync.sync_entries` that runs once, after the existing entry loop, reusing the existing `confirm()` prompt helper. No new CLI flags.

**Tech Stack:** Python 3.12, PyYAML (existing), pytest (new dev dependency — this repo currently has zero automated tests; see spec `docs/superpowers/specs/2026-08-04-prune-stale-plugins-design.md` for why pytest was chosen over the repo's existing manual-testing convention).

## Global Constraints

- Detection compares against **every** `type: official-plugin` entry in the full manifest, not just entries passed to this `sync` invocation and not filtered by `.toolkit-sync-state` (spec: "Detection").
- Stale-plugin comparison covers **all** `enabledPlugins` entries regardless of marketplace, not just `@claude-plugins-official` ones (spec: "Trade-off (accepted)").
- Removal deletes the `enabledPlugins` key entirely — never sets it to `false` (spec: "Removal").
- The prune step runs on **every** `sync` invocation, unconditionally, after the requested entries are applied (spec: "Orchestration").
- `--yes` auto-confirms plugin removals exactly like it auto-confirms every other proposed change (spec: "Orchestration" / "Edge cases").
- A declined removal must not abort the run — the loop continues to the next stale plugin (spec: "Edge cases").
- New functions are pure (return new dicts/sets, never mutate their arguments), matching the existing style in `settings_patch.py`.

---

## File Structure

- Modify `tools/sync/manifest.py` — add `official_plugin_refs()`.
- Modify `tools/sync/settings_patch.py` — add `stale_plugin_refs()` and `remove_plugin()`.
- Modify `tools/sync/sync.py` — add `_prune_stale_plugins()`, call it at the end of `sync_entries()`.
- Create `tests/tools/sync/test_manifest.py`.
- Create `tests/tools/sync/test_settings_patch.py`.
- Create `tests/tools/sync/test_sync.py`.
- Create `requirements-dev.txt` (repo root) — adds `pytest`.
- Modify `docs/user-guide.md` — document the prune behavior in the official plugin catalog section.
- Modify `docs/developer-guide.md` — document how to run the new test suite.

---

### Task 1: `official_plugin_refs()` in manifest.py

**Files:**
- Modify: `tools/sync/manifest.py`
- Test: `tests/tools/sync/test_manifest.py`

**Interfaces:**
- Produces: `official_plugin_refs(entries: dict[str, SyncEntry]) -> set[str]` — set of every `plugin_ref` across `type: official-plugin` entries in `entries`.

- [ ] **Step 1: Create the test file and write the failing tests**

Create `tests/tools/sync/test_manifest.py`:

```python
from tools.sync.manifest import SyncEntry, official_plugin_refs


def _entry(id_: str, type_: str = "file", plugin_ref: str | None = None) -> SyncEntry:
    return SyncEntry(id=id_, type=type_, scope="project", tier="baseline", plugin_ref=plugin_ref)


def test_official_plugin_refs_collects_only_official_plugin_entries():
    entries = {
        "gitlab": _entry("gitlab", type_="official-plugin", plugin_ref="gitlab@claude-plugins-official"),
        "common": _entry("common", type_="file"),
    }
    assert official_plugin_refs(entries) == {"gitlab@claude-plugins-official"}


def test_official_plugin_refs_empty_when_none_declared():
    entries = {"common": _entry("common", type_="file")}
    assert official_plugin_refs(entries) == set()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from repo root): `python -m pytest tests/tools/sync/test_manifest.py -v`
Expected: FAIL with `ImportError: cannot import name 'official_plugin_refs'`

- [ ] **Step 3: Implement `official_plugin_refs()`**

In `tools/sync/manifest.py`, add at the end of the file (after `load_manifest`):

```python
def official_plugin_refs(entries: dict[str, SyncEntry]) -> set[str]:
    """Every plugin_ref declared by a type: official-plugin entry, regardless
    of whether that entry has been synced to any given project."""
    return {e.plugin_ref for e in entries.values() if e.type == "official-plugin"}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/tools/sync/test_manifest.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tools/sync/manifest.py tests/tools/sync/test_manifest.py
git commit -m "feat(sync): add official_plugin_refs() for stale-plugin detection"
```

---

### Task 2: `stale_plugin_refs()` and `remove_plugin()` in settings_patch.py

**Files:**
- Modify: `tools/sync/settings_patch.py`
- Test: `tests/tools/sync/test_settings_patch.py`

**Interfaces:**
- Consumes: nothing from Task 1 (operates on plain `dict`/`set[str]`, decoupled from `SyncEntry`).
- Produces: `stale_plugin_refs(settings: dict, known_refs: set[str]) -> list[str]` — sorted list of `enabledPlugins` keys with a truthy value that aren't in `known_refs`. `remove_plugin(settings: dict, ref: str) -> dict` — new settings dict with `ref` removed from `enabledPlugins` (no-op if absent).

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/sync/test_settings_patch.py`:

```python
from tools.sync.settings_patch import remove_plugin, stale_plugin_refs


def test_stale_plugin_refs_filters_known_and_falsy():
    settings = {
        "enabledPlugins": {
            "gitlab@claude-plugins-official": True,
            "old-plugin@some-marketplace": True,
            "disabled-plugin@x": False,
        }
    }
    known = {"gitlab@claude-plugins-official"}
    assert stale_plugin_refs(settings, known) == ["old-plugin@some-marketplace"]


def test_stale_plugin_refs_sorted_when_multiple():
    settings = {
        "enabledPlugins": {
            "zzz@x": True,
            "aaa@x": True,
        }
    }
    assert stale_plugin_refs(settings, set()) == ["aaa@x", "zzz@x"]


def test_stale_plugin_refs_no_enabled_plugins_key():
    assert stale_plugin_refs({}, {"gitlab@claude-plugins-official"}) == []


def test_remove_plugin_deletes_key_only():
    settings = {
        "enabledPlugins": {
            "gitlab@claude-plugins-official": True,
            "old-plugin@some-marketplace": True,
        },
        "otherKey": "untouched",
    }

    result = remove_plugin(settings, "old-plugin@some-marketplace")

    assert result == {
        "enabledPlugins": {"gitlab@claude-plugins-official": True},
        "otherKey": "untouched",
    }
    assert "old-plugin@some-marketplace" in settings["enabledPlugins"]  # original untouched


def test_remove_plugin_missing_key_is_noop():
    settings = {"enabledPlugins": {"gitlab@claude-plugins-official": True}}
    result = remove_plugin(settings, "not-there@x")
    assert result == settings
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/tools/sync/test_settings_patch.py -v`
Expected: FAIL with `ImportError: cannot import name 'remove_plugin'`

- [ ] **Step 3: Implement both functions**

In `tools/sync/settings_patch.py`, add at the end of the file (after `save_settings`):

```python
def stale_plugin_refs(settings: dict, known_refs: set[str]) -> list[str]:
    enabled = settings.get("enabledPlugins", {})
    return sorted(ref for ref, value in enabled.items() if value and ref not in known_refs)


def remove_plugin(settings: dict, ref: str) -> dict:
    merged = dict(settings)
    enabled = dict(merged.get("enabledPlugins", {}))
    enabled.pop(ref, None)
    merged["enabledPlugins"] = enabled
    return merged
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/tools/sync/test_settings_patch.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add tools/sync/settings_patch.py tests/tools/sync/test_settings_patch.py
git commit -m "feat(sync): add stale_plugin_refs() and remove_plugin()"
```

---

### Task 3: Wire pruning into `sync_entries()`

**Files:**
- Modify: `tools/sync/sync.py`
- Test: `tests/tools/sync/test_sync.py`

**Interfaces:**
- Consumes: `official_plugin_refs(entries)` from Task 1; `stale_plugin_refs(settings, known)` and `remove_plugin(settings, ref)` from Task 2; existing `confirm(prompt, auto_yes)` from `tools/sync/diffing.py`; existing `load_settings(path)` / `save_settings(path, settings)` from `tools/sync/settings_patch.py`.
- Produces: `_prune_stale_plugins(manifest: dict[str, SyncEntry], claude_dir: Path, auto_yes: bool) -> None`, called once at the end of `sync_entries()`.

- [ ] **Step 1: Write the failing integration tests**

Create `tests/tools/sync/test_sync.py`:

```python
import json
from pathlib import Path

from tools.sync.sync import sync_entries

MANIFEST = """
- id: gitlab
  type: official-plugin
  plugin_ref: "gitlab@claude-plugins-official"
  scope: project
  tier: baseline
  settings_patch:
    enabledPlugins:
      "gitlab@claude-plugins-official": true
"""


def _make_toolkit(tmp_path: Path) -> Path:
    toolkit_root = tmp_path / "toolkit"
    toolkit_root.mkdir()
    (toolkit_root / "sync-manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    return toolkit_root


def _make_project(tmp_path: Path, enabled_plugins: dict) -> Path:
    claude_dir = tmp_path / "project" / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(
        json.dumps({"enabledPlugins": enabled_plugins}), encoding="utf-8"
    )
    return claude_dir


def test_sync_prunes_stale_plugin_with_auto_yes(tmp_path):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(
        tmp_path,
        {
            "gitlab@claude-plugins-official": True,
            "old-plugin@some-marketplace": True,
        },
    )

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {"gitlab@claude-plugins-official": True}


def test_sync_keeps_stale_plugin_when_declined(tmp_path, monkeypatch):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(
        tmp_path,
        {
            "gitlab@claude-plugins-official": True,
            "old-plugin@some-marketplace": True,
        },
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=False)

    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {
        "gitlab@claude-plugins-official": True,
        "old-plugin@some-marketplace": True,
    }


def test_sync_no_prune_output_when_nothing_stale(tmp_path, capsys):
    toolkit_root = _make_toolkit(tmp_path)
    claude_dir = _make_project(tmp_path, {"gitlab@claude-plugins-official": True})

    sync_entries(["gitlab"], toolkit_root, claude_dir, auto_yes=True)

    assert "[prune]" not in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/tools/sync/test_sync.py -v`
Expected: FAIL — `test_sync_prunes_stale_plugin_with_auto_yes` and `test_sync_keeps_stale_plugin_when_declined` fail because `old-plugin@some-marketplace` is still present (no pruning happens yet); `test_sync_no_prune_output_when_nothing_stale` passes vacuously (acceptable — it becomes a real regression guard once Step 3 lands).

- [ ] **Step 3: Implement `_prune_stale_plugins()` and wire it in**

In `tools/sync/sync.py`, update the imports at the top of the file:

```python
from .diffing import apply_file_changes, confirm, plan_file_changes, render_file_changes, sha256_bytes
from .manifest import SyncEntry, load_manifest, official_plugin_refs
from .settings_patch import diff_settings, load_settings, merge_patch, remove_plugin, save_settings, stale_plugin_refs
from .state import load_state, save_state
```

Add this function after `_check_choice_group` and before `sync_entries`:

```python
def _prune_stale_plugins(manifest: dict[str, SyncEntry], claude_dir: Path, auto_yes: bool) -> None:
    settings_path = claude_dir / "settings.json"
    settings = load_settings(settings_path)
    known = official_plugin_refs(manifest)
    for ref in stale_plugin_refs(settings, known):
        print(f"[prune] plugin '{ref}' is enabled but not referenced by any entry in sync-manifest.yaml")
        if confirm(f"Remove '{ref}' from enabledPlugins?", auto_yes):
            settings = remove_plugin(settings, ref)
            save_settings(settings_path, settings)
            print(f"[prune] removed '{ref}'")
        else:
            print(f"[prune] kept '{ref}'")
```

In `sync_entries()`, call it right before the final `save_state(claude_dir, state)`:

```python
    _prune_stale_plugins(manifest, claude_dir, auto_yes)
    save_state(claude_dir, state)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/tools/sync/test_sync.py -v`
Expected: 3 passed

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: 10 passed (2 from Task 1 + 5 from Task 2 + 3 from Task 3)

- [ ] **Step 6: Commit**

```bash
git add tools/sync/sync.py tests/tools/sync/test_sync.py
git commit -m "feat(sync): prune enabledPlugins entries not referenced by the manifest"
```

---

### Task 4: Dev dependencies and docs

**Files:**
- Create: `requirements-dev.txt`
- Modify: `docs/user-guide.md`
- Modify: `docs/developer-guide.md`

- [ ] **Step 1: Add the pytest dev dependency**

Create `requirements-dev.txt` at the repo root:

```
pytest
```

- [ ] **Step 2: Verify a clean install runs the suite**

Run: `pip install -r tools/sync/requirements.txt -r requirements-dev.txt`
Run: `python -m pytest tests/ -v`
Expected: 10 passed

- [ ] **Step 3: Document the prune behavior in the official plugin catalog**

In `docs/user-guide.md`, insert this new subsection after the "### Installing an official plugin without the sync tool" section (after the paragraph ending "...it doesn't do anything a direct `/plugin install` couldn't.") and before "### Adding a new official-plugin entry":

```markdown
### Pruning stale plugins

Every `sync` run also checks the target `settings.json` for
`enabledPlugins` entries that no `type: official-plugin` entry in
`sync-manifest.yaml` references anymore — regardless of marketplace,
and regardless of whether that entry was ever synced to this project.
It offers to remove each one, plugin by plugin; declining leaves that
plugin as-is and moves on to the next. `--yes` auto-confirms removals
the same way it auto-confirms every other proposed change.
```

- [ ] **Step 4: Document how to run tests in the developer guide**

In `docs/developer-guide.md`, add a new bullet at the end of the "## Before committing" section:

```markdown
- Python changes under `tools/`: run `pip install -r tools/sync/requirements.txt -r requirements-dev.txt` once, then `python -m pytest tests/ -v` before committing.
```

- [ ] **Step 5: Commit**

```bash
git add requirements-dev.txt docs/user-guide.md docs/developer-guide.md
git commit -m "docs(sync): document plugin pruning and the new pytest suite"
```

---

## Self-Review Notes

- **Spec coverage:** Detection (Task 1+2), Removal (Task 2), Orchestration + edge cases (Task 3, including the "no stale plugins → no output" case and the "declined → kept, loop continues" case), Trade-off note (carried into Task 4 docs), Testing (Tasks 1-3), Docs (Task 4) — all spec sections have a corresponding task.
- **Placeholder scan:** no TBD/TODO; every step has runnable code and exact expected output.
- **Type consistency:** `official_plugin_refs(entries: dict[str, SyncEntry]) -> set[str]` (Task 1) is consumed as `known = official_plugin_refs(manifest)` in Task 3 with the same `dict[str, SyncEntry]` shape `sync_entries` already holds. `stale_plugin_refs(settings: dict, known_refs: set[str]) -> list[str]` and `remove_plugin(settings: dict, ref: str) -> dict` (Task 2) are consumed with matching signatures in Task 3's `_prune_stale_plugins`.
