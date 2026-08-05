# Code navigation: prefer the graph, when there is one

**Only applies if the `codegraph_explore` tool is available in this session.**
It isn't installed everywhere, and this rule ships in the baseline — so check
before reaching for it, and never announce a graph the project doesn't have.
Where it's absent, grep and glob are simply the tools, and the
`codegraph-setup` skill explains how to add it if the project would benefit.

When it *is* available, it's the first reflex for symbol-level questions, not
the fallback: grep opens files one at a time and costs tokens proportional to
what it reads, the graph answers from an index.

Reach for it on:

- *where is X defined* — a function, a type, a constant;
- *who calls Y* — callers, callees, call paths;
- *what breaks if I change Z* — blast radius before an edit.

Keep grep and glob for what they're genuinely better at: free text, comments,
strings, configuration, filenames, and anything the index doesn't cover.

**An empty answer usually means a stale index, not a missing symbol.**
Re-index once, ask again, and only then fall back to grep — saying so. Quietly
reverting to grep for the rest of the session is how a code graph stops paying
for itself.

The index describes the code *as last indexed*: after large edits in the same
session, read the file you just changed rather than asking the graph about it.
