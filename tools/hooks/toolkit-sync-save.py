"""PostToolUse hook helper for toolkit-sync-save-impl.sh: reads
AskUserQuestion's tool-call JSON from stdin and, if it's an answer to the
sync question with "Sync now" chosen, runs `tools.sync sync` directly as
hook automation instead of the agent issuing a Bash call for it. Mirrors
style-prompt-save.py's shape (see common/hooks/), applied to a real
filesystem mutation instead of a one-line state write.

Fires on ANY AskUserQuestion call carrying the sync question's option set —
not just the one the SessionStart drift-check triggers. That's deliberate: a
manually-typed "sync the toolkit" request is meant to go through the same
confirmation (see self-check/rules/toolkit-sync-manual.md), and this hook has
no way to tell the two apart, nor does it need to. project_dir/toolkit_root
are re-resolved here rather than read from a state file written earlier, so
this works identically whichever path asked the question.

Matching deliberately ignores the question *text*: the agent asks in the
user's own language, so keying on an English string meant the sync silently
never fired outside English — the exact regression style-prompt-save.py
already hit (see common/hooks/). But that hook's answer-only fix is too loose
here: it persists a keyword, this one mutates a filesystem, and a bare
"Sync now" answered to some unrelated question must not do that. So the
signature is the whole offered option set — all three labels, which the
contract dictates verbatim — on the very question that was answered
"Sync now". Wording free, options fixed.
"""
import json
import os
import subprocess
import sys

TRIGGER_LABEL = "Sync now"
REQUIRED_LABELS = {"Sync now", "Show details first", "Not now"}


def _wants_sync(tool_input: dict) -> bool:
    answers = tool_input.get("answers")
    questions = tool_input.get("questions")
    if not isinstance(answers, dict) or not isinstance(questions, list):
        return False
    for question in questions:
        if not isinstance(question, dict):
            continue
        # answers is keyed by question text, so this pairs an answer with the
        # options that were actually offered alongside it — a "Sync now" from
        # a different question in the same call can't borrow this one's set.
        if answers.get(question.get("question")) != TRIGGER_LABEL:
            continue
        options = question.get("options")
        if not isinstance(options, list):
            continue
        labels = {o.get("label") for o in options if isinstance(o, dict)}
        if REQUIRED_LABELS <= labels:
            return True
    return False


def main() -> None:
    toolkit_root = sys.argv[1]
    project_dir = sys.argv[2] if len(sys.argv) > 2 else ""
    data = json.load(sys.stdin)
    should_sync = (
        data.get("tool_name") == "AskUserQuestion"
        and _wants_sync(data.get("tool_input") or {})
    )

    if not should_sync:
        return

    failures = []
    if project_dir:
        if _run_sync(toolkit_root, toolkit_root, project_dir, user=False) != 0:
            failures.append("project")
    if _run_sync(toolkit_root, toolkit_root, project_dir or ".", user=True) != 0:
        failures.append("user")

    # The agent has no other way to learn what this hook did: it was told not
    # to run the sync itself, so without a line here it can only assume the
    # answer it collected was honoured — and announce a success that never
    # happened. Both outcomes are reported, and the failure case says outright
    # not to claim otherwise.
    if failures:
        print(
            f"toolkit-sync: FAILED for {' and '.join(failures)} scope. "
            "The toolkit was NOT synced. Tell the user it failed and that the "
            "drift is still pending; do not report the sync as done."
        )
    else:
        print("toolkit-sync: applied successfully.")


def _run_sync(cwd: str, toolkit_root: str, project_dir: str, user: bool) -> int:
    args = [
        sys.executable, "-m", "tools.sync", "sync",
        "--toolkit-root", toolkit_root,
        "--project-dir", project_dir,
        "--yes",
    ]
    if user:
        args.append("--user")
    # A hook subprocess on Windows inherits cp1252 for stdout, and the diff
    # tools.sync prints carries whatever the rules contain — an arrow, an
    # em dash. That raises UnicodeEncodeError inside render_file_changes,
    # which aborts the sync for that entry; check=False then swallows it and
    # the sync silently does nothing. Forcing UTF-8 is what keeps a rule's
    # punctuation from deciding whether the sync runs.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(args, cwd=cwd, check=False, env=env).returncode


if __name__ == "__main__":
    main()
