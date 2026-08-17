---
description: List optional toolkit blocks (suggested tier, detected tech stacks) not yet synced into this project
allowed-tools: Bash
model: haiku
---

Discover what's available but not installed. `$CLAUDE_PROJECT_DIR` is only set
by the harness for actual hook executions, not for a plain `Bash` call, so
export it yourself first, then resolve the toolkit checkout and hand off to
`toolkit-status` — the same script a plain terminal (no Claude Code) uses to
check status. The project's own copy of the resolver hook is the first
choice, but a never-onboarded project won't have one, so fall back to the
user-scope copy:

```
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
if [ -f "$CLAUDE_PROJECT_DIR/.claude/hooks/resolve-toolkit-root.sh" ]; then
    source "$CLAUDE_PROJECT_DIR/.claude/hooks/resolve-toolkit-root.sh"
elif [ -f "$HOME/.claude/hooks/resolve-toolkit-root.sh" ]; then
    source "$HOME/.claude/hooks/resolve-toolkit-root.sh"
else
    echo "toolkit not onboarded at either scope" >&2
    exit 1
fi
TOOLKIT_ROOT="$(resolve_toolkit_root)"
"$TOOLKIT_ROOT/bin/toolkit-status" --project-dir "$CLAUDE_PROJECT_DIR"
```

From the output, keep only the "detected stack(s)" and "available, not
installed" sections — ignore the up-to-date roll call, that's not what this
command is for. Present each entry with its one-line summary.

If the user wants one synced, run it yourself — see the
`toolkit-sync-auto-apply` rule for why this command applies directly instead
of printing the command for the user to paste. The user asking for it *is*
the deliberate choice opt-in blocks need; a second copy-paste step through
`!` wouldn't add review, just friction. Re-run the same resolution snippet
first (a fresh `Bash` call doesn't inherit `TOOLKIT_ROOT` from the status
call above), then hand off to the `bin/toolkit-sync` wrapper, not
`python -m tools.sync` directly, so it works regardless of your own cwd (it
already defaults `--project-dir` to it), and always `--yes` — never
`--yes-except-user-tools`, which would block on a prompt this `Bash` call
has no stdin to answer:

```
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
if [ -f "$CLAUDE_PROJECT_DIR/.claude/hooks/resolve-toolkit-root.sh" ]; then
    source "$CLAUDE_PROJECT_DIR/.claude/hooks/resolve-toolkit-root.sh"
elif [ -f "$HOME/.claude/hooks/resolve-toolkit-root.sh" ]; then
    source "$HOME/.claude/hooks/resolve-toolkit-root.sh"
else
    echo "toolkit not onboarded at either scope" >&2
    exit 1
fi
TOOLKIT_ROOT="$(resolve_toolkit_root)"
"$TOOLKIT_ROOT/bin/toolkit-sync" sync <entry-id> --yes
```

Report back what changed (the `Syncing: + ...` lines it prints).

If the user says they don't want one of the listed entries, record it so the
session-start report stops offering it — otherwise it reappears every session
forever, and the whole report gets tuned out. It only writes a reporting
filter, and the entry stays syncable by id at any time (`--undo` to offer it
again). Same resolution snippet, same reason:

```
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
if [ -f "$CLAUDE_PROJECT_DIR/.claude/hooks/resolve-toolkit-root.sh" ]; then
    source "$CLAUDE_PROJECT_DIR/.claude/hooks/resolve-toolkit-root.sh"
elif [ -f "$HOME/.claude/hooks/resolve-toolkit-root.sh" ]; then
    source "$HOME/.claude/hooks/resolve-toolkit-root.sh"
else
    echo "toolkit not onboarded at either scope" >&2
    exit 1
fi
TOOLKIT_ROOT="$(resolve_toolkit_root)"
"$TOOLKIT_ROOT/bin/toolkit-sync" dismiss <entry-id>
```

If nothing is listed, tell the user there's nothing optional pending — and
mention `--undo` if they're wondering where a block they declined went.
