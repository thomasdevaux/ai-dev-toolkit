#!/bin/bash
# SessionStart hook: resolves an ai-dev-toolkit checkout (env override, or
# an auto-cloned/pulled local cache) and delegates to that checkout's own
# tools/hooks/toolkit-drift-check-impl.sh. This stub is deployed/synced
# into a project or ~/.claude/ and should rarely need to change — all the
# actual status/reporting logic lives in the impl script, which always runs
# from the freshly resolved checkout, so behavior fixes there take effect
# on the next `git pull` (throttled to once an hour) without requiring a
# manual re-sync of this stub. Read-only and never blocks session start:
# any resolution failure is caught, a warning is printed instead, and the
# script always exits 0.
set -u

DEFAULT_REMOTE="https://github.com/thomasdevaux/ai-dev-toolkit.git"
REMOTE="${AI_DEV_TOOLKIT_REMOTE:-$DEFAULT_REMOTE}"
CACHE_DIR="$HOME/.cache/ai-dev-toolkit"
PULL_INTERVAL_SECONDS=3600

resolve_toolkit_root() {
    if [ -n "${AI_DEV_TOOLKIT_ROOT:-}" ]; then
        printf '%s\n' "$AI_DEV_TOOLKIT_ROOT"
        return 0
    fi

    if [ ! -d "$CACHE_DIR/.git" ]; then
        if ! git clone --quiet "$REMOTE" "$CACHE_DIR" >/dev/null 2>&1; then
            return 1
        fi
        date +%s > "$CACHE_DIR/.last-pull"
        printf '%s\n' "$CACHE_DIR"
        return 0
    fi

    local stamp_file="$CACHE_DIR/.last-pull"
    local now last=0
    now="$(date +%s)"
    if [ -f "$stamp_file" ]; then
        last="$(cat "$stamp_file")"
    fi
    if [ "$((now - last))" -ge "$PULL_INTERVAL_SECONDS" ]; then
        git -C "$CACHE_DIR" pull --ff-only --quiet >/dev/null 2>&1
        printf '%s\n' "$now" > "$stamp_file"
    fi

    printf '%s\n' "$CACHE_DIR"
    return 0
}

TOOLKIT_ROOT="$(resolve_toolkit_root)"
IMPL="$TOOLKIT_ROOT/tools/hooks/toolkit-drift-check-impl.sh"
if [ -z "$TOOLKIT_ROOT" ] || [ ! -f "$IMPL" ]; then
    echo "toolkit-drift-check: could not resolve an ai-dev-toolkit checkout (tried '$TOOLKIT_ROOT'); skipping drift check this session."
    exit 0
fi

exec bash "$IMPL" "$TOOLKIT_ROOT" "$CLAUDE_PROJECT_DIR"
