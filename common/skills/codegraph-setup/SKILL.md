---
name: codegraph-setup
description: Install, first-index, verify or remove CodeGraph on this project — the local code graph queried through codegraph_explore. Use when setting it up, when it needs repairing, or when the user wants it gone. A plain re-index of a stale index is the codegraph-reindex agent's job, not this skill's.
when_to_use: Use when asked to set up, index, troubleshoot or uninstall CodeGraph on this project. For a stale index, delegate to the codegraph-reindex agent instead.
disable-model-invocation: true
---

# CodeGraph setup

CodeGraph indexes the repository into a **local** graph and exposes it to the
agent as an MCP tool. Nothing leaves the machine.

**It is not installed by default.** The baseline ships this skill and the
`codegraph` rule; the tool itself is a per-project decision. The rule is
written to stay silent where the tool is absent.

Provenance, kept here rather than in a separate file because it's exactly what
a consumer needs to see before installing anything:

- Upstream: https://github.com/colbymchenry/codegraph — MIT
- **Expected version: `0.x`.** Bumping this pin is a deliberate change to the
  toolkit, not something to do mid-task.
- Indexes 30+ languages, C and C++ among them (`.c`, `.h`, `.cpp`, `.hpp`,
  `.cc`). `codegraph-freshness.sh` carries a copy of the extension list it
  uses to decide whether a repo is worth indexing — **re-check that list
  against upstream when bumping the pin**, or the suggestion starts firing on
  repos the tool can't read.

## What it actually installs

Say this out loud before installing, so nobody inherits a black box:

| What | Where | Removable |
| --- | --- | --- |
| The `codegraph` binary | its own runtime, no Node required | yes |
| The index | a local SQLite database in the repo's data dir | yes, it's a file |
| An MCP server registration | the agent's config (`codegraph serve --mcp`) | yes |
| Git hooks that re-index on change | this repo's `.git/hooks` | yes |

## Install and index

1. Install the CLI per the upstream README for this platform.
2. `codegraph --version` — compare with the pin above. Report a mismatch
   instead of silently accepting it.
3. Run the interactive installer to register the MCP server for this agent.
   **Decline the option to write guidance into `AGENTS.md`/`CLAUDE.md`.** That
   file is owned by the `context-quality` block; the guidance we want is
   already in this block's `codegraph` rule, and a second, differently-worded
   copy is how the two start contradicting each other.
4. Index the repository.
5. **Verify before declaring victory**: ask `codegraph_explore` for a symbol
   you know exists and check the answer names the right file.

## Keep the tool set small

Leave the default single `codegraph_explore` tool exposed. The upstream
`CODEGRAPH_MCP_TOOLS` variable can re-enable five more narrow tools
(`codegraph_search`, `codegraph_callers`, `codegraph_callees`,
`codegraph_impact`, `codegraph_node`) — don't, unless a concrete need shows up.
One well-described tool gets reached for reliably; a menu of six with fuzzy
boundaries gets skipped.

## Refresh

The upstream git hooks re-index on change, so this is normally automatic. The
`codegraph-freshness.sh` hook shipped alongside this skill only speaks when the
index is actually behind. It exits immediately when CodeGraph isn't installed,
which is why it can live in the baseline.

**Re-indexing itself is not this skill's job**: it's the `codegraph-reindex`
agent, which runs on a cheaper model because running one CLI command and
checking a timestamp needs no judgment. Delegate to it and move on. Everything
else on this page — install, first index, verify, remove — stays here: it
downloads and runs a third-party binary, which is not a decision to hand to a
cheap model.

If it speaks every session, the git hooks aren't firing: fix that rather than
re-indexing by hand forever.

The index describes the code *as last indexed*: after large edits in the same
session, read the file you just changed rather than asking the graph about it.

When to reach for `codegraph_explore` is the `codegraph` rule's job, not this
skill's — it's loaded in every session, this file only when someone is
installing or repairing something.

## Remove it

1. Delete the MCP server registration from the agent config.
2. Remove the git hooks the installer added.
3. Delete the index database.
4. Uninstall the binary.

That's all. The rule and this skill stay — they're part of the baseline, and
the rule is conditional on `codegraph_explore` actually being available, so a
project without the tool is left alone.
