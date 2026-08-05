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

STATUS_OUTPUT="$(cd "$TOOLKIT_ROOT" && python -m tools.sync status --toolkit-root "$TOOLKIT_ROOT" --project-dir "$PROJECT_DIR" 2>/dev/null)"

# Nothing actionable, nothing printed — not even which checkout was used.
# A hook that speaks every session stops being read by the third one. The
# purely informational parts of the report (suggested blocks, detected
# stacks) stay reachable through `tools.sync status` and `tools.sync detect`,
# which the user runs deliberately.
if ! printf '%s' "$STATUS_OUTPUT" | grep -qE '(not yet synced|drift:)'; then
    exit 0
fi

echo "toolkit-drift-check: using toolkit checkout at $TOOLKIT_ROOT"
echo "ACTION: this project has pending toolkit onboarding or drift (see below). Tell the user about it at the start of your very first reply this session, before addressing anything else they said, and ask whether to sync now or defer."
printf '%s\n' "$STATUS_OUTPUT"
exit 0
