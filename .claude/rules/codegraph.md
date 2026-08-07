# Code navigation: prefer the graph, when there is one

**Only applies if the `codegraph_explore` tool is available in this session.**
Check before reaching for it; stay silent where it's absent — grep and glob
are simply the tools there, and `codegraph-setup` explains how to add it.

When available, it's the first reflex for symbol-level questions (where's X
defined, who calls Y, blast radius of Z) — it answers from an index instead of
reading files one at a time. Keep grep/glob for free text, comments, strings,
filenames.

**An empty answer usually means a stale index, not a missing symbol.**
Re-index once, ask again, before falling back to grep — see `codegraph-setup`.
