"""Tests for common/hooks/style-prompt-save.py.

The helper is driven as a subprocess rather than imported: its filename has a
hyphen, and stdin-JSON in / state-file out is the actual contract the
PostToolUse hook relies on.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = (
    Path(__file__).resolve().parents[2]
    / "common"
    / "hooks"
    / "style-prompt-save.py"
)


def run(payload: dict, state_file: Path) -> None:
    subprocess.run(
        [sys.executable, str(HELPER), str(state_file)],
        input=json.dumps(payload),
        text=True,
        check=True,
    )


def ask_user_question(answers: dict) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "AskUserQuestion",
        "tool_input": {"answers": answers},
    }


def test_question_wording_is_irrelevant(tmp_path):
    """The regression: the agent asks in the user's language, so the question
    text cannot be what the answer is looked up by."""
    state = tmp_path / "style-last"
    run(
        ask_user_question(
            {"Quel style de communication pour cette session ?": "Caveman lite"}
        ),
        state,
    )
    assert state.read_text(encoding="utf-8") == "lite"


@pytest.mark.parametrize(
    "label,keyword",
    [
        ("Normal (off)", "normal"),
        ("Caveman lite", "lite"),
        ("Caveman full", "full"),
        ("Caveman ultra", "ultra"),
    ],
)
def test_each_label_maps_to_its_keyword(tmp_path, label, keyword):
    state = tmp_path / "style-last"
    run(ask_user_question({"whatever": label}), state)
    assert state.read_text(encoding="utf-8") == keyword


def test_last_used_marker_is_stripped(tmp_path):
    state = tmp_path / "style-last"
    run(ask_user_question({"whatever": "Caveman full (last used)"}), state)
    assert state.read_text(encoding="utf-8") == "full"


def test_unrelated_question_leaves_state_untouched(tmp_path):
    state = tmp_path / "style-last"
    state.write_text("ultra", encoding="utf-8")
    run(
        ask_user_question({"Which database should we use?": "PostgreSQL"}),
        state,
    )
    assert state.read_text(encoding="utf-8") == "ultra"


def test_free_text_other_answer_leaves_state_untouched(tmp_path):
    state = tmp_path / "style-last"
    state.write_text("lite", encoding="utf-8")
    run(ask_user_question({"whatever": "something the user typed"}), state)
    assert state.read_text(encoding="utf-8") == "lite"


def test_two_style_labels_at_once_is_refused(tmp_path):
    state = tmp_path / "style-last"
    state.write_text("normal", encoding="utf-8")
    run(ask_user_question({"a": "Caveman lite", "b": "Caveman ultra"}), state)
    assert state.read_text(encoding="utf-8") == "normal"


def test_other_tools_are_ignored(tmp_path):
    state = tmp_path / "style-last"
    payload = ask_user_question({"whatever": "Caveman lite"})
    payload["tool_name"] = "Bash"
    run(payload, state)
    assert not state.exists()
