#!/bin/bash
# PostToolUse hook, matched to Skill: persists the active caveman intensity
# to ~/.ai-dev-toolkit/active-style whenever the caveman skill is invoked
# (manually or auto-triggered), so the statusline reflects the current
# style without any session-start question. Delegates the JSON parsing to
# style-save.py since bash has no reliable built-in JSON support.
set -u

STATE_DIR="$HOME/.ai-dev-toolkit"
mkdir -p "$STATE_DIR"

# `python` alone doesn't exist on many Linux/macOS installs, and a hook that
# fails here surfaces nothing to the session — so resolve the interpreter,
# and give up quietly rather than emitting an error if there is none.
PY=$(command -v python3 || command -v python) || exit 0

"$PY" "$(dirname "$0")/style-save.py" "$STATE_DIR/active-style"
