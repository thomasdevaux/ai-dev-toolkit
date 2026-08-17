# Maintaining this toolkit

How a **block** becomes files in a project's `.claude/`, and how to add,
change, or remove one. This is the repo's own maintenance reference —
not something synced to consuming projects.

`.claude/` here is committed, real `tools/sync` output — this repo dogfoods
its own sync mechanism — but `common/`, `tech-stacks/`, `project-type/`, etc.
remain the edited source, not `.claude/`. Commits land directly on `main`.
Don't apply `common/rules/*` conventions (branch-per-feature, PR review,
etc.) to work on this repo itself unless the user asks.

## Blocks and the manifest

`sync-manifest.yaml` is the *index* of every syncable block, not the
place their entries live. A block is a directory tree under `common/`,
`context-quality/`, `project-type/<variant>/`, `tech-stacks/<lang>/`,
`user-tools/<topic>/`, `self-check/`, or `suggested/<topic>/`, shaped
internally like `.claude/` itself (`rules/`, `skills/`, optionally
`commands/`, `agents/`, `hooks/`) — **and it owns a `manifest.yaml`
fragment of its own**, listing only its own entries. The root
`sync-manifest.yaml` is a flat list of `- include: <path>` lines, one
per directory, resolved relative to the toolkit root; `tools/sync/manifest.py`
follows them (nesting is fine, a cycle is a `ManifestError`) and merges
every fragment into one id-keyed table. That's what keeps the directory
tree the actual index — `sync-manifest.yaml` stays a short table of
contents instead of the one file every block competes to be readable in.

Each block has one `type: file` entry in its fragment: `id`, `source`
(the block's directory), `target: .claude/`, `scope` (`project` or
`user`), `tier`, a one-line `summary:`, and `detect` if it's a tech
stack. `tools/sync` reads the entry, diffs the block's files against the
project's `.claude/`, and only writes after confirmation — never
deletes, always shows the diff first.

A block's dependency on an official Anthropic plugin (`gitlab`, a
language server, ...) is its own `type: official-plugin` entry rather
than a nested dependency declaration. Syncing it patches only the
`enabledPlugins` key of `settings.json`, key by key.

### Where a new entry's fragment goes

One axis only: **does it have content of its own to vendor** (`rules/`,
`skills/`, `hooks/`)? Never split by scope — `scope:` is a field on the
entry, not a directory criterion; nothing here is organized "project vs.
user" (that's exactly the confusion to avoid re-introducing).

- **Has content** → its own topic directory, owning a `manifest.yaml`
  next to that content (`common/manifest.yaml`,
  `tech-stacks/python/manifest.yaml`, ...). A new language, a new
  per-machine tool, or a new opt-in skill each get one subdirectory
  under `tech-stacks/`, `user-tools/`, or `suggested/` respectively —
  **never a new directory at the repo root**. The root's set of
  category directories (`common/`, `context-quality/`, `project-type/`,
  `tech-stacks/`, `user-tools/`, `self-check/`, `suggested/`) is meant
  to stay closed; it mirrors the four tiers in the table above and a
  new one should be as rare as a new tier.
- **No content, just a `plugin_ref`** (nothing to vendor) → a section
  in `plugins.yaml` at the toolkit root, grouped by topic with a
  comment banner (git hosting, language servers, ...) — not a new
  file or directory per plugin. It stays flat because it costs nothing
  to keep flat: unlike `rules/*.md`, `plugins.yaml` is never loaded
  into a Claude session, only read by `tools/sync` — so its size is a
  human-readability concern, solved by section banners, not by
  directory-per-entry.
- **Exception**: a content-free plugin still gets its own directory
  when its *tier* is `suggested` (`suggested/gitlab/manifest.yaml`,
  `suggested/skill-creator/manifest.yaml`). Not a scope split — the two
  sit at opposite scopes and it changes nothing — a directory because
  `tier: suggested` is exactly what `suggested/` already means, and an
  opt-in entry is the one a reader goes looking for by name. What stays
  in `plugins.yaml` is therefore everything *not* suggested: `baseline`
  and `tech-stack` plugins, which nobody hunts for one by one because
  they arrive on their own.

Target layout, showing where growth is contained:

```
ai-dev-toolkit/
├── sync-manifest.yaml     # index: "- include: <path>" per directory below
├── plugins.yaml            # content-free non-suggested plugins, by topic
│
├── common/                 # fixed: one block, tier: baseline, both scopes
├── context-quality/        # fixed: one block, tier: baseline, project only
├── self-check/             # fixed: one block, tier: baseline, both scopes
│
├── project-type/             # bounded: one subdir per choice-group variant
│   └── none/  app/  embedded-fccu/
│
├── tech-stacks/             # grows HERE: one subdir per language
│   └── python/  rust/  go/  dotnet/  ...
│       shared/              # not a block: files two stacks deploy verbatim,
│                            # pulled in via a `shared_files:` entry field
│
├── user-tools/               # grows HERE: one subdir per user-scope tool
│   └── statusline/  ...
│
├── suggested/                 # grows HERE: one subdir per opt-in block/plugin
│   └── gitlab/  skill-creator/  ...
│
└── incubator/  handbook/  docs/  templates/  tests/  tools/  demo/
    # infra and non-syncable content — not blocks, not manifest-bearing
```

New content nests inside an existing category directory; a new
content-free plugin adds a section to `plugins.yaml`, or a subdirectory
under `suggested/` if that's its tier. None of them adds a directory at
the repo root.

Every fragment's `summary:` fields are what a reader sees when they
inspect a directory or run `tools.sync status`. There is no separate
rendered catalog to keep in sync with them.

## The four tiers

Every manifest entry has a `tier` — the only source of truth for
governance status; never encode it in the block's directory name, since
a block that changes tier (e.g. `tech-stack` → `baseline`) should never
need a rename.

| Tier | Meaning | Enforcement |
| --- | --- | --- |
| `baseline` | Expected on every project. | Team-process expectation; `tools.sync status` lists it as missing until synced. |
| `choice-group:<name>` | Exactly one variant of `<name>`. | Blocked at sync time — `tools/sync` refuses a second entry sharing the tier while one is already registered; `tools.sync switch` is how a project changes its mind. |
| `tech-stack` | Suggested from marker files — `detect:` (any one marker) or `detect_all:` (every marker, same directory). Use `detect_all:` when the block covers one framework inside a language, so the language marker alone doesn't fire on every project. | Never auto-synced — `tools/sync detect` only prints a suggestion. |
| `suggested` | Useful, never expected — the only opt-in, never-imposed tier. | Listed once under "available, not installed" (`tools.sync status`, and the `SessionStart` hook), never blocking. Synced by id only. |

### A file two blocks ship identically

`shared_files:` on an entry deploys a file that lives once in the checkout
into that block's target tree:

```yaml
shared_files:
  - source: tech-stacks/shared/react-conventions.md      # from the toolkit root
    target: skills/<skill>/references/react-conventions.md  # under the entry's target
```

React is the mandated frontend for both webview stacks, so
`react-conventions.md` is the same file for Tauri and for Wails. Two copies in
the checkout drift; one copy referenced by a path would leave the other block
pointing outside itself. This does both: one source, and a real file inside
each block once synced — so a project that syncs only `tech-stack-go` still
gets a self-contained skill. The deployed file is planned, hashed, drift-checked
and pruned exactly like the block's own files.

Reading `tech-stacks/go/` in the checkout therefore no longer shows everything
the block delivers — the entry's `shared_files:` is the place that says so.

A former `optional` tier (opt-in but invisible everywhere) was folded into
`suggested` — visibility was the only real difference, and staying invisible
by default just meant nobody found the entry to opt into.

### Declining an offer

`tech-stack` and `suggested` entries are the two things the `SessionStart`
hook keeps printing ambiently. Offering the same never-wanted block every
session forever is how the whole report gets tuned out, so a project can say
no once:

```
python -m tools.sync dismiss <id...> --toolkit-root . --project-dir <path>
```

It records the ids under `dismissed` in `.toolkit-sync-state` and the two
discovery sections skip them from then on. Purely a reporting filter: a
dismissed entry is still syncable by id at any time, and syncing it clears
the dismissal. `--undo` puts it back in the offer list. `/toolkit-feat`
runs this when the user declines something it just listed — it's the one
sync-adjacent command the agent may run itself, because it writes no files.

### Letting the installer pick project vs. user scope

A `type: official-plugin` entry's `settings_patch` lands in whichever
`settings.json` the sync targets, and every entry currently fixes that
choice itself, deliberately: `gitlab` is `scope: project` because MR and
issue access is a property of the repository, identical for everyone who
clones it; `skill-creator-user` is `scope: user` because authoring a skill
is an occasional individual act, and a project entry would charge the whole
team a permanent `enabledPlugins` line for it; the LSP entries are
`scope: user` as a per-machine tool preference with no project-level
meaning. None of them asks.

When a choice is *genuinely* ambiguous — someone might reasonably want the
entry either committed to the team's project or kept private to their
machine — the mechanism is **two manifest entries**: one `scope: project`,
one `scope: user`, same `plugin_ref`, ids distinguished by a `-user` suffix
on the user-scope one. That's all of it: whoever syncs picks which id to
run, say `sync <thing>` (writes to the project's `.claude/`) or
`sync <thing>-user --user` (writes to `~/.claude/`). No prompt, no dynamic
scope field — just two ids, same as picking between two `tech-stack`
blocks; pass `--user` whenever the chosen id is the `scope: user` one,
exactly as for any other user-scope entry.

**No entry uses this today**, and the bar for the first one is high: a
plugin whose value genuinely differs per person *and* per project, rather
than one where the honest answer is simply that one of the two scopes is
right. Reach for it only after failing to argue a single scope. It is kept
because `tools/sync` supports and tests it (`tests/tools/sync/test_status.py`
covers the user-scope filtering), not because it is the default shape.

## How rules actually load

Claude Code loads `.claude/rules/*.md` natively at the project level: a
rule with no `paths:` frontmatter loads at launch with the same priority
as `CLAUDE.md`; a rule with `paths:` loads only when Claude reads a
matching file. That's why every rule in this repo is a plain
`rules/<topic>.md` file with `paths:` frontmatter when it needs scoping
— no companion "rules" skill required. A `skills/<name>/SKILL.md` is
reserved for a genuine on-demand procedure, not a wrapper restating a
rule file.

That difference is what the two character budgets below encode. An
unscoped rule is charged to every session whether or not it turns out to
be relevant, so it competes with every other unscoped rule for the same
room. A scoped one is charged only to sessions that open a matching file,
and two languages' scoped rules can never be loaded beside each other —
which is why `tools/audit` sums them into a separate, looser budget rather
than making a Python rule pay for a Go one.

## Which model a block's entry point runs on

A block's content is not all worth the same model, and the harness only lets
you say so in two places:

| Where | `model:` field | Runs on |
| --- | --- | --- |
| `commands/<name>.md` | **yes** | the model it names |
| `agents/<name>.md` | **yes** | the model it names |
| `skills/<name>/SKILL.md` | **no** | the session's model, always |
| `rules/<topic>.md` | **no** | the session's model, always |
| `hooks/*.sh` | n/a | nothing — it's a script |

So a skill cannot be made cheap. It can only *delegate* to something that is.
`tools/audit` requires `model:` on every command and every agent — not any
particular value, just an explicit one, because the silent default is the
most expensive model in the session.

### Which side a piece of work falls on

- **Mechanical *and* isolatable** — it takes a stated input, drives a script
  or compares against a fixed vocabulary, and hands back a short result →
  `agents/<name>.md`, `model: haiku`. `common/agents/codegraph-reindex.md`
  (run the indexer, check a timestamp) and
  `project-type/app/agents/docs-lint.md` (file presence, status vocabulary,
  index drift) are the two examples.
- **Mechanical but inline, or the cheapest step of a larger procedure** —
  `commit-message-format` fires mid-`git commit` and outputs three lines;
  `init-project-docs`' on-hold stubs are five fixed-text writes inside a
  five-step procedure whose value is elsewhere. No wrapper: the delegation
  hop costs more than the tier saves, and splitting a procedure to offload
  its trivial step is complexity with negative value.
- **Judgment on under-specified input** — `improve-architecture`,
  `audit-project-context`, the stack architecture skills. Session model,
  never pinned down. A cheap model here returns plausible, wrong architecture
  advice, which is the most expensive failure mode this toolkit has.
- **A skill with both halves** → split it, don't downgrade it. The agent
  produces findings and ranks nothing; the skill arbitrates them. That is
  what `adr-cleanup` and `audit-docs` now do, and it mirrors the
  report-then-grill split `improve-architecture` already used.
- **One agent per *kind* of pass, not per skill.** `adr-cleanup` and
  `audit-docs` had the same mechanical slice, so they share one `docs-lint`
  rather than owning two agents that would drift apart.

A `SessionStart` hook's `ACTION:` output is outside all of this: it is read by
the session's model by construction, so the only lever there is writing less
of it, or firing the hook less often.

**Measured savings: not yet.** `handbook/token-economy.md` records what the
toolkit has actually measured, and this lever is not in it. Treat the split
above as an argument, not a result, until a number lands there.

## Choice groups

A `choice-group:<name>` tier permits exactly one variant per project.
Adding a new group means: pick a `<name>`, give every variant `tier:
choice-group:<name>`, and add a rule (following
`common/rules/project-type-profile.md`'s pattern) that prompts the user when
none of the group's variants are present. `tools/audit` checks that every
`choice-group:<name>` has at least two members — a lone member is a dead
group.

### Changing a project's mind

```
python -m tools.sync switch <group> <id> --toolkit-root . --project-dir <path>
```

`sync` alone refuses the second member, on purpose. `switch` drops the
outgoing entry from `.toolkit-sync-state`, syncs the incoming one, and lets
the ordinary orphan prune offer to delete the files the old one left behind
— all on the usual confirmation prompts (`--yes` skips them).

The point is that the state file is never hand-edited: it also carries the
per-file hashes drift detection reads, so an edit that looks like it only
removes an entry is one typo away from silently disabling drift reporting.

### The `project-type` group, in full

`common/rules/project-type-profile.md` keeps only the standing rule; this is
the reference the rule points to when no profile is present yet:

| Profile | For what | What it implies |
| --- | --- | --- |
| `project-type-none` | Script, one-shot, tinkering session. | Nothing to maintain: no docs, no requirements, no ADRs. |
| `project-type-app` | An application or tool with its own repository. | Doc map, requirements list, ADR log, architecture review. |
| `project-type-embedded-fccu` | Embedded, safety-critical or certified software (e.g. a fuel cell control unit). | Extra rigor — **not designed yet**, see below. |

`project-type-embedded-fccu` is currently a stub, kept in the manifest
rather than parked in `incubator/` because adopting it is itself
meaningful: a project that picks it is saying `project-type-app`'s
discipline doesn't fit as written. Its rule file is deliberately tiny —
what it can't do on disk is explained here rather than paid for in every
session's context.

Being a choice-group sibling of `project-type-app`, its files never land
alongside it: apply `project-type-app`'s rules from the toolkit checkout by
hand in the meantime, don't expect them on disk. If the project's needs
genuinely exceed them (regulatory traceability, formal audit trail,
real-time constraints), say so to the user instead of inventing ad hoc
process — that gap is exactly what this profile will eventually fill.

Note what it does **not** gate: the `commit-message-format` and
`desktop-app-architecture` skills live in `common`, so every profile gets
them, `project-type-none` included. The branch/merge workflow, by contrast,
is `project-type-app`'s alone.

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

   A block may also carry `commands/<name>.md` (a slash command the user
   types) and `agents/<name>.md` (a sub-task the session delegates). Both
   **must** declare `model:` — see "Which model a block's entry point runs
   on" for which side a piece of work falls on; `tools/audit` fails without
   it. Nothing in `tools/sync` needs to know: a block's whole tree is
   copied, so a new subdirectory deploys on its own.

   **For the skill body itself, `skill-creator` and `new-block` compose —
   they are not alternatives.** `new-block` answers placement: which
   directory, which tier, the manifest entry, the character budget, the
   audit, the sync round-trip. It says almost nothing about writing a good
   `SKILL.md`. The `skill-creator` plugin (`sync skill-creator-user
   --user`) covers exactly that gap — a writing guide, and a script that
   tunes the `description` for triggering accuracy, which `tools/audit`
   cannot check (it only verifies the frontmatter field exists, never that
   it fires on the right prompt). Caveat: its eval loop expects a directly
   invocable skill, so evaluate a block's skill from the scratch project of
   step 4, not from `common/skills/` in place.
3. Register the block in its directory's own `manifest.yaml` (create the
   file if the directory is new): one `type: file` entry (`id`, `source`,
   `target: .claude/`, `scope`, `tier`, `summary:`, `detect` if a tech
   stack), plus a `type: official-plugin` entry for any official plugin
   it depends on. If the directory is new, add its
   `- include: <dir>/manifest.yaml` line to the root `sync-manifest.yaml`.
   `summary:` is mandatory — `tools/audit` fails without it.

   **Before adding a stack or a rule set, ask whether it's been used.**
   Content that hasn't been validated on a real project belongs in
   `incubator/`, absent from the manifest.
4. Test locally: `python -m tools.sync sync <id> --toolkit-root . --project-dir /path/to/scratch --yes`,
   confirm the expected files land, then re-run the same command and
   confirm it reports nothing to synchronize (idempotence). Add a dummy
   sub-project under `../demo/` if the block needs one — see
   [`../demo/README.md`](../demo/README.md).
5. Run `python -m tools.audit --toolkit-root .` — checks `paths:`
   overlap, the rule character budgets, choice-group integrity,
   third-party provenance, missing `summary:`, and the frontmatter of every
   skill, command and agent (including their `model:`).

## Modify an existing block

- Edit `rules/<topic>.md` directly — it's both the reviewable source and
  what actually loads.
- If you change a rule's `paths:` scoping, run `python -m tools.audit
  --toolkit-root .` — it checks for new overlap with other blocks, and
  adding or removing `paths:` also moves the file between the two session
  budgets.
- Re-test the affected manifest entry end to end (sync into a scratch
  project, confirm idempotence) before committing.

## Deprecate a block

- Remove its entry (or entries) from its directory's `manifest.yaml`. If
  that empties the file, delete it and remove the matching `- include:`
  line from the root `sync-manifest.yaml`.
- If it belonged to a `choice-group:<name>`, run `python -m tools.audit
  --toolkit-root .` to check the group still has at least two members.
- Delete the block's directory.
- Remove its section from `../demo/README.md` and delete its demo
  sub-project under `../demo/`, if any.
- Already-synced projects keep their copy of the deprecated block's files
  until their next sync, where the orphan prune offers to delete each one.
  A file is never removed without that confirmation.

## Before committing

- Keep each `rules/*.md` under 4,000 characters, and the worst-case set a
  project syncs under 20,000 for always-on rules / 16,000 for
  `paths:`-scoped ones (`tools/audit` enforces all three). A rule that
  won't fit usually has detail in it that belongs in a skill, which loads
  on demand rather than on every session.
- Follow `../project-type/app/rules/git-workflow-app.md` and
  `../project-type/app/skills/git-workflow-app/SKILL.md`,
  `../common/skills/commit-message-format/SKILL.md`, and
  `../common/rules/language.md` for everything you write here.
- Python changes under `tools/`: `pip install -r tools/sync/requirements.txt -r requirements-dev.txt`
  once, then `python -m pytest tests/ -v` before committing.

## Gotchas

- A file under a block's `hooks/` directory ending in `.sh` gets `chmod
  +x` automatically when `tools/sync` writes it — don't rely on the
  source checkout's own executable bit (this toolkit is developed on
  Windows).
- `python -m tools.sync sync <id...>` with **no** ids expands to every
  `tier: baseline` entry for the target scope, plus every entry already
  synced (any tier) that has drifted — so it also re-syncs an adopted
  `tech-stack`/`choice-group`/`suggested` entry. Adopting a **new** one still
  needs an explicit id (or `switch`, for a choice-group).
  `python -m tools.sync status --toolkit-root . --project-dir <path>`
  (add `--user` for `~/.claude`) is the read-only version — same report,
  no writes.
- **A hook must be silent when its check passes.** `context-check.sh`
  and `codegraph-freshness.sh` print nothing on a healthy project; a hook
  that speaks every session stops being read.
- **`common/` is deployed at both scopes** (`common-rules` and
  `common-rules-user`). Anything added there runs in `~/.claude/` too, so
  it must make sense in a folder that is not a project — that's why a
  hook there self-guards, and why `context-quality/` is a separate block.
  A project that syncs `common-rules` while its user also has
  `common-rules-user` at `~/.claude` ends up with `common/` loaded twice
  in that project's sessions (double token cost, duplicate `/skill`
  entries) — known and accepted, not a bug to file. The project-scope
  copy is the one that must exist and be committed, since a teammate
  cloning the repo without a matching `~/.claude` still needs it;
  de-duplicating by skipping it at sync time was tried and reverted
  because it broke that guarantee. Trimming the `~/.claude` copy instead
  is a per-machine call for whoever hits the duplication, not something
  `tools/sync` should decide on a single project's behalf. The same goes for
  `settings_patch` hook registrations: `codegraph-freshness.sh` is registered
  by both entries, so it *executes* twice per session in such a project.
  Accepted for the same reason — which is why that hook has to stay cheap
  (its index lookup prunes `node_modules/` and friends) and silent when the
  index is fresh, so paying for it twice costs nothing worth removing.
- **A `bin/`-level script is a bare name plus a `.cmd` twin**, not a
  `.sh`/`.ps1` pair: `bin/toolkit-sync`/`bin/toolkit-sync.cmd`,
  `bin/toolkit-status`/`bin/toolkit-status.cmd`,
  `bin/toolkit-help`/`bin/toolkit-help.cmd`. Each resolves its own directory
  and takes the parent as the toolkit root (`cd`s there before invoking
  Python) so it works from any cwd once cloned — `install.sh`/`install.ps1`
  are the one exception, both in staying at the repo root and in resolving
  themselves: they exist specifically to be curled before any checkout
  exists, so they clone one instead of locating one.
- `{{VERSION}}` in a manifest's `settings_patch` is expanded from the
  `VERSION` file when the manifest loads (the startup banner uses it). Write
  the placeholder, never the number — a hand-written version is one nobody
  remembers to bump, it just quietly starts lying. Expansion happens at load
  time, so `status`, the diff and `sync` all agree and a bump shows up as
  ordinary drift.
