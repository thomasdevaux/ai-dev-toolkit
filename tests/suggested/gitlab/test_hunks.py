"""Unit tests for hunk parsing and position building. No network calls."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "suggested" / "gitlab" / "skills" / "gitlab-common" / "bin"))
import gitlab_tool as gt  # noqa: E402


SIMPLE_DIFF = (
    "@@ -1,3 +1,4 @@\n"
    " line one\n"
    "-line two\n"
    "+line two changed\n"
    "+line new\n"
    " line three\n"
)

MULTI_HUNK_DIFF = (
    "@@ -1,2 +1,2 @@\n"
    "-old a\n"
    "+new a\n"
    " context a\n"
    "@@ -10,2 +10,3 @@\n"
    " context b\n"
    "+added b\n"
    " context c\n"
)

NO_NEWLINE_DIFF = (
    "@@ -1,1 +1,1 @@\n"
    "-old last line\n"
    "\\ No newline at end of file\n"
    "+new last line\n"
    "\\ No newline at end of file\n"
)


class TestComputeHunkMap(unittest.TestCase):
    def test_added_removed_context(self):
        hunk_map = gt.compute_hunk_map(SIMPLE_DIFF)
        kinds = [(r["kind"], r["old_line"], r["new_line"]) for r in hunk_map]
        self.assertEqual(kinds, [
            ("context", 1, 1),
            ("removed", 2, None),
            ("added", None, 2),
            ("added", None, 3),
            ("context", 3, 4),
        ])

    def test_multiple_hunks_resume_counters_from_header(self):
        hunk_map = gt.compute_hunk_map(MULTI_HUNK_DIFF)
        # second hunk header resets counters to 10/10
        second_hunk = hunk_map[3:]
        self.assertEqual(second_hunk[0], {"old_line": 10, "new_line": 10, "kind": "context"})
        self.assertEqual(second_hunk[1], {"old_line": None, "new_line": 11, "kind": "added"})
        self.assertEqual(second_hunk[2], {"old_line": 11, "new_line": 12, "kind": "context"})

    def test_no_newline_marker_does_not_shift_counters(self):
        hunk_map = gt.compute_hunk_map(NO_NEWLINE_DIFF)
        self.assertEqual(hunk_map, [
            {"old_line": 1, "new_line": None, "kind": "removed"},
            {"old_line": None, "new_line": 1, "kind": "added"},
        ])

    def test_empty_diff(self):
        self.assertEqual(gt.compute_hunk_map(""), [])


DIFF_REFS = {"base_sha": "base", "start_sha": "start", "head_sha": "head"}


class TestBuildPosition(unittest.TestCase):
    def setUp(self):
        self.hunk_map = gt.compute_hunk_map(SIMPLE_DIFF)

    def test_added_line_uses_new_line_only(self):
        pos = gt.build_position(self.hunk_map, 3, "new", DIFF_REFS, "f.py", "f.py")
        self.assertEqual(pos["new_line"], 3)
        self.assertNotIn("old_line", pos)

    def test_removed_line_uses_old_line_only(self):
        pos = gt.build_position(self.hunk_map, 2, "old", DIFF_REFS, "f.py", "f.py")
        self.assertEqual(pos["old_line"], 2)
        self.assertNotIn("new_line", pos)

    def test_context_line_uses_both(self):
        pos = gt.build_position(self.hunk_map, 1, "old", DIFF_REFS, "f.py", "f.py")
        self.assertEqual(pos["old_line"], 1)
        self.assertEqual(pos["new_line"], 1)

    def test_line_outside_any_hunk_returns_none(self):
        pos = gt.build_position(self.hunk_map, 999, "new", DIFF_REFS, "f.py", "f.py")
        self.assertIsNone(pos)

    def test_position_carries_diff_refs(self):
        pos = gt.build_position(self.hunk_map, 3, "new", DIFF_REFS, "f.py", "f.py")
        self.assertEqual(pos["base_sha"], "base")
        self.assertEqual(pos["start_sha"], "start")
        self.assertEqual(pos["head_sha"], "head")


if __name__ == "__main__":
    unittest.main()
