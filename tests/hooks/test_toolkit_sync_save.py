"""Tests for tools/hooks/toolkit-sync-save.py.

The only part of self-check that mutates a filesystem, so what matters here
is the gate: which payloads reach `tools.sync sync` at all, and what the hook
tells the agent afterwards. Driven as a subprocess — stdin-JSON in, sync
invocation out, is the contract the PostToolUse hook relies on.

`tools.sync` itself is never really run: a stub module on PYTHONPATH records
the argv it was called with, which is exactly the assertion each test wants
and keeps the tests from writing to a real .claude/.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "tools" / "hooks" / "toolkit-sync-save.py"

STUB = '''\
import json, os, sys
calls = []
log = os.environ["SYNC_CALL_LOG"]
if os.path.exists(log):
    calls = json.load(open(log))
calls.append(sys.argv[1:])
json.dump(calls, open(log, "w"))
raise SystemExit(int(os.environ.get("SYNC_EXIT_CODE", "0")))
'''


@pytest.fixture
def fake_toolkit(tmp_path):
    """A directory that looks enough like a checkout for `python -m tools.sync`
    to resolve to the stub above instead of the real package."""
    root = tmp_path / "toolkit"
    (root / "tools" / "sync").mkdir(parents=True)
    (root / "tools" / "__init__.py").write_text("")
    (root / "tools" / "sync" / "__init__.py").write_text("")
    (root / "tools" / "sync" / "__main__.py").write_text(STUB)
    return root


def run(payload: dict, toolkit_root: Path, project_dir: str, log: Path, exit_code: int = 0):
    return subprocess.run(
        [sys.executable, str(HELPER), str(toolkit_root), project_dir],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env={
            **_clean_env(),
            "SYNC_CALL_LOG": str(log),
            "SYNC_EXIT_CODE": str(exit_code),
            "PYTHONPATH": str(toolkit_root),
        },
    )


def _clean_env():
    import os

    return {k: v for k, v in os.environ.items() if k not in ("SYNC_CALL_LOG", "SYNC_EXIT_CODE", "PYTHONPATH")}


def calls(log: Path) -> list[list[str]]:
    return json.loads(log.read_text()) if log.exists() else []


SYNC_OPTIONS = ["Sync now", "Show details first", "Not now"]


def ask(
    question: str,
    answer: str,
    options: list[str] | None = None,
    tool_name: str = "AskUserQuestion",
) -> dict:
    """Shaped like a real PostToolUse payload: `answers` is keyed by question
    text and sits beside the `questions` the agent actually offered."""
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": tool_name,
        "tool_input": {
            "questions": [
                {
                    "question": question,
                    "options": [{"label": label} for label in (SYNC_OPTIONS if options is None else options)],
                }
            ],
            "answers": {question: answer},
        },
    }


ENGLISH = "Sync the toolkit now?"
FRENCH = "Synchroniser le toolkit maintenant ?"


def test_sync_now_syncs_both_scopes(tmp_path, fake_toolkit):
    log = tmp_path / "calls.json"
    result = run(ask(ENGLISH, "Sync now"), fake_toolkit, str(tmp_path / "proj"), log)
    recorded = calls(log)
    assert len(recorded) == 2, recorded
    assert "--user" not in recorded[0]
    assert "--user" in recorded[1]
    assert "successfully" in result.stdout


def test_question_wording_is_irrelevant(tmp_path, fake_toolkit):
    """The regression: the agent asks in the user's language, so keying on an
    English question text meant the sync silently never fired outside English.
    Same defect style-prompt-save.py already hit."""
    log = tmp_path / "calls.json"
    run(ask(FRENCH, "Sync now"), fake_toolkit, str(tmp_path / "proj"), log)
    assert len(calls(log)) == 2


def test_not_now_syncs_nothing(tmp_path, fake_toolkit):
    log = tmp_path / "calls.json"
    result = run(ask(ENGLISH, "Not now"), fake_toolkit, str(tmp_path / "proj"), log)
    assert calls(log) == []
    assert result.stdout == ""


def test_show_details_first_syncs_nothing(tmp_path, fake_toolkit):
    """The middle option must not be a sync: it exists so the user can read the
    report before deciding, and the agent asks again afterwards."""
    log = tmp_path / "calls.json"
    run(ask(ENGLISH, "Show details first"), fake_toolkit, str(tmp_path / "proj"), log)
    assert calls(log) == []


def test_sync_now_without_the_option_set_syncs_nothing(tmp_path, fake_toolkit):
    """Why this hook can't just match the answer the way style-prompt-save.py
    does: that one persists a keyword, this one mutates a filesystem. A
    'Sync now' answered to some unrelated question must not do that."""
    log = tmp_path / "calls.json"
    run(
        ask("Sync the database now?", "Sync now", options=["Sync now", "Later"]),
        fake_toolkit,
        str(tmp_path / "proj"),
        log,
    )
    assert calls(log) == []


def test_answer_cannot_borrow_another_questions_options(tmp_path, fake_toolkit):
    """One AskUserQuestion call can carry several questions. The option set has
    to be the one offered alongside the answer, not merely present somewhere."""
    log = tmp_path / "calls.json"
    payload = ask(ENGLISH, "Not now")
    payload["tool_input"]["questions"].append(
        {"question": "Sync the database now?", "options": [{"label": "Sync now"}, {"label": "Later"}]}
    )
    payload["tool_input"]["answers"]["Sync the database now?"] = "Sync now"
    run(payload, fake_toolkit, str(tmp_path / "proj"), log)
    assert calls(log) == []


def test_other_tool_syncs_nothing(tmp_path, fake_toolkit):
    log = tmp_path / "calls.json"
    run(ask(ENGLISH, "Sync now", tool_name="Bash"), fake_toolkit, str(tmp_path / "proj"), log)
    assert calls(log) == []


def test_missing_project_dir_still_syncs_user_scope(tmp_path, fake_toolkit):
    """A session with no project dir is still a machine with a ~/.claude to
    keep current; only the project-scope half is skipped."""
    log = tmp_path / "calls.json"
    run(ask(ENGLISH, "Sync now"), fake_toolkit, "", log)
    recorded = calls(log)
    assert len(recorded) == 1
    assert "--user" in recorded[0]


def test_failure_is_reported_and_not_swallowed(tmp_path, fake_toolkit):
    """The regression this guards: check=False meant a failed sync exited 0
    with no output, and the agent announced a success that never happened."""
    log = tmp_path / "calls.json"
    result = run(ask(ENGLISH, "Sync now"), fake_toolkit, str(tmp_path / "proj"), log, exit_code=3)
    assert "FAILED" in result.stdout
    assert "do not report the sync as done" in result.stdout


def test_sync_runs_with_utf8_io_encoding(tmp_path, fake_toolkit):
    """A rule containing an em dash used to abort the sync on Windows (cp1252
    stdout), which check=False then swallowed."""
    stub = fake_toolkit / "tools" / "sync" / "__main__.py"
    stub.write_text(
        'import json, os, sys\n'
        'json.dump([os.environ.get("PYTHONIOENCODING")], open(os.environ["SYNC_CALL_LOG"], "w"))\n'
    )
    log = tmp_path / "calls.json"
    run(ask(ENGLISH, "Sync now"), fake_toolkit, str(tmp_path / "proj"), log)
    assert json.loads(log.read_text()) == ["utf-8"]
