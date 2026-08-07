"""PostToolUse hook helper for style-prompt-save.sh: reads AskUserQuestion's
tool-call JSON from stdin and persists the chosen communication style
keyword to the given state file path.

Matching is done on the *answer*, not on the question text. style-prompt.sh
dictates the four option labels verbatim but leaves the wording of the
question to the agent, which asks it in the user's own language — keying on
the question text meant the choice was silently never persisted outside
English. So only an answer whose value is one of the four known style labels
is acted on, and only when exactly one is: any other AskUserQuestion call in
the session leaves the state file untouched.
"""
import json
import sys

LABEL_TO_KEYWORD = {
    "Normal (off)": "normal",
    "Caveman lite": "lite",
    "Caveman full": "full",
    "Caveman ultra": "ultra",
}


def main() -> None:
    state_file = sys.argv[1]
    data = json.load(sys.stdin)
    if data.get("tool_name") != "AskUserQuestion":
        return
    answers = data.get("tool_input", {}).get("answers", {})
    if not isinstance(answers, dict):
        return
    keywords = set()
    for value in answers.values():
        if not isinstance(value, str):
            continue
        # The agent embeds a "(last used)" marker directly in the option
        # label it offers (see style-prompt.sh); strip it back off first.
        keyword = LABEL_TO_KEYWORD.get(value.replace(" (last used)", ""))
        if keyword is not None:
            keywords.add(keyword)
    # Nothing matched: an unrelated question, or a free-text "Other" answer.
    # More than one matched: ambiguous, so refuse rather than guess.
    if len(keywords) != 1:
        return
    with open(state_file, "w", encoding="utf-8") as f:
        f.write(keywords.pop())


if __name__ == "__main__":
    main()
