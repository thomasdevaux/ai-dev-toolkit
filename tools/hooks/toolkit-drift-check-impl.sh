#!/bin/bash
# Actual toolkit-drift-check logic, deliberately NOT under any manifest
# `source:` path — it's never synced/deployed into a consumer project.
# The deployed stub (self-check/hooks/toolkit-drift-check.sh) execs this
# script from the freshly resolved/pulled toolkit checkout every time, so
# behavior changes here take effect via the next `git pull` (throttled to
# once an hour) instead of requiring a manual re-sync of the stub.
set -u

TOOLKIT_ROOT="$1"
PROJECT_DIR="$2"

# A toolkit checkout is not a consumer of its own blocks (see its AGENTS.md,
# "Self-application"), so onboarding it into itself is meaningless — and the
# report would be actively misleading, since the cached checkout this hook
# runs from is usually older than the working copy being edited. Recognized
# by the two files no consumer project has. `tools.sync status` invoked
# explicitly still works here; only the automatic session-start report is off.
if [ -f "$PROJECT_DIR/sync-manifest.yaml" ] && [ -f "$PROJECT_DIR/tools/sync/manifest.py" ]; then
    exit 0
fi

# --for-hook drops the up-to-date roll call and the 'nothing to report' line,
# keeping drift, un-synced entries and the two discovery sections. Empty means
# there is nothing worth saying — and then the hook says nothing at all, not
# even which checkout it resolved.
STATUS_OUTPUT="$(cd "$TOOLKIT_ROOT" && python -m tools.sync status --for-hook --toolkit-root "$TOOLKIT_ROOT" --project-dir "$PROJECT_DIR" 2>/dev/null)"
if [ -z "$STATUS_OUTPUT" ]; then
    exit 0
fi

echo "toolkit-drift-check: using toolkit checkout at $TOOLKIT_ROOT"
# The ACTION line only when something actually needs syncing. A suggested
# block or a detected stack is an offer, not a task — pressing the agent to
# open every session with it is how the whole report gets tuned out.
if printf '%s' "$STATUS_OUTPUT" | grep -qE '(not yet synced|drift:)'; then
    echo "ACTION: this project has pending toolkit onboarding or drift (see below). Tell the user about it at the start of your very first reply this session, before addressing anything else they said, and ask whether to sync now or defer."
fi
printf '%s\n' "$STATUS_OUTPUT"
exit 0
