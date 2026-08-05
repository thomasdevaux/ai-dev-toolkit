# Decisions

Why the non-obvious choices were made. `architecture.md` is the *what*; this
is the *why*. Append-only: a decision is never edited to reverse it, a new
entry marked `superseded` replaces it.

---

### D-01 — The manifest exposes only mature content; the rest is parked

**Status:** settled

Blocks that have never been used on a real project live in `incubator/` and
are absent from `sync-manifest.yaml`, so they cannot be synced.

**Why:** the first pass shipped five stacks whose rules were twenty lines of
deduced convention — MISRA, safety-critical, Simulink naming, per-language
style and packaging — none of it validated by anyone from the domain. A
published convention that has never been used is followed without being
questioned, and nobody can tell any more which parts are earned.

**Rejected:** deleting them outright (git would keep them, but the work is a
reasonable starting point and finding it again costs more than a directory);
keeping them in the manifest and improving them in place (the improvement
never happens while they still look official).

**Cost accepted:** the toolkit covers far fewer stacks than it did. That's an
honest reading of what it actually contains.

---

### D-02 — Three process profiles, and `none` is a real one

**Status:** settled

The `process` choice-group gains `process-none` alongside `light` and `full`.

**Why:** with only light and full, a one-hour script session was pressed into
a docs-and-requirements discipline it doesn't need, so the discipline gets
ignored — and once it's ignored somewhere, it's negotiable everywhere. Naming
"no process" as a legitimate choice is what keeps the other two meaningful.

---

### D-03 — `process-light` will eventually be renamed, but not now

**Status:** provisional

The name describes the amount of process, not the kind of product. The concept
it actually serves is "secondary app" — a tool or desktop application beside
the main product — as opposed to the embedded software that will belong to
`process-full`.

**Why not now:** renaming a manifest id breaks every consuming project's
`.toolkit-sync-state`. That needs a migration path, which is its own piece of
work.

---

### D-04 — Closed doc map, materialized as stubs at init

**Status:** settled

Ten slots, named in the rule from the start. Five are filled at init; five are
created as stubs carrying a guard line that names their trigger and forbids
early filling. Content that fits no slot is reported, never filed.

**Why:** the risk isn't too few documents, it's an *open* map where each new
topic lands wherever seems reasonable that day. Closing the map fixes routing.
Materializing it as files makes it visible in the tree rather than only in a
rule nobody re-reads.

**Rejected:** eight mandatory documents (the previous design — most projects
carried empty skeletons that read as neglect); create-on-demand with the map
living only in the rule (routing is correct but invisible).

**Cost accepted:** five near-empty files in every light project, and a real
risk that an agent fills a stub because it looks unfinished. The guard line is
the mitigation, and `audit-docs` checks for exactly that failure.

---

### D-05 — No commit-time documentation obligation; audit instead

**Status:** settled

The "update the doc in the same change" rule is gone. Staleness is caught by
`audit-docs`, run on demand and as a mandatory release step.

**Why:** a per-commit obligation taxes every change, including the ones that
document nothing, and is unenforceable anyway. A review that actually runs at
a moment that matters beats a rule everyone quietly skips.

**Cost accepted:** documentation drifts between audits. Accepted knowingly —
the release gate bounds the drift.

---

### D-06 — Absorb `claude-md-management`'s criteria, then drop the copy

**Status:** settled

The official plugin was first copied in, then read, and the parts worth
keeping were folded into `context-quality`'s own `init-project-context` and
`audit-project-context` skills — retargeted to `AGENTS.md`. The copy was then
deleted, and the `official-plugin` manifest entry with it.
`_prune_stale_plugins` offers each consumer its removal on the next sync.

**Why:** the plugin is `CLAUDE.md`-centric while this toolkit is
`AGENTS.md`-first with a `CLAUDE.md` pointer. As a dependency, it kept telling
users something our own rule contradicts, and cost 180 always-on tokens per
session to do it. Once its criteria live in our skills, carrying the file adds
nothing.

**Cost accepted:** no upstream updates to its criteria — nobody will tell us
if they improve. Attribution stays in both skills, which is what Apache 2.0
asks and what honesty asks anyway.

---

### D-07 — CodeGraph is integrated, not reimplemented

**Status:** settled

The toolkit wires up a third-party MCP code-graph server rather than writing
one. (It shipped as its own block at first; D-10 moved it into the baseline —
that's a placement change, not a reversal of this decision.)

**Why:** exploration is where the token budget actually goes, and a
tree-sitter-plus-index engine is not something to rewrite for the sake of
purity. What we own is the part that decides whether it gets used: an
always-loaded rule naming the trigger cases, a freshness guard, and a
documented removal path.

**Cost accepted:** an external dependency, contrary to the general preference
for native features. Bounded by the block documenting exactly what it installs
and how to remove all of it.

---

### D-08 — Hooks speak only when something is wrong

**Status:** settled

`context-check.sh` and `codegraph-freshness.sh` print nothing when their checks
pass. The always-on `remind-testing-policy.sh` hook was removed.

`toolkit-drift-check` was brought under the same rule afterwards: it used to
announce which checkout it resolved, then print the full status, on every
session. Now nothing is printed unless something is un-synced or drifted. The
informational parts it used to surface for free — suggested blocks, detected
stacks — stay reachable through `tools.sync status` and `tools.sync detect`,
run deliberately. That's the cost accepted: discoverability moves from ambient
to on-demand.

**Why:** a hook that speaks every session stops being read by the third one,
and it was restating a rule already loaded permanently. A rare signal is a read
signal.

---

### D-09 — The status report stays quiet outside a git repository

**Status:** settled

A folder with no `.git` and no `.toolkit-sync-state` gets one line instead of
the onboarding list. What a session opened there needs comes from
`~/.claude/` via `common-rules-user`.

**Why:** the toolkit has to survive "open a session anywhere to poke at a
script". Turning that into a sync checklist — and creating a `.claude/`
nobody asked for — is how a team toolkit becomes something people work around.

---

### D-10 — Caveman and CodeGraph ship in the baseline

**Status:** provisional

Both moved out of standalone `suggested` blocks into `common/`, which every
project gets: `common/skills/caveman/` (third-party text, verbatim, with its
LICENSE and SOURCE.md), and the `codegraph` rule + `codegraph-setup` skill +
freshness hook.

**Why:** measured context cost is what makes it defensible. A skill costs
nothing until invoked, and the LSP-style plugins the team wants alongside them
measure at zero always-on tokens. Making them baseline removes a decision
nobody was going to make deliberately.

**What it required:** the `codegraph` rule had to be rewritten as
*conditional*. Its earlier wording asserted "this project has a CodeGraph
index" — loaded everywhere, that would send the agent after a tool most
projects don't have. It now applies only when `codegraph_explore` is actually
available, and the hook exits immediately when the binary isn't installed.

**Provisional:** if the always-loaded `codegraph` rule proves to be noise on
projects without the tool, it moves back to a `suggested` block. Marked so
nobody has to argue that it was always meant to be permanent.

---

### D-11 — `stack` becomes `tech-stack`, everywhere

**Status:** settled

The tier, the directory (`stacks/` → `tech-stacks/`) and the entry ids
(`stacks-python` → `tech-stack-python`) all use the same word.

**Why:** "stack" alone reads as ambiguous at a glance in a manifest that also
talks about profiles, blocks and tiers. Renaming one of the three and not the
others would have been worse than not renaming at all.

**Cost accepted:** already-synced projects carry the old tier string in
`.toolkit-sync-state`. It only matters for choice-group conflict detection,
which no `tech-stack` entry participates in, so nothing breaks.

---

### D-12 — The 13 official language servers ship at user scope, in the baseline

**Status:** provisional

`sync --user` enables all of them in `~/.claude/`. No project-scope entry, and
no per-language decision.

**Why user scope rather than project baseline:** a scratch folder never syncs
anything, so a project-scope entry can't reach the case that motivated this —
opening a session anywhere to work on a script. `~/.claude/` applies in every
folder, including every project, so one set of entries covers everything.

**Why baseline rather than one pick per language:** measured context cost is
zero. The official catalog reports `always_on: 0` and `on_invoke: 0` for all
13 — they carry no skill, command or agent, they only wire up a language
server. There is nothing to ration.

**Cost accepted:** it isn't committed to any project repo, so a teammate who
skips the per-machine install doesn't have them. That's the same trade as the
status line, and the same fix: run the one command.

**Unverified, and the reason this is provisional:** what a language server does
when its binary isn't on the machine. The assumption is that it stays inert. If
one turns out to download something, fail loudly, or slow startup, drop that
entry — the per-language granularity is still there, we just aren't using it.

**Also fixed here (D-12):** `common-rules-user`, `user-statusline` and
`toolkit-self-check-user` moved from `optional`/`suggested` to `baseline` at
user scope. Until then, the documented `sync --user` command failed outright —
there were no user-scope baseline entries for it to expand to. `_missing_lines`
now filters by scope, so a user-scope baseline entry is never reported as
missing from a project it has nothing to do with.

---

### D-13 — The drift check exempts a toolkit checkout from itself

**Status:** settled

`toolkit-drift-check-impl.sh` exits silently, before producing any report,
when the project directory holds both `sync-manifest.yaml` and
`tools/sync/manifest.py`. Explicit `tools.sync status` calls are unaffected.

**Why:** this repo is not a consumer of its own blocks, so onboarding it into
itself is meaningless — and the report was worse than useless, because the
hook runs from a *cached* checkout that lags the working copy being edited. It
was listing entries this repo had already deleted, and pressing for a sync
that must never happen. A check that is wrong in the one repository where its
own authors read it is a check nobody trusts elsewhere either.

**Rejected:** unregistering the hook in this repo's `.claude/settings.json` —
hooks merge across scopes, a project file cannot remove a user-scope hook; a
marker file such as `.no-toolkit-sync` (invents a convention for one case,
and the two files already identify a checkout unambiguously).

**Cost accepted:** a consumer project that happens to vendor a full copy of
the toolkit at its root would also go silent. No such project exists, and it
would be the right behaviour anyway.
