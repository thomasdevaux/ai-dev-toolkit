# Vision

## Why this exists

A multi-stack engineering team needs a shared baseline for how Claude
Code behaves across its projects — security and git-workflow rules that
apply everywhere, a process discipline every project opts into exactly
one of, a single well-shaped context file, and per-stack conventions
(Python, Rust, Go, .NET) that only apply where relevant. Without a shared
source, each project either reinvents these rules or drifts out of sync
with the rest of the team.

## Two deliverables, not one

- **Blocks** — the syncable conventions described below.
- **A handbook** — [`../handbook/`](../handbook/), the team's reference on
  working with an agentic coding tool. Never synced, never loaded into a
  session, written for people. It exists because a shared configuration
  doesn't teach anyone anything; the reasoning behind it does.

## Expose the mechanism, don't hide it

Everything a block does is a file someone can open and read. That's the
reason third-party content is copied in plain text with pinned provenance
rather than installed as a plugin, and why a block that wires up an external tool also
documents exactly what that tool installs and how to remove it.

The team is learning to work with agents. A magic install command teaches
nothing; a rule file you can read, disagree with and edit does.

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
  the `baseline` tier being a stated team expectation — `tech-stack`,
  `suggested` and `optional` tiers are always a judgment call.
- **It doesn't get in the way of a throwaway session.** Opening Claude in a
  folder to poke at a script creates nothing and asks nothing; the common
  rules come from `~/.claude/`. A toolkit that taxes small work is a toolkit
  people learn to work around.
- **It doesn't publish conventions nobody has used.** Blocks that haven't
  been validated on a real project stay in `incubator/`, absent from the
  manifest, until they have.
- It doesn't try to be a general-purpose plugin system; each block is
  scoped to what a `.claude/` directory can natively express (rules,
  skills, agents, hooks).
