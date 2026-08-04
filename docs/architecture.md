# Architecture: how the toolkit is put together

How a **block** becomes files in a project's `.claude/`, how governance
status is expressed, and how Claude Code actually loads what gets synced.

## Blocks and the manifest

`sync-manifest.yaml` lists every syncable block. A block is a directory
tree under `common/`, `process/<variant>/`, `stacks/<topic>/`,
`user-tools/<topic>/`, or `self-check/`, shaped internally like
`.claude/` itself (`rules/`, `skills/`, optionally `agents/` and
`hooks/`). Each block has one `type: file` manifest entry: `id`,
`source` (the block's directory), `target: .claude/`, `scope`
(`project` or `user`), `tier`, and `detect` if it's a stack.
`tools/sync` reads the entry, diffs the block's files against the
project's `.claude/`, and only writes after confirmation — see
[`requirements.md`](requirements.md) for the exact guarantees this
gives.

`self-check/` holds one block — its single file,
`hooks/toolkit-drift-check.sh`, is registered under two manifest
entries at once (`toolkit-self-check` at `scope: project`,
`tier: baseline`, and `toolkit-self-check-user` at `scope: user`,
`tier: optional`), the same "one source, two scopes" pattern a stack
and its official-plugin dependency use. The project entry gets the hook
into every project that syncs baseline, so it's enforced for every
contributor; the user entry is a one-time, per-developer install into
`~/.claude/` so the same check also fires on brand-new projects that
haven't been synced yet at all.

That deployed file is deliberately a thin stub: it only resolves an
`ai-dev-toolkit` checkout (env override, or an auto-cloned/pulled local
cache) and then `exec`s `tools/hooks/toolkit-drift-check-impl.sh` —
found inside that resolved checkout, not the deployed copy. The impl
script (which prints `python -m tools.sync status`'s report as
`SessionStart` context) deliberately lives outside `self-check/`, so it
is never itself synced/deployed; it always runs live from whatever the
stub just resolved. This means behavior changes to the impl script take
effect on a project's next session (via the cache's throttled `git
pull`) without anyone needing to re-sync the stub — only changes to the
stub's own bootstrap logic (rare) require that. See
[`user-guide.md`](user-guide.md) for the one-time setup command.

A block's dependency on an official Anthropic plugin (`gitlab`,
`rust-analyzer-lsp`, ...) is its own `type: official-plugin` manifest
entry rather than a nested dependency declaration. Its `tier` mirrors the
block it supports (`baseline` for `common`'s dependencies, `stack` with a
matching `detect` list for a language stack's LSP). Syncing it patches
only the `enabledPlugins` key of `settings.json`, key by key — every
other setting, including unrelated `enabledPlugins` entries, is left
untouched. See [`user-guide.md`](user-guide.md#official-plugin-catalog)
for the current catalog.

## The four tiers

Every manifest entry has a `tier` field — this is the *only* source of
truth for a block's governance status; never encode it in the block's
directory name (see [`developer-guide.md`](developer-guide.md) for why
that matters in practice).

| Tier | Meaning | Enforcement |
| --- | --- | --- |
| `baseline` | Non-negotiable, applies to every project. | Nothing blocks *not* syncing it — a team-process expectation, not a technical lock. |
| `choice-group:<name>` | Exactly one variant of `<name>` must be present, never zero, never two. | **Blocked at sync time**: `tools/sync` refuses to sync a second entry sharing the same `tier` value once one is already registered in `.toolkit-sync-state`, until the first is removed. |
| `stack` | Suggested for a specific tech stack; `detect` lists the marker files that make it relevant. | Never auto-synced — `tools/sync detect` only prints a suggestion, syncing is always an explicit `tools/sync sync <id>` call. |
| `optional` | Opt-in, never suggested by stack detection (e.g. `user-tools/statusline`). | Same as `stack`: always explicit. |

`common/`'s single entry (`common-rules`) is the only `baseline` entry
today. There's no schema-level "required" flag anywhere; `baseline` is a
documentation convention.

## Mutual exclusion

`tools/sync` blocks syncing `process-full` while `process-light` is
already registered in `.toolkit-sync-state` (or vice versa) — it fails
immediately with an error naming the conflicting entry, before anything
is written. See `process/light/rules/process-profile.md` for the rule
that asks the user to pick one when *neither* is present yet — the tool
enforces "not both," not "at least one."

Adding a new choice group means: pick a `<name>`, give every variant
`tier: choice-group:<name>`, and add a rule (following
`process-profile.md`'s pattern) that prompts the user when none of the
group's variants are present yet. `tools/audit` separately checks that
every `choice-group:<name>` value in `sync-manifest.yaml` has at least
two members — a lone member is a dead group, not a real choice.

## How rules actually load

Claude Code loads `.claude/rules/*.md` natively at the project level: a
rule with no `paths:` frontmatter loads at launch with the same priority
as `CLAUDE.md`; a rule with `paths:` loads only when Claude reads a
matching file. This is confirmed against Claude Code's own docs (the
`.claude/rules/` section), and it's why every rule in this repo is a
plain `rules/<topic>.md` file with `paths:` frontmatter when it needs
scoping, with no companion "rules" skill required to get scoped
behavior. A skill under a block's `skills/` directory is reserved for
genuine on-demand procedures (e.g. `ship-tool`, `build-toolchain`) — not
a wrapper that just restates a rule file.

## What stays a pure documentation convention

Whether a `stack` or `optional` entry is worth adopting for a given
project is a judgment call, not something the tool enforces.
`tools/sync detect` surfaces a suggestion from marker files; a human
still decides whether to act on it.
