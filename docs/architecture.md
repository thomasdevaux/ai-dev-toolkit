# Architecture: how the toolkit is put together

How a **block** becomes files in a project's `.claude/`, how governance
status is expressed, and how Claude Code actually loads what gets synced.

## Blocks and the manifest

`sync-manifest.yaml` lists every syncable block. A block is a directory
tree under `common/`, `context-quality/`, `process/<variant>/`,
`tech-stacks/<lang>/`, `user-tools/<topic>/`, or `self-check/`, shaped
internally like `.claude/` itself (`rules/`, `skills/`, optionally
`commands/`, `agents/` and `hooks/`). Each block has one `type: file` manifest entry: `id`,
`source` (the block's directory), `target: .claude/`, `scope`
(`project` or `user`), `tier`, a one-line `summary:`, and `detect` if it's a tech stack.
`tools/sync` reads the entry, diffs the block's files against the
project's `.claude/`, and only writes after confirmation — see
[`requirements.md`](requirements.md) for the exact guarantees this
gives.

`self-check/` holds one block — its single file,
`hooks/toolkit-drift-check.sh`, is registered under two manifest
entries at once (`toolkit-self-check` at `scope: project`,
`tier: baseline`, and `toolkit-self-check-user` at `scope: user`,
`tier: optional`), the same "one source, two scopes" pattern
`common-rules` / `common-rules-user` uses. The project entry gets the hook
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
block it supports (`baseline` for `common`'s dependencies, `tech-stack`
with a matching `detect` list for a language's LSP). Syncing it patches
only the `enabledPlugins` key of `settings.json`, key by key — every
other setting, including unrelated `enabledPlugins` entries, is left
untouched. See [`user-guide.md`](user-guide.md#official-plugin-catalog)
for the current catalog.

## The five tiers

Every manifest entry has a `tier` field — this is the *only* source of
truth for a block's governance status; never encode it in the block's
directory name (see [`developer-guide.md`](developer-guide.md) for why
that matters in practice).

| Tier | Meaning | Enforcement |
| --- | --- | --- |
| `baseline` | Non-negotiable, applies to every project. | Nothing blocks *not* syncing it — a team-process expectation, not a technical lock. |
| `choice-group:<name>` | Exactly one variant of `<name>` must be present, never zero, never two. | **Blocked at sync time**: `tools/sync` refuses to sync a second entry sharing the same `tier` value once one is already registered in `.toolkit-sync-state`, until the first is removed. |
| `tech-stack` | Suggested for a specific language/stack; `detect` lists the marker files that make it relevant. | Never auto-synced — `tools/sync detect` only prints a suggestion, syncing is always an explicit `tools/sync sync <id>` call. |
| `suggested` | Useful, never expected. Listed by `status` under "available, not installed", with its `summary:`. | Listed once per report, never counted as drift, never blocking. |
| `optional` | Opt-in and **invisible** — never surfaced by any report (e.g. `common-rules-user`). | Synced by id only, by someone who already knows they want it. |

`suggested` and `optional` differ in exactly one thing: visibility. That's
deliberate — before the split, a genuinely useful block could only be
advertised by writing it into a document nobody reads at the right moment.

`tier` values are validated at load time (`manifest.py:VALID_TIERS`): a typo
used to sync silently under a tier nothing looks at.

There's no schema-level "required" flag anywhere; `baseline` is a
documentation convention.

## `summary:`, and where it surfaces

Every entry carries a one-line `summary:`. It's the single source for the
"available, not installed" section of the status report and for the block
catalog in [`user-guide.md`](user-guide.md) — `tools/audit` fails when one is
missing, so the two can't drift apart through neglect.

## What is deliberately not syncable

- **`incubator/`** — blocks written but not validated on a real project. No
  manifest entry may point into it. See [`decisions.md`](decisions.md#d-01).
- **`handbook/`** — team reference material, written for people, never loaded
  into a session.

Third-party content, by contrast, **is** syncable: it's copied in plain text
into the block that uses it, with its `LICENSE` and a `SOURCE.md` beside it
(`common/skills/caveman/`). Those two travel to the consumer on purpose —
someone reading a skill in their own `.claude/` should be able to see it isn't
ours. `tools/audit` fails on a `SOURCE.md` missing a field, and on MIT content
shipped without its `LICENSE`.

## A report that knows when to stay quiet

`build_status_report` returns a single line, instead of the onboarding list,
when the target folder has neither `.git` nor a `.toolkit-sync-state`. The
user-scope hook runs in *every* folder, so without that condition a session
opened to edit one script would be met with a sync checklist — and the common
rules such a session needs come from `~/.claude/` (`common-rules-user`)
rather than from a project `.claude/` nobody asked for. See
[`decisions.md`](decisions.md#d-09).

## Mutual exclusion

The `process` group has three members — `process-none`, `process-light`,
`process-full`. `tools/sync` blocks syncing any one of them while another is
already registered in `.toolkit-sync-state`: it fails immediately, naming the
conflicting entry, before anything is written. See
`common/rules/process-profile.md` for the rule that asks the user to pick when
*none* is present — the tool enforces "not two," not "at least one."

That rule also states the case the tool can't see: a folder that is neither a
repository nor synced has no profile to pick and is never asked.

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

Whether a `tech-stack`, `suggested` or `optional` entry is worth adopting for a given
project is a judgment call, not something the tool enforces.
`tools/sync detect` surfaces a suggestion from marker files; a human
still decides whether to act on it.
