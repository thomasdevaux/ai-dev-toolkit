#!/bin/bash
# SessionStart hook: resolves an ai-dev-toolkit checkout and delegates to
# that checkout's own tools/hooks/toolkit-drift-check-impl.sh. This stub is
# deployed/synced into a project or ~/.claude/ and should rarely need to
# change — all the actual status/reporting logic lives in the impl script,
# which always runs from the freshly resolved checkout, so behavior fixes
# there take effect on the next `git pull` (throttled to once an hour)
# without requiring a manual re-sync of this stub. Read-only and never
# blocks session start: any resolution failure is caught, a warning is
# printed instead, and the script always exits 0.
set -u

source "$(dirname "${BASH_SOURCE[0]}")/resolve-toolkit-root.sh"

# Both the project-scope and user-scope copy of this stub fire in the same
# session whenever both are installed; the project-scope one already reports
# on both scopes in a single process (see build_hook_report), so running the
# user-scope copy too would just repeat the exact same git-resolve, manifest
# parse and file hashing a second time. See is_redundant_user_scope_copy in
# resolve-toolkit-root.sh.
is_redundant_user_scope_copy "${BASH_SOURCE[0]}" && exit 0

TOOLKIT_ROOT="$(resolve_toolkit_root)"
IMPL="$TOOLKIT_ROOT/tools/hooks/toolkit-drift-check-impl.sh"
if [ -z "$TOOLKIT_ROOT" ] || [ ! -f "$IMPL" ]; then
    echo "toolkit-drift-check: could not resolve an ai-dev-toolkit checkout (tried '$TOOLKIT_ROOT'); skipping drift check this session."
    exit 0
fi

# ${CLAUDE_PROJECT_DIR:-$PWD}, not $CLAUDE_PROJECT_DIR: `set -u` turns a
# harness that didn't export it into a hard error at session start, and the
# working directory is the right answer in that case anyway.
exec bash "$IMPL" "$TOOLKIT_ROOT" "${CLAUDE_PROJECT_DIR:-$PWD}"
