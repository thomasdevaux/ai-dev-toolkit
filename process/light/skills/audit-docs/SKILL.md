---
name: audit-docs
description: Review the project's documentation against the doc map — missing slots whose trigger has fired, stale content, requirements consistency, misrouted or duplicated material. Use on demand, and as a mandatory step of the release procedure.
when_to_use: Use when asked to "audit the docs", "check the docs are up to date", and always before a release on a project that has adopted process-light.
disable-model-invocation: true
---

# Audit docs

Read-only review. **Report findings; apply nothing without confirmation.**

There is deliberately one depth level: the full review. It's the only thing
that runs, so it has to be worth running.

## Procedure

1. **Map conformance.** Compare `docs/` against the ten slots of the
   `docs-map` rule.
   - A **file outside the map** is a finding on its own — say where its
     content belongs, or that the map needs a new slot (a decision for the
     user, not for you).
   - An **active slot missing** (`README.md`, `AGENTS.md`,
     `docs/architecture.md`, `docs/decisions.md`, `docs/requirements.md`).
   - An **on-hold stub that was filled anyway**, with no sign its trigger
     fired — that's invented content, flag it as such.

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

4. **Requirements.** Every table row has a valid status (`proposed`,
   `accepted`, `done`, `deferred`, `rejected`, `superseded`), unique ids, no
   duplicate lines. Flag rows the code contradicts (`done` but the feature
   isn't there; a shipped feature with no row at all).

5. **Decisions.** Every entry has a `D-<NN>` id and one of `settled`,
   `provisional`, `superseded`. Flag an entry edited in place to reverse an
   earlier one (should be a new `superseded` entry), and entries that
   contradict each other.

6. **Content routing and duplication.** This is where the map earns its keep:
   - architecture explained in the `README`;
   - a decision buried in `architecture.md` instead of `decisions.md`;
   - the same material in two docs, drifting apart;
   - a doc grown enough to need splitting — propose the split.

7. **Report.** A short list per category, most consequential first. State
   explicitly when a category is clean rather than omitting it — a silent
   section reads as "not checked". End with a proposed plan of fixes, and stop
   there.
