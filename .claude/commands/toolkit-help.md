---
description: Show the toolkit's daily-practice guide and where the rest of the handbook lives
allowed-tools: Bash
model: haiku
---

First, show this link:

```
https://github.com/thomasdevaux/ai-dev-toolkit/tree/main/handbook
```

Then resolve the checkout (same fallback the other toolkit commands use,
since `$CLAUDE_PROJECT_DIR` is only set by the harness for real hook runs,
not a plain `Bash` call) and hand off to `toolkit-help` — the same script a
plain terminal (no Claude Code) uses to read the handbook. `practices.md`
isn't synced into any project, it only exists in the toolkit's own
checkout/GitHub repo:

```
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
source "$CLAUDE_PROJECT_DIR/.claude/hooks/resolve-toolkit-root.sh"
TOOLKIT_ROOT="$(resolve_toolkit_root)"
"$TOOLKIT_ROOT/toolkit-help"
```

A `Bash` result is only visible to you, not to the user, so something has to
be reproduced in your reply — but not the whole file. Print its **table of
contents**: every heading, each with the one short line it's about. Then ask
which section they want, and reproduce that one **verbatim, in full** — for
the section they actually asked for, the real text matters, not your
paraphrase of it.

The file is the reference; echoing all of it through a reply costs its full
length in output tokens every single time, to tell the user something they
could have read from the link above.

If the command fails (checkout not resolvable), stop after the link instead.
