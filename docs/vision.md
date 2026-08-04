# Vision

## Why this exists

A multi-stack engineering team needs a shared baseline for how Claude
Code behaves across its projects — security and git-workflow rules that
apply everywhere, a process discipline every project opts into exactly
one of, and per-stack conventions (Python, Node.js/web, Rust, embedded
C, Simulink/MATLAB model-based design) that only apply where relevant.
Without a shared source, each project either reinvents these rules or
drifts out of sync with the rest of the team.

## The model: synced and committed, not installed

This repo is authored and validated content, not a runtime dependency.
A project adopts it by running `tools/sync` against a checkout of this
repo; the result — rules, skills, agents, hooks — lands as ordinary
files under the project's own `.claude/` (or `~/.claude/` for user-scope
tools), reviewed as a diff and committed like any other change. Once
synced, a project's `.claude/` works with no further dependency on this
repo being present, reachable, or even correctly configured — it's just
files the project owns.

This is a deliberate trade-off against a marketplace/plugin-install
model: less "install once, get automatic updates," more "you control
exactly when and what you pull in, and the result is fully yours to
read, diff, and modify." Re-running the same sync command later picks
up upstream changes explicitly, on the project's own schedule.

## Who this serves

- A team lead deciding what baseline every project should carry.
- Someone bootstrapping a new project who wants working conventions
  immediately instead of writing `.claude/rules/` from scratch.
- Someone adding a new tech stack to an existing project and wanting the
  matching conventions without hand-authoring them.
- This repo's own maintainers, adding or refining a block for the team.

## What this deliberately doesn't do

- It doesn't push updates to consuming projects — sync is always a pull,
  initiated from the consumer's side.
- It doesn't enforce that a project adopts any particular block beyond
  the `baseline` tier being a stated team expectation — `stack` and
  `optional` tiers are always a judgment call.
- It doesn't try to be a general-purpose plugin system; each block is
  scoped to what a `.claude/` directory can natively express (rules,
  skills, agents, hooks).
