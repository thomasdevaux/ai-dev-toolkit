---
name: audit-docs
description: Review the project's documentation against the doc map — missing slots whose trigger has fired, stale content, requirements consistency, misrouted or duplicated material. Use on demand, and as a mandatory step of the release procedure.
when_to_use: Use when asked to "audit the docs", "check the docs are up to date", and always before a release on a project that has adopted project-type-app.
disable-model-invocation: true
---

# Audit docs

Read-only review. **Report findings; apply nothing without confirmation.**

There is deliberately one depth level: the full review. It's the only thing
that runs, so it has to be worth running.

## Procedure

1. **Run the mechanical checks.** Delegate to the `docs-lint` agent with
   `scope: map,adr`. It returns, as a plain findings list: which of the ten
   doc-map slots are present or missing; markdown files under `docs/` that
   belong to no slot; on-hold stubs whose guard line is gone; the
   requirements file's structural validity (status vocabulary, unique ids,
   duplicate sections); and `docs/adr/INDEX.md` drift against the files on
   disk.

   It runs on a cheaper model on purpose — those are file-presence tests and
   table parses, and none of them needs judgment. Invoking this skill is what
   asks for that delegation; don't ask again. It ranks nothing and concludes
   nothing, deliberately: the interpretation is this skill's job.

   Turn what it returns into findings:

   - A **file outside the map** — say where its content belongs, or that the
     map needs a new slot (a decision for the user, not for you).
   - A **filled on-hold stub** — check step 2 for whether its trigger has
     actually fired. If it hasn't, that's invented content; flag it as such.
   - **Missing active slots** (`README.md`, `AGENTS.md`,
     `docs/architecture.md`, `docs/adr/INDEX.md`, `docs/requirements.md`)
     carry straight through.
   - **ADR findings** stay a cheap staleness signal here — see step 5.

2. **Triggers that have fired.** For each stub still on hold, check whether
   reality has moved past it:
   - `build-and-release.md` — does the repo build or publish an artifact
     (release job, packaging config, tagged versions)?
   - `developer-guide.md` — are there non-obvious prerequisites (toolchain,
     env vars, services to run locally)?
   - `user-guide.md` — is there a user-facing surface (CLI, GUI, API) used by
     someone other than the author?
   - `testing-strategy.md` — is there a visible coverage gap nobody recorded?
   - `vision.md` — is there a roadmap living in someone's head or in commit
     messages?

3. **Staleness.** For each filled doc, compare against `git log` on the area it
   describes. Flag a doc untouched despite related recent changes — name the
   commits that make it suspect, so the user can judge.

4. **Requirements against the code.** Step 1 already covered the table's
   structure. What's left needs reading the repository: rows the code
   contradicts (`done` but the feature isn't there; a shipped feature with no
   row at all).

5. **ADRs.** A cheap staleness check only — step 1 already reported whether
   `docs/adr/INDEX.md` is out of sync with the files in `docs/adr/`; carry
   that through and stop there. The full pass — stalled proposals,
   contradictions, consolidation — is `adr-cleanup`'s job; point the user at
   it instead of duplicating it here. Both skills reach the same `docs-lint`
   agent for the mechanical part, which is why the two never disagree on it.

6. **Content routing and duplication.** This is where the map earns its keep:
   - architecture explained in the `README`;
   - a decision buried in `architecture.md` instead of `docs/adr/`;
   - the same material in two docs, drifting apart;
   - a doc grown enough to need splitting — propose the split.

7. **Report.** A short list per category, most consequential first. State
   explicitly when a category is clean rather than omitting it — a silent
   section reads as "not checked". End with a proposed plan of fixes, and stop
   there.
