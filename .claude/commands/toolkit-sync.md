---
description: Check toolkit onboarding/drift status for this project, and sync it
allowed-tools: Bash
model: haiku
---

`$CLAUDE_PROJECT_DIR` is only set by the harness for actual hook executions,
not for a plain `Bash` call, so export it yourself first, then resolve the
toolkit checkout and hand off to `toolkit-status` — the same script a plain
terminal (no Claude Code) uses to check status, covering both project and
user scope in one run. The project's own copy of the resolver hook is the
first choice, but a never-onboarded project (no `.claude/` at all — the
exact case this command most needs to handle) won't have one, so fall back
to the user-scope copy, which the common block installs everywhere:

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

Otherwise, apply it yourself — see the `toolkit-sync-auto-apply` rule for
why this command runs the sync directly instead of just printing the
command. Re-run the same resolution snippet (a fresh `Bash` call doesn't
inherit `TOOLKIT_ROOT` from the one above) and hand off to `bin/toolkit-sync`,
not `python -m tools.sync` directly: the wrapper `cd`s into the toolkit root
before invoking Python and defaults both `--toolkit-root` and
`--project-dir` to itself, so nothing needs spelling out beyond `--yes`
(never `--yes-except-user-tools` — see the rule for why):

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
"$TOOLKIT_ROOT/bin/toolkit-sync" sync --yes
```

If the drift reported is at user scope (`~/.claude`) instead of (or in
addition to) project scope, run the `--user` variant too:

```
"$TOOLKIT_ROOT/bin/toolkit-sync" sync --user --yes
```

Report back what actually changed — the `Syncing: + ...` feature lines
each run prints, or "nothing to apply" if a scope turned out already
up to date by the time you got here.
