"""Tests for common/hooks/style-save.py.

The helper is driven as a subprocess rather than imported: its filename has a
hyphen, and stdin-JSON in / state-file out is the actual contract the
PostToolUse hook (matched on the `Skill` tool) relies on.
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
    / "style-save.py"
)


def run(payload: dict, state_file: Path) -> None:
    subprocess.run(
        [sys.executable, str(HELPER), str(state_file)],
        input=json.dumps(payload),
        text=True,
        check=True,
    )


def skill_call(skill: str, args: str | None = None) -> dict:
    tool_input = {"skill": skill}
    if args is not None:
        tool_input["args"] = args
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Skill",
        "tool_input": tool_input,
    }


@pytest.mark.parametrize(
    "args,keyword",
    [
        ("lite", "lite"),
        ("full", "full"),
        ("ultra", "ultra"),
        ("wenyan-lite", "wenyan-lite"),
        ("wenyan-full", "wenyan-full"),
        ("wenyan-ultra", "wenyan-ultra"),
    ],
)
def test_each_valid_level_is_written_verbatim(tmp_path, args, keyword):
    state = tmp_path / "active-style"
    run(skill_call("caveman", args), state)
    assert state.read_text(encoding="utf-8") == keyword


def test_no_args_defaults_to_full(tmp_path):
    """Bare invocation ('use caveman', or /caveman with no level) —
    the skill's own stated default."""
    state = tmp_path / "active-style"
    run(skill_call("caveman"), state)
    assert state.read_text(encoding="utf-8") == "full"


def test_off_maps_to_normal(tmp_path):
    state = tmp_path / "active-style"
    state.write_text("full", encoding="utf-8")
    run(skill_call("caveman", "off"), state)
    assert state.read_text(encoding="utf-8") == "normal"


def test_non_caveman_skill_leaves_state_untouched(tmp_path):
    state = tmp_path / "active-style"
    state.write_text("ultra", encoding="utf-8")
    run(skill_call("commit-message-format"), state)
    assert state.read_text(encoding="utf-8") == "ultra"


def test_other_tools_are_ignored(tmp_path):
    state = tmp_path / "active-style"
    payload = skill_call("caveman", "full")
    payload["tool_name"] = "Bash"
    run(payload, state)
    assert not state.exists()


def test_unrecognized_args_leaves_state_untouched(tmp_path):
    state = tmp_path / "active-style"
    state.write_text("lite", encoding="utf-8")
    run(skill_call("caveman", "something the user typed"), state)
    assert state.read_text(encoding="utf-8") == "lite"
