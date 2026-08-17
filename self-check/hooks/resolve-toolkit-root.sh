#!/bin/bash
# Shared by self-check's SessionStart and PostToolUse stubs: resolves an
# ai-dev-toolkit checkout (env override, or an auto-cloned/pulled local
# cache) so hook logic can `exec` straight from it and pick up fixes on
# the next `git pull` without requiring every consumer to re-sync the
# stub. Meant to be `source`d, not executed directly.
set -u

DEFAULT_REMOTE="https://github.com/thomasdevaux/ai-dev-toolkit.git"
REMOTE="${AI_DEV_TOOLKIT_REMOTE:-$DEFAULT_REMOTE}"
CACHE_DIR="$HOME/.cache/ai-dev-toolkit"
PULL_INTERVAL_SECONDS=3600
# Both git calls below run inside a SessionStart hook, so an unbounded one
# holds the session open. Two independent ways that happens: git blocking on
# a credential prompt nothing can answer (no TTY, but the helper can still
# pop a GUI dialog), and a proxy/DNS stall that git's own timeouts don't
# cover. GIT_TERMINAL_PROMPT/GIT_ASKPASS close the first, `timeout` the
# second. A failure here is never fatal — the caller reports "could not
# resolve a checkout" and the session proceeds.
GIT_TIMEOUT_SECONDS=20
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=echo

resolve_toolkit_root() {
    if [ -n "${AI_DEV_TOOLKIT_ROOT:-}" ]; then
        printf '%s\n' "$AI_DEV_TOOLKIT_ROOT"
        return 0
    fi

    # The current project IS a toolkit checkout: use it directly instead of
    # the separately-cached clone, or local edits here would never take
    # effect until pushed and re-pulled into the cache. Recognized by the
    # same two-file fingerprint no consumer project has.
    # Checked against both $CLAUDE_PROJECT_DIR and $PWD — PostToolUse hooks
    # aren't guaranteed to inherit the former, but do run with the project
    # directory as their working directory.
    for _candidate in "${CLAUDE_PROJECT_DIR:-}" "${PWD:-}"; do
        if [ -n "$_candidate" ] \
            && [ -f "$_candidate/sync-manifest.yaml" ] \
            && [ -f "$_candidate/tools/sync/manifest.py" ]; then
            printf '%s\n' "$_candidate"
            return 0
        fi
    done

    if [ ! -d "$CACHE_DIR/.git" ]; then
        if ! timeout "$GIT_TIMEOUT_SECONDS" git clone --quiet "$REMOTE" "$CACHE_DIR" >/dev/null 2>&1; then
            # A timed-out clone can leave a partial directory behind; drop it
            # so the next session retries cleanly instead of finding a
            # .git-less husk it would then treat as an unusable cache.
            [ -d "$CACHE_DIR/.git" ] || rm -rf "$CACHE_DIR"
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
    case "$last" in ''|*[!0-9]*) last=0 ;; esac
    if [ "$((now - last))" -ge "$PULL_INTERVAL_SECONDS" ]; then
        timeout "$GIT_TIMEOUT_SECONDS" git -C "$CACHE_DIR" pull --ff-only --quiet >/dev/null 2>&1
        # Stamped whether or not the pull succeeded: an offline machine would
        # otherwise pay the full timeout on every single session instead of
        # once an hour, and the cached checkout is perfectly usable meanwhile.
        printf '%s\n' "$now" > "$stamp_file"
    fi

    printf '%s\n' "$CACHE_DIR"
    return 0
}
