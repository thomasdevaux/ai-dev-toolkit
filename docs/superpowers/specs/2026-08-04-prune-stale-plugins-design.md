# Prune stale plugins during sync

## Problem

`tools/sync` can add `enabledPlugins` entries to a project's
`.claude/settings.json` (via `type: official-plugin` manifest entries),
but nothing ever removes them. A plugin can end up enabled in a
project's `settings.json` while no longer being referenced by
`sync-manifest.yaml` at all — e.g. the toolkit dropped an
`official-plugin` entry, or a plugin was enabled by some other means.
`sync` should surface this and offer to clean it up, plugin by plugin.

## Scope

Every `python -m tools.sync sync ...` invocation, after applying the
requested entries, checks the target `settings.json` for
`enabledPlugins` entries that aren't referenced by **any**
`type: official-plugin` entry in `sync-manifest.yaml` (regardless of
that entry's own sync state, and regardless of the stale plugin's
marketplace of origin) and offers to remove each one interactively.

No new CLI flag. `--yes` also auto-confirms removals, consistent with
how it already auto-confirms every other proposed change in a sync
run.

## Detection

`known_refs` is the set of `plugin_ref` values across *all*
`type: official-plugin` entries in the loaded manifest — not just the
entries passed on this invocation's command line, and not filtered by
`state.entries` (the toolkit's own sync history). The manifest is the
single source of truth for "does the toolkit know about this plugin".

After the entry loop finishes applying its changes, reload
`settings.json` fresh (so the check sees this run's own edits) and
collect every key of `enabledPlugins` whose value is truthy. Any such
key not in `known_refs` is stale.

```python
# manifest.py
def official_plugin_refs(entries: dict[str, SyncEntry]) -> set[str]:
    return {e.plugin_ref for e in entries.values() if e.type == "official-plugin"}

# settings_patch.py
def stale_plugin_refs(settings: dict, known_refs: set[str]) -> list[str]:
    enabled = settings.get("enabledPlugins", {})
    return sorted(ref for ref, value in enabled.items() if value and ref not in known_refs)
```

## Removal

Removal deletes the key entirely (not `false`) — the resulting
`settings.json` looks as if the plugin had never been added.

```python
# settings_patch.py
def remove_plugin(settings: dict, ref: str) -> dict:
    merged = dict(settings)
    enabled = dict(merged.get("enabledPlugins", {}))
    enabled.pop(ref, None)
    merged["enabledPlugins"] = enabled
    return merged
```

`remove_plugin` is pure, matching the existing style in
`settings_patch.py` (`merge_patch`, `diff_settings`).

## Orchestration

New function in `sync.py`, called once at the end of `sync_entries`,
after the entry loop and before `save_state`:

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

Runs regardless of which `entry_ids` were passed to this invocation —
`known_refs` always comes from the full manifest, so the check is
consistent whether the user synced one entry or ten.

### Edge cases

- No `settings.json`, or no `enabledPlugins` key: nothing to check, no
  prune output at all.
- No stale plugins found: no prune output (keeps the common case
  quiet).
- User declines a removal (interactive `n`): plugin is left as-is,
  `[prune] kept '<ref>'` is printed, and the loop continues to the
  next stale plugin without aborting the run.
- `--yes`: every proposed removal is auto-confirmed, same as every
  other change `sync` proposes.

### Trade-off (accepted)

Because the check compares against *all* enabled plugins regardless of
marketplace, a plugin a developer enabled by hand from an unrelated
marketplace (not `@claude-plugins-official`) will also be flagged as
stale if nothing in `sync-manifest.yaml` references it. This was a
deliberate choice (see design discussion) — the toolkit's `sync`
becomes the source of truth for "which plugins should be enabled on a
synced project."

## Testing

Unit tests:
- `official_plugin_refs`: extracts refs only from `official-plugin`
  entries, ignores `file` entries.
- `stale_plugin_refs`: filters out known refs, ignores falsy values,
  returns a sorted list.
- `remove_plugin`: removes the target key, leaves other
  `enabledPlugins` entries and other top-level settings keys untouched.

Integration test (CLI):
- Seed a project's `settings.json` with an `enabledPlugins` entry not
  present in a test manifest; run `sync` with `--yes` and assert the
  entry is gone afterward.
- Same setup without `--yes`, simulated `n` input; assert the entry is
  still present and the run still exits 0.

## Docs

Add a short note to
`docs/user-guide.md#official-plugin-catalog` describing that `sync`
also offers to remove `enabledPlugins` entries no longer referenced by
the manifest.
