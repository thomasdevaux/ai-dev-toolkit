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
    # effect until pushed and re-pulled into the cache. Same two-file
    # fingerprint toolkit-drift-check-impl.sh uses to recognize this case.
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

# self-check's SessionStart and PostToolUse stubs are each deployed twice —
# once at project scope (.claude/hooks/), once at user scope (~/.claude/hooks/)
# — but their impl scripts already do combined project+user work in one call
# (build_hook_report merges both scopes into one report; toolkit-sync-save.py
# syncs both scopes from a single invocation whenever a project dir is known).
# When both copies are installed, Claude Code fires both hook registrations in
# the same session, so the user-scope copy would otherwise repeat work the
# project-scope copy already did. Skip it there: true when this script is the
# ~/.claude/hooks copy AND a same-named project-scope copy also exists.
# Compared by basename, not full path — the two copies are byte-identical
# files landing in two different targets, so the pairing is exact.
is_redundant_user_scope_copy() {
    local self_dir script_name
    self_dir="$(cd "$(dirname "$1")" && pwd)"
    script_name="$(basename "$1")"
    [ "$self_dir" = "$HOME/.claude/hooks" ] || return 1
    [ -n "${CLAUDE_PROJECT_DIR:-}" ] || return 1
    [ -f "$CLAUDE_PROJECT_DIR/.claude/hooks/$script_name" ]
}
