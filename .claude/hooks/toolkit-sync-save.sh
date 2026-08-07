#!/bin/bash
# PostToolUse hook (matcher: AskUserQuestion): resolves an ai-dev-toolkit
# checkout the same way toolkit-drift-check.sh does, and delegates to that
# checkout's own tools/hooks/toolkit-sync-save-impl.sh — the actual answer
# extraction and sync invocation. This stub is deployed/synced and should
# rarely need to change; behavior fixes to the impl land on the next
# `git pull`. Silent on resolution failure: unlike the SessionStart stub,
# there's no session-opening moment to attach a warning to, and staying
# silent matches every other PostToolUse hook's failure mode.
set -u

# Cheap gate FIRST, before resolving anything or even sourcing. This hook
# fires on *every* AskUserQuestion call in every session, and resolving a
# checkout can mean a `git clone`/`git pull` — a network round-trip hung off
# an unrelated question. A substring test on the raw payload rejects the
# common case for the price of one `case`. Matched on the option label rather
# than the question text, which the agent writes in the user's own language
# (see toolkit-sync-save.py); this is only a cheap pre-filter, the real
# option-set check happens there. stdin is consumed here and replayed below.
PAYLOAD="$(cat)"
case "$PAYLOAD" in
    *'Sync now'*) ;;
    *) exit 0 ;;
esac

source "$(dirname "${BASH_SOURCE[0]}")/resolve-toolkit-root.sh"

# Same duplication as toolkit-drift-check.sh: toolkit-sync-save.py already
# applies both project-scope and user-scope entries from a single invocation
# whenever a project dir is known, so the user-scope copy of this stub firing
# too would re-run `tools.sync sync` for both scopes a second time.
is_redundant_user_scope_copy "${BASH_SOURCE[0]}" && exit 0

TOOLKIT_ROOT="$(resolve_toolkit_root)"
IMPL="$TOOLKIT_ROOT/tools/hooks/toolkit-sync-save-impl.sh"
if [ -z "$TOOLKIT_ROOT" ] || [ ! -f "$IMPL" ]; then
    exit 0
fi

exec bash "$IMPL" "$TOOLKIT_ROOT" <<<"$PAYLOAD"
