"""PostToolUse hook helper for style-save.sh: reads the `Skill` tool's
call JSON from stdin and, when it's a caveman invocation, persists the
chosen intensity to the given state file so the statusline reflects the
currently active style — without any session-start question involved.

Keyed on the Skill tool's own structured `tool_input` (skill name + args),
not on freeform text, so there's no language- or wording-dependent parsing
to get wrong: the skill is invoked in the same shape regardless of how the
user phrased the request or what language the session is in.
"""
import json
import sys

VALID_LEVELS = {"lite", "full", "ultra", "wenyan-lite", "wenyan-full", "wenyan-ultra"}


def main() -> None:
    state_file = sys.argv[1]
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Skill":
        return
    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict) or tool_input.get("skill") != "caveman":
        return

    args = tool_input.get("args")
    args = args.strip().lower() if isinstance(args, str) else ""

    if args in VALID_LEVELS:
        style = args
    elif args in ("", "on"):
        # Bare invocation ("use caveman", "/caveman" with no level) — the
        # skill's own stated default.
        style = "full"
    elif args == "off":
        style = "normal"
    else:
        # Unrecognized args: leave existing state untouched rather than guess.
        return

    with open(state_file, "w", encoding="utf-8") as f:
        f.write(style)


if __name__ == "__main__":
    main()
