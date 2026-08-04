---
name: audit-docs
description: Check the project's docs, requirements list, and testing-strategy doc for staleness or inconsistency. Use before a release, or when asked to "audit the docs".
when_to_use: Use when asked to "audit the docs", "check the docs are up to date", or before a release on a project that has adopted the process/light profile.
disable-model-invocation: true
---

# Audit docs

Read-only check. Report findings, don't fix them without confirming first.

## Procedure

1. **Doc set exists**: confirm `README.md`, `docs/architecture.md`,
   `docs/decisions.md`, `docs/user-manual.md`, `docs/developer-guide.md`,
   `docs/testing-strategy.md`, `docs/build-and-release.md`, and
   `docs/requirements.md` all exist.

2. **Staleness**: compare each doc's content against recent commits
   (`git log`) touching the area it describes — flag a doc that looks like
   it hasn't been updated despite a related recent change (e.g.
   `docs/build-and-release.md` unchanged despite a recent CI/build-config
   change).

3. **Requirements**: every line in `docs/requirements.md` has one of the
   six valid statuses (`proposed`/`accepted`/`implemented`/`deferred`/
   `rejected`/`superseded`); flag any missing or unrecognized status, and
   any requirement whose status looks contradicted by the code (e.g.
   `implemented` but the feature isn't found).

4. **Decisions**: `docs/decisions.md` has no entry that's been edited to
   reverse a prior one in place (should be a new appended entry marked
   `superseded` instead), every entry has a `D-<NN>` id and one of the
   three valid statuses (`settled`/`provisional`/`superseded`), and no
   entry contradicts another.

5. **Testing strategy**: `docs/testing-strategy.md`'s description of what's
   covered roughly matches the actual test suite; flag tests that exist but
   aren't mentioned, or claimed coverage that isn't backed by a test.

6. **Report**: a short list — missing docs, staleness flags, requirements
   issues, decision-log issues, testing-strategy mismatches. If nothing is
   found, say so explicitly rather than omitting the section.
