---
description: Force a toolkit onboarding/drift check right now, instead of waiting for session start
allowed-tools: Bash, AskUserQuestion
model: haiku
---

Run the same check the session-start hook runs, on demand. `$CLAUDE_PROJECT_DIR`
is only set by the harness for actual hook executions, not for a plain `Bash`
call, so export it yourself first:

```
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
bash "$CLAUDE_PROJECT_DIR/.claude/hooks/toolkit-drift-check.sh"
bash "$HOME/.claude/hooks/toolkit-drift-check.sh"
```

Run whichever of the two exists. Follow its output exactly as you would at
session start, including any `ACTION:` line — in particular, if it says to
propose a sync, ask via `AskUserQuestion` offering exactly the three options
`Sync now` / `Show details first` / `Not now`, labelled verbatim. The
question's own wording is yours, in the user's language: the hook matches the
option set (see the `toolkit-sync-manual` rule). Never run
`python -m tools.sync sync` yourself — the `PostToolUse` hook applies it
automatically once answered.

If both scripts print nothing, tell the user the toolkit is already up to
date and stop there.
