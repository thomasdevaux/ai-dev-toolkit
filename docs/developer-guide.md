# Developer guide: contributing to this repo

This repo is where blocks are authored and validated, not a consumer of
them: it does not sync its own blocks onto itself, and commits land
directly on `main`. Don't apply `common/rules/*` conventions
(branch-per-feature, PR review, etc.) to work on this repo itself unless
the user asks.

## Add a new block

1. Use [`../templates/new-block/SKILL.md`](../templates/new-block/SKILL.md)
   to scaffold it (point Claude at the file directly, or copy it into
   `.claude/skills/` locally). It asks for the block's topic, location
   (`common/`, `process/<variant>/`, `stacks/<topic>/`,
   `user-tools/<topic>/`, or `self-check/`), `tier`, and `scope`.
2. Fill in real rule content directly under `rules/<topic>.md` — add
   `paths:` YAML frontmatter if the rule should only apply to matching
   files, leave it unscoped otherwise. There's no companion "rules"
   skill to also write: `.claude/rules/*.md` loads natively (see
   [`architecture.md`](architecture.md#how-rules-actually-load)). Add
   on-demand workflow skills under `skills/` only for genuine
   procedures, not rule-restating wrappers.
3. Register the block in `sync-manifest.yaml`: one `type: file` entry
   (`id`, `source`, `target: .claude/`, `scope`, `tier`, `detect` if it's
   a stack), plus a separate `type: official-plugin` entry for any
   official Claude Code plugin it depends on.
4. Test locally: sync it into a scratch project —
   `python -m tools.sync sync <id> --toolkit-root . --project-dir
   /path/to/scratch --yes`, confirm the expected files land, then re-run
   the same command and confirm it reports nothing to synchronize
   (idempotence — see [`requirements.md`](requirements.md)). Add a dummy
   sub-project under `../demo/` if the block needs one — see
   [`../demo/README.md`](../demo/README.md) for the pattern.
5. Run `python -m tools.audit --toolkit-root .` to confirm no `paths:`
   overlap with existing blocks, the 200-line rules cap, and choice-group
   integrity.
6. Update the [block catalog](user-guide.md#block-catalog) table in
   `user-guide.md`, and the [official plugin catalog](user-guide.md#official-plugin-catalog)
   if you added an `official-plugin` entry.

## Modify an existing block

- Edit `rules/<topic>.md` directly — it's both the reviewable source and
  what actually loads, no companion skill to keep in sync.
- If you change a rule's `paths:` scoping, run `python -m tools.audit
  --toolkit-root .` to check for new overlap with other blocks.
- Re-test the affected manifest entry end to end (sync into a scratch
  project, confirm idempotence) before committing.

## Deprecate a block

- Remove its entry (or entries) from `sync-manifest.yaml`.
- If it belonged to a `choice-group:<name>`, check whether the group is
  left with fewer than two members — run `python -m tools.audit
  --toolkit-root .`, it flags this directly.
- Delete the block's directory.
- Remove its row from the `user-guide.md` block catalog, and from the
  official plugin catalog if it had an `official-plugin` entry.
- Remove its section from `../demo/README.md` and delete its demo
  sub-project under `../demo/`, if any.
- Note in the removal that already-synced projects keep their copy of
  the deprecated block's files until they explicitly remove them —
  `tools/sync` never deletes files on its own, by design.

## Before committing

- Never commit a block with a `rules/*.md` file that doesn't need
  `paths:` scoping when it actually does — check it loads only where
  intended by testing against a matching and a non-matching file.
- Keep each block's `rules/*.md` content under 200 cumulative lines
  (`tools/audit` enforces this).
- Follow `../common/rules/git-workflow.md` and
  `../common/rules/language.md` for everything you write here.
- Python changes under `tools/`: run `pip install -r tools/sync/requirements.txt -r requirements-dev.txt` once, then `python -m pytest tests/ -v` before committing.

## Gotchas

Non-obvious behaviors of this repo's tooling and conventions.

- **A block's location and `tier` field are the only source of truth for
  governance status** — never encode it in the block's directory name.
  A block that changes governance status (e.g. moves from `stack` to
  `baseline`) should never need a rename; `tier` lives in
  `sync-manifest.yaml`, not the filesystem path.
- `.claude/rules/*.md` loads natively — confirmed against Claude Code's
  own docs. A rule file needs `paths:` frontmatter directly on itself to
  scope it; there is no companion "rules" skill to also write. Only
  write a `skills/<name>/SKILL.md` for a genuine on-demand procedure.
- Keep each block's `rules/*.md` content under 200 cumulative lines —
  `tools/audit` enforces this.
- After editing a rule's `paths:` scoping, run `python -m tools.audit
  --toolkit-root .` to check for new overlap with other blocks.
- A `choice-group:<name>` tier is blocked **at sync time**, not just by
  lint: `tools/sync` refuses to sync a second entry sharing the tier
  while another member is already registered in a project's
  `.toolkit-sync-state`.
- A file under a block's `hooks/` directory ending in `.sh` gets
  `chmod +x` automatically when `tools/sync` writes it — don't rely on
  the source checkout's own executable bit, since it isn't reliable
  across platforms (this toolkit is developed on Windows).
- `tools/sync` never deletes files — a conflict (local content differs
  from source) is always shown as a diff and applied only after
  confirmation, never blocked outright and never silently skipped.
- `python -m tools.sync sync <id...> --toolkit-root . --user` targets
  `~/.claude/` for `scope: user` entries; `python -m tools.sync detect
  --project-dir <path>` only ever *suggests* `tier: stack` entries from
  marker files and never syncs anything itself.
- `tools/audit/checks.py` is where the three automated checks (`paths:`
  overlap, 200-line cap, choice-group integrity) live.
- `python -m tools.sync sync <id...>` with **no** ids expands to every
  `tier: baseline` entry for the target scope (`baseline_entry_ids` in
  `manifest.py`) — pass explicit ids only for `stack`/`choice-group`/
  `optional` entries, which always require a deliberate pick.
  `python -m tools.sync status --toolkit-root . --project-dir <path>` is
  the read-only version: same drift/missing-entry report, no writes.
- A `SessionStart` hook script that needs to evolve without requiring
  every consumer to re-sync should follow `toolkit-self-check`'s
  pattern: keep the deployed/synced file a thin stub that `exec`s a
  same-named "impl" script living **outside** any block's `source:`
  path (`tools/hooks/toolkit-drift-check-impl.sh`) so it's never itself
  synced — the stub always runs the impl script from the freshly
  resolved checkout, not from its own deployed copy.
