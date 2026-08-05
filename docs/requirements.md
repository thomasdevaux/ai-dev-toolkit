# Requirements: guarantees the toolkit must hold

These are the properties `tools/sync` and `tools/audit` are built to
guarantee. They constrain how any new block or manifest entry may
behave — a change that breaks one of these is a regression, not a
design choice.

## Sync must be idempotent

Running the same `python -m tools.sync sync <id...>` command twice
against an unchanged project reports "nothing to synchronize" the second
time. Every block, once added, must be tested this way (see
[`developer-guide.md`](developer-guide.md)).

## Sync must be non-destructive

`tools/sync` never deletes files. A conflict — local content differs
from the block's source — is always shown as a diff and applied only
after explicit confirmation; it's never blocked outright and never
silently skipped. A deprecated block's already-synced files stay in a
project until someone removes them by hand.

## Every write is diff-then-confirm

`tools/sync` prints the files it would create or change, and any
`settings.json` key it would patch, before writing anything. Nothing
lands without confirmation.

## Choice groups are mutually exclusive at sync time

A `choice-group:<name>` tier permits exactly one variant per project.
`tools/sync` refuses to sync a second entry sharing that tier value
while another member is already registered in `.toolkit-sync-state`,
failing before anything is written. See
[`architecture.md`](architecture.md#mutual-exclusion) for the mechanism.

## Automated lint checks

`python -m tools.audit --toolkit-root .` must catch, for the whole
manifest at once:

- `paths:` frontmatter overlap between any two rule files.
- Each block's `rules/*.md` content staying under 200 cumulative lines.
- Choice-group integrity — every `choice-group:<name>` value has at
  least two members.

## Stack detection only suggests

`tools/sync detect --project-dir <path>` inspects marker files and
prints suggested `tier: tech-stack` ids. It never syncs anything itself —
every sync is an explicit, separate command.

## Settings patches are scoped

Syncing an `official-plugin` entry patches only the `enabledPlugins` key
of `settings.json`, key by key. Every other setting, including unrelated
`enabledPlugins` entries, is left untouched.
