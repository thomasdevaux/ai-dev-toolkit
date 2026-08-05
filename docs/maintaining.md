# Maintaining this toolkit

How a **block** becomes files in a project's `.claude/`, and how to add,
change, or remove one. This is the repo's own maintenance reference —
not something synced to consuming projects.

This repo does not sync its own blocks onto itself, and commits land
directly on `main`. Don't apply `common/rules/*` conventions
(branch-per-feature, PR review, etc.) to work on this repo itself unless
the user asks.

## Blocks and the manifest

`sync-manifest.yaml` lists every syncable block. A block is a directory
tree under `common/`, `context-quality/`, `process/<variant>/`,
`tech-stacks/<lang>/`, `user-tools/<topic>/`, or `self-check/`, shaped
internally like `.claude/` itself (`rules/`, `skills/`, optionally
`commands/`, `agents/`, `hooks/`). Each block has one `type: file`
manifest entry: `id`, `source` (the block's directory), `target:
.claude/`, `scope` (`project` or `user`), `tier`, a one-line `summary:`,
and `detect` if it's a tech stack. `tools/sync` reads the entry, diffs
the block's files against the project's `.claude/`, and only writes
after confirmation — never deletes, always shows the diff first.

A block's dependency on an official Anthropic plugin (`gitlab`, a
language server, ...) is its own `type: official-plugin` manifest entry
rather than a nested dependency declaration. Syncing it patches only the
`enabledPlugins` key of `settings.json`, key by key.

`sync-manifest.yaml` is the single source of truth for what's syncable —
its `summary:` fields are what a reader sees when they inspect the
manifest or run `tools.sync status`. There is no separate rendered
catalog to keep in sync with it.

## The five tiers

Every manifest entry has a `tier` — the only source of truth for
governance status; never encode it in the block's directory name, since
a block that changes tier (e.g. `tech-stack` → `baseline`) should never
need a rename.

| Tier | Meaning | Enforcement |
| --- | --- | --- |
| `baseline` | Expected on every project. | Team-process expectation; `tools.sync status` lists it as missing until synced. |
| `choice-group:<name>` | Exactly one variant of `<name>`. | Blocked at sync time — `tools/sync` refuses a second entry sharing the tier while one is already registered. |
| `tech-stack` | Suggested from marker files (`detect:`). | Never auto-synced — `tools/sync detect` only prints a suggestion. |
| `suggested` | Useful, never expected. | Listed once under "available, not installed", never blocking. |
| `optional` | Opt-in and invisible. | Synced by id only, by someone who already knows they want it. |

## How rules actually load

Claude Code loads `.claude/rules/*.md` natively at the project level: a
rule with no `paths:` frontmatter loads at launch with the same priority
as `CLAUDE.md`; a rule with `paths:` loads only when Claude reads a
matching file. That's why every rule in this repo is a plain
`rules/<topic>.md` file with `paths:` frontmatter when it needs scoping
— no companion "rules" skill required. A `skills/<name>/SKILL.md` is
reserved for a genuine on-demand procedure, not a wrapper restating a
rule file.

## Choice groups

A `choice-group:<name>` tier permits exactly one variant per project.
Adding a new group means: pick a `<name>`, give every variant `tier:
choice-group:<name>`, and add a rule (following
`common/rules/process-profile.md`'s pattern) that prompts the user when
none of the group's variants are present. `tools/audit` checks that every
`choice-group:<name>` has at least two members — a lone member is a dead
group.

## What is deliberately not syncable

- **`incubator/`** — blocks written but not validated on a real project.
  No manifest entry may point into it.
- **`handbook/`** — team reference material, written for people, never
  loaded into a session.

Third-party content, by contrast, **is** syncable: copied in plain text
into the block that uses it, with its `LICENSE` and a `SOURCE.md`
recording upstream, commit, license, and import date
(`common/skills/caveman/` is the current example). `tools/audit` fails on
a `SOURCE.md` missing a field, or on MIT content shipped without its
`LICENSE`.

## Add a new block

1. Use [`../templates/new-block/SKILL.md`](../templates/new-block/SKILL.md)
   to scaffold it (point Claude at the file directly, or copy it into
   `.claude/skills/` locally). It asks for the block's topic, location,
   `tier`, and `scope`.
2. Fill in real rule content under `rules/<topic>.md`, with `paths:`
   frontmatter if it should only apply to matching files. Add on-demand
   skills under `skills/` only for genuine procedures.
3. Register the block in `sync-manifest.yaml`: one `type: file` entry
   (`id`, `source`, `target: .claude/`, `scope`, `tier`, `summary:`,
   `detect` if a tech stack), plus a `type: official-plugin` entry for
   any official plugin it depends on. `summary:` is mandatory —
   `tools/audit` fails without it.

   **Before adding a stack or a rule set, ask whether it's been used.**
   Content that hasn't been validated on a real project belongs in
   `incubator/`, absent from the manifest.
4. Test locally: `python -m tools.sync sync <id> --toolkit-root . --project-dir /path/to/scratch --yes`,
   confirm the expected files land, then re-run the same command and
   confirm it reports nothing to synchronize (idempotence). Add a dummy
   sub-project under `../demo/` if the block needs one — see
   [`../demo/README.md`](../demo/README.md).
5. Run `python -m tools.audit --toolkit-root .` — checks `paths:`
   overlap, the 200-line rules cap, choice-group integrity, third-party
   provenance, and missing `summary:`.

## Modify an existing block

- Edit `rules/<topic>.md` directly — it's both the reviewable source and
  what actually loads.
- If you change a rule's `paths:` scoping, run `python -m tools.audit
  --toolkit-root .` to check for new overlap with other blocks.
- Re-test the affected manifest entry end to end (sync into a scratch
  project, confirm idempotence) before committing.

## Deprecate a block

- Remove its entry (or entries) from `sync-manifest.yaml`.
- If it belonged to a `choice-group:<name>`, run `python -m tools.audit
  --toolkit-root .` to check the group still has at least two members.
- Delete the block's directory.
- Remove its section from `../demo/README.md` and delete its demo
  sub-project under `../demo/`, if any.
- Already-synced projects keep their copy of the deprecated block's
  files until they explicitly remove them — `tools/sync` never deletes
  files on its own, by design.

## Before committing

- Keep each block's `rules/*.md` content under 200 cumulative lines
  (`tools/audit` enforces this).
- Follow `../process/light/rules/git-workflow-light.md`,
  `../process/light/skills/commit-message-format/SKILL.md`, and
  `../common/rules/language.md` for everything you write here.
- Python changes under `tools/`: `pip install -r tools/sync/requirements.txt -r requirements-dev.txt`
  once, then `python -m pytest tests/ -v` before committing.

## Gotchas

- A file under a block's `hooks/` directory ending in `.sh` gets `chmod
  +x` automatically when `tools/sync` writes it — don't rely on the
  source checkout's own executable bit (this toolkit is developed on
  Windows).
- `python -m tools.sync sync <id...>` with **no** ids expands to every
  `tier: baseline` entry for the target scope; pass explicit ids for
  `tech-stack`/`choice-group`/`suggested`/`optional` entries.
  `python -m tools.sync status --toolkit-root . --project-dir <path>` is
  the read-only version — same report, no writes.
- **A hook must be silent when its check passes.** `context-check.sh`
  and `codegraph-freshness.sh` print nothing on a healthy project; a hook
  that speaks every session stops being read.
- **`common/` is deployed at both scopes** (`common-rules` and
  `common-rules-user`). Anything added there runs in `~/.claude/` too, so
  it must make sense in a folder that is not a project — that's why a
  hook there self-guards, and why `context-quality/` is a separate block.
- A `SessionStart` hook that needs to evolve without requiring every
  consumer to re-sync should follow `toolkit-self-check`'s pattern: keep
  the deployed/synced file a thin stub that `exec`s a same-named "impl"
  script living **outside** any block's `source:` path
  (`tools/hooks/toolkit-drift-check-impl.sh`), so it's never itself
  synced — the stub always runs the impl script from the freshly
  resolved checkout, not its own deployed copy. This is also why the
  drift check exits silently on a toolkit checkout of itself (detected
  by the presence of both `sync-manifest.yaml` and
  `tools/sync/manifest.py`): the report would otherwise come from a
  cached checkout lagging the working copy being edited, listing entries
  this repo already deleted.
