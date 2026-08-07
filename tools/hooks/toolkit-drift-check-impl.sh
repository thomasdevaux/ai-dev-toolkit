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

# Which checkout got resolved is diagnostic, not information: printed on any
# non-empty report, it reappears every session for as long as one suggested
# block or detected stack stays uninstalled — a permanent line about the
# toolkit's own plumbing, attached to something that isn't a task. Keep it for
# the cases where the user may actually have to act on the wrong checkout
# being picked, i.e. when there is real drift or a missing baseline entry.
if printf '%s' "$STATUS_OUTPUT" | grep -qE '(not yet synced|drift:)'; then
    echo "toolkit-drift-check: using toolkit checkout at $TOOLKIT_ROOT"
fi

# No `choice-group:project-type` entry in .toolkit-sync-state means no
# profile has been picked for this project yet — the trigger the
# project-type-profile rule used to carry as static text, computed here
# instead since it's already known at this point.
if printf '%s' "$STATUS_OUTPUT" | grep -q '\[choice-group:project-type\]'; then
    echo "ACTION: no project-type profile is registered for this project yet. Before non-trivial work, ask the user which one applies (project-type-none, project-type-app, or project-type-embedded-fccu — see common/rules/project-type-profile.md and docs/maintaining.md for what each implies). Don't guess or silently default."
fi

# The ACTION line only when something actually needs syncing. A suggested
# block or a detected stack is an offer, not a task — pressing the agent to
# open every session with it is how the whole report gets tuned out.
if printf '%s' "$STATUS_OUTPUT" | grep -qE '(not yet synced|drift:)'; then
    # The actual `tools.sync sync` invocation runs as hook automation (see
    # self-check/rules/toolkit-sync-manual.md and toolkit-sync-save.py) once
    # the question below is answered "Sync now" — that hook re-resolves
    # toolkit_root/project_dir itself, so nothing needs handing off here.
    echo "ACTION: this project has pending toolkit onboarding or drift (see below). At the start of your very first reply this session, before addressing anything else they said, tell the user about it and ask them via the AskUserQuestion tool, offering exactly these 3 options, labelled verbatim: \"Sync now\", \"Show details first\", \"Not now\". Word the question itself as you like, in the user's language — the option labels are what matters. If they pick \"Show details first\", show them the report below, then ask again in plain text whether to sync. Do not run the sync yourself in any case — a PostToolUse hook applies it automatically once they answer \"Sync now\"."
fi
printf '%s\n' "$STATUS_OUTPUT"
exit 0
