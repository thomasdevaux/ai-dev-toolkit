---
description: Check toolkit onboarding/drift status for this project, and show the command to sync it yourself
allowed-tools: Bash
model: haiku
---

Report-only: this command never writes anything. `$CLAUDE_PROJECT_DIR` is
only set by the harness for actual hook executions, not for a plain `Bash`
call, so export it yourself first, then resolve the toolkit checkout and
hand off to `toolkit-status` — the same script a plain terminal (no Claude
Code) uses to check status, covering both project and user scope in one run.
The project's own copy of the resolver hook is the first choice, but a
never-onboarded project (no `.claude/` at all — the exact case this command
most needs to handle) won't have one, so fall back to the user-scope copy,
which the common block installs everywhere:

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

Summarize the report for the user: what's up to date, what's missing or
drifted, what's available but not installed. If nothing needs attention at
either scope, say so briefly and stop there.

Otherwise, give the user the exact command to run themselves via the `!`
prefix — never run it yourself. Use the `bin/toolkit-sync` wrapper, not
`python -m tools.sync` directly: the wrapper `cd`s into the toolkit root
before invoking Python, so it works regardless of the user's own cwd, and
it already defaults `--toolkit-root` to itself:

```
"$TOOLKIT_ROOT/bin/toolkit-sync" sync --project-dir "$CLAUDE_PROJECT_DIR"
```

If the drift reported is at user scope (`~/.claude`), give the `--user`
variant instead:

```
"$TOOLKIT_ROOT/bin/toolkit-sync" sync --project-dir "$CLAUDE_PROJECT_DIR" --user
```

See the `toolkit-sync-manual` rule for why this command never applies the
sync on its own.
