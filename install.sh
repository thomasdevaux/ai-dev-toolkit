#!/usr/bin/env bash
# One-time per-machine bootstrap: clone (or update) ai-dev-toolkit into the
# same cache path the session-start check reuses afterwards (so there's only
# ever one checkout on disk), then sync every user-scope baseline entry into
# ~/.claude/. See README.md for what that installs.
set -euo pipefail

REMOTE="${AI_DEV_TOOLKIT_REMOTE:-https://github.com/thomasdevaux/ai-dev-toolkit.git}"
CACHE_DIR="${AI_DEV_TOOLKIT_ROOT:-$HOME/.cache/ai-dev-toolkit}"

if [ -d "$CACHE_DIR/.git" ]; then
    git -C "$CACHE_DIR" pull --ff-only
else
    git clone "$REMOTE" "$CACHE_DIR"
fi

cd "$CACHE_DIR"
python -m tools.sync sync --user --toolkit-root .
