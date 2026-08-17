---
description: List optional toolkit blocks (suggested tier, detected tech stacks) not yet synced into this project
allowed-tools: Bash
model: haiku
---

Discover what's available but not installed. `$CLAUDE_PROJECT_DIR` is only set
by the harness for actual hook executions, not for a plain `Bash` call, so
export it yourself first, then resolve the toolkit checkout and hand off to
`toolkit-status` — the same script a plain terminal (no Claude Code) uses to
check status:

```
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
source "$CLAUDE_PROJECT_DIR/.claude/hooks/resolve-toolkit-root.sh"
TOOLKIT_ROOT="$(resolve_toolkit_root)"
"$TOOLKIT_ROOT/toolkit-status" --project-dir "$CLAUDE_PROJECT_DIR"
```

From the output, keep only the "detected stack(s)" and "available, not
installed" sections — ignore the up-to-date roll call, that's not what this
command is for. Present each entry with its one-line summary.

If the user wants one synced, give them the exact command to run themselves
via the `!` prefix:

```
python -m tools.sync sync --toolkit-root "$TOOLKIT_ROOT" --project-dir "$CLAUDE_PROJECT_DIR" <entry-id>
```

Do not run it yourself. Opt-in blocks are a deliberate, reviewed choice —
same reasoning as the rest of this toolkit's sync-and-commit model, just not
covered by `/toolkit-sync` (that one only ever reports on the baseline tier).

If the user says they don't want one of the listed entries, record it so the
session-start report stops offering it — otherwise it reappears every session
forever, and the whole report gets tuned out. This one you do run yourself;
it only writes a reporting filter, and the entry stays syncable by id at any
time (`--undo` to offer it again):

```
python -m tools.sync dismiss <entry-id> --toolkit-root "$TOOLKIT_ROOT" --project-dir "$CLAUDE_PROJECT_DIR"
```

If nothing is listed, tell the user there's nothing optional pending — and
mention `--undo` if they're wondering where a block they declined went.
