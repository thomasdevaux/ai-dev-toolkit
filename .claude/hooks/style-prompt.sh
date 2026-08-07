#!/bin/bash
# SessionStart hook: every session, tells the agent to ask the user which
# communication style they want (normal / caveman lite / full / ultra),
# with the last-used value from a prior session offered as a shortcut on
# top of the four fixed choices. State is global (~/.ai-dev-toolkit/style-last)
# since communication style is a personal habit, not a project setting.
#
# Persisting the answer is NOT done by having the agent issue a Bash/Write
# tool call (three attempts at that all hit permission friction: Write
# ignores Edit-only path rules, ~/.claude paths are hardcoded-sensitive,
# and any Bash write outside the project directory hits a per-workspace
# trust gate that no settings_patch rule can pre-approve). Instead a
# PostToolUse hook (style-prompt-save.sh, matched to AskUserQuestion) does
# the write itself as hook automation, which isn't subject to the
# interactive tool-permission system at all.
set -u

STATE_DIR="$HOME/.ai-dev-toolkit"
STATE_FILE="$STATE_DIR/style-last"
mkdir -p "$STATE_DIR"
LAST="normal"
if [ -f "$STATE_FILE" ]; then
    LAST="$(cat "$STATE_FILE")"
fi

# AskUserQuestion caps at 4 options, so the last-used value is promoted to
# position 1 rather than added as a 5th slot — the other 3 keep their fixed
# relative order with the promoted one removed. `full` sits ahead of `lite`
# because it is the intensity the skill itself defaults to, and the one the
# measured compression figures describe; `lite` barely compresses at all.
# The order is stated once here and interpolated into the prompt below —
# spelling it out a second time in the message is how the two drift apart.
FIXED="normal full lite ultra"
ORDER="$LAST"
for s in $FIXED; do
    if [ "$s" != "$LAST" ]; then
        ORDER="$ORDER $s"
    fi
done

label_for() {
    case "$1" in
        normal) echo "Normal (off)" ;;
        lite) echo "Caveman lite" ;;
        full) echo "Caveman full" ;;
        ultra) echo "Caveman ultra" ;;
    esac
}

OPTIONS_DESC=""
i=0
for s in $ORDER; do
    i=$((i + 1))
    LABEL="$(label_for "$s")"
    if [ "$s" = "$LAST" ]; then
        LABEL="$LABEL (last used)"
    fi
    OPTIONS_DESC="$OPTIONS_DESC $i) \"$LABEL\","
done

# No persistence instruction here anymore — the PostToolUse hook captures
# the answer on its own once AskUserQuestion returns. See the file header.
FIXED_DESC="$(echo "$FIXED" | tr ' ' ',' | sed 's/,/, /g')"
echo "ACTION: before addressing anything else the user said this session, ask them (via the AskUserQuestion tool) which communication style they want for this session. Offer exactly these 4 options, in this order:$OPTIONS_DESC — i.e. the previous session's choice ($LAST) comes first and its label carries a '(last used)' marker, then the remaining 3 in their usual fixed order ($FIXED_DESC) with the promoted one skipped. If they pick a caveman option, load the caveman skill at that intensity for the rest of the session. Ask this first, then proceed with whatever they asked."
