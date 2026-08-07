#!/bin/bash
# Actual toolkit-sync-save logic, deliberately NOT under any manifest
# `source:` path — it's never synced/deployed into a consumer project.
# The deployed stub (self-check/hooks/toolkit-sync-save.sh) execs this
# script from the freshly resolved/pulled toolkit checkout every time.
# Thin wrapper: the real answer-extraction and sync invocation live in
# toolkit-sync-save.py (bash has no reliable built-in JSON support).
# CLAUDE_PROJECT_DIR is whatever project the current session is in (set by
# Claude Code itself for every hook invocation) — passed through as-is so
# the same PostToolUse hook resolves the right target whether it's firing
# for the SessionStart-detected drift or a manually-typed sync request.
set -u

TOOLKIT_ROOT="$1"
python "$TOOLKIT_ROOT/tools/hooks/toolkit-sync-save.py" "$TOOLKIT_ROOT" "${CLAUDE_PROJECT_DIR:-}"
