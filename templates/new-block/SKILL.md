---
name: new-block-template
description: Scaffold a new block for this toolkit repo (org convention, process profile variant, or tech-stack convention), following the block-first layout and sync-manifest.yaml registration this repo uses. Use when the user wants to add support for a new tech stack, project type, or org-wide convention.
when_to_use: Use when asked to "add a new block", "create a block for <tech>", or "scaffold conventions for <language/tool>" while working in this toolkit repo.
disable-model-invocation: true
---

# New block template

Scaffold a new block in this repo: a directory tree (`rules/`, `skills/`,
optionally `agents/`, `hooks/`) registered as one or more entries in
`sync-manifest.yaml`.

This repo does not currently install this skill on itself (see
CLAUDE.md's "Self-application" section) — invoke it by pointing Claude at
this file directly, or by copying it into `.claude/skills/` locally if
you want it to auto-trigger in a session.

## Procedure

1. **Ask the required questions** if not already answered by the user:
   - Block topic (one sentence, e.g. "Go project conventions").
   - Location: `common/` (org-wide, singleton), `process/<variant>/` (a
     new mutually-exclusive process profile — confirm the full set of
     variants and their shared choice-group name now), or
     `tech-stacks/<lang>/` (one language/tech stack).
   - `tier` for its manifest entry: `baseline` (expected everywhere),
     `choice-group:<name>` (process variants), `tech-stack` (with a
     `detect` marker-file list), `suggested` (useful and listed once as
     available, never pressed), or `optional` (opt-in and never surfaced
     at all — for something the user syncs by id because they already
     know they want it).
   - A one-line `summary:` — mandatory, and the source for both the
     status report and the user-guide catalog.
   - **Whether it belongs in the manifest at all.** Content not yet used
     on a real project goes to `incubator/`, unsynced, until it has.
   - `scope`: `project` (written to a consumer's `.claude/`) or `user`
     (written to `~/.claude/`).
   - Does it need a subagent with a pinned model/effort for a specific
     task type? If yes, get the task type and whether it needs a
     stronger or lighter model than the session default.
   - Does it need a hook (deterministic action at a lifecycle event, not
     just a reminder Claude might skip)? If yes, get the event and what
     the hook should do.

2. **Create the directory skeleton** under the chosen location:
   ```
   <location>/
   ├── rules/
   ├── skills/
   ├── agents/      (only if a subagent was requested)
   └── hooks/        (only if a hook was requested)
   ```
   This mirrors the target `.claude/` layout internally (`rules/`,
   `skills/`, `agents/`, `hooks/` are exactly the directories a consumer's
   `.claude/` uses), which is why a single `sync-manifest.yaml` entry with
   `source: <location>`, `target: .claude/` copies the whole block
   correctly — no per-subdirectory entries needed.

3. **Write passive rules as native `.claude/rules/*.md`, not a wrapper
   skill**: put the concrete, verifiable rule text directly in
   `rules/<topic>.md`. Add `paths:` YAML frontmatter only if the rule
   should apply to a subset of files; leave it unscoped otherwise. Claude
   Code loads `.claude/rules/*.md` natively (confirmed against the
   `.claude/rules/` mechanism in Claude Code's own docs) — there is no
   companion "rules" skill to also write.

4. **Write on-demand workflow skills only for genuine procedures**: name
   them for the task they support (e.g. `ship-tool`, `build-toolchain`),
   not generically ("helper", "utils"). Each `SKILL.md` needs a real,
   runnable procedure — not a placeholder, and not a rules-wrapper that
   just restates a `rules/*.md` file (that pattern is deprecated; see
   step 3).

5. **If a subagent was requested**, write `agents/<name>.md` with `name`,
   `description` (what task type triggers it), `model`, and `effort`
   explicitly set — do not leave these to inherit if the whole point was
   to pin them.

6. **If a hook was requested**, write `hooks/<name>.sh` (or the
   appropriate script type) and wire it through the manifest entry's
   `settings_patch` on the relevant `hooks.<Event>` key — see
   `context-quality`'s `context-check.sh` entry in `sync-manifest.yaml`
   for a worked example, including the executable bit that `tools/sync`
   sets automatically for anything under `hooks/*.sh`. **The hook must
   print nothing when its check passes**: one that speaks every session
   stops being read.

7. **Register the block** in `sync-manifest.yaml`: add one `type: file`
   entry with `id`, `source: <location>`, `target: .claude/`, `scope`,
   `tier`, `summary`, and `detect` if it's a tech stack. Add a separate `type:
   official-plugin` entry (with its own matching `detect` if it's a
   tech stack) for any official Claude Code plugin the block depends on,
   rather than bundling it into the block's own entry.

8. **Self-check before finishing**:
   - Does every skill have a `description` specific enough that Claude
     would actually invoke it for the right task?
   - Run `python -m tools.audit --toolkit-root .` from the repo root —
     it checks `paths:` overlap against every other block, the
     200-cumulative-line cap on `rules/*.md`, and choice-group integrity
     in `sync-manifest.yaml`. Fix anything it reports.
   - Test the new entry end to end: `python -m tools.sync sync <id>
     --toolkit-root . --project-dir <scratch-dir> --yes`, confirm the
     expected files land under `<scratch-dir>/.claude/`, then re-run the
     same command and confirm it reports nothing to synchronize
     (idempotence).

9. **Add or update a `demo/` fixture** exercising the new block's scoped
   rules and skills, matching the pattern of the existing fixtures under
   `demo/`.
