"""Unit tests for --dry-run payload shape on write subcommands.

Network calls (`glab_api`, and the read helpers built on it) are monkeypatched
out — these tests assert the exact payload a write subcommand would send,
without ever invoking `glab` or touching the network.
"""

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "suggested" / "gitlab" / "skills" / "gitlab-common" / "bin"))
import gitlab_tool as gt  # noqa: E402


def write_body(text: str) -> str:
    fd, name = tempfile.mkstemp(suffix=".md")
    Path(name).write_text(text, encoding="utf-8")
    return name


def run_dry(func, ns) -> dict:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        func(ns)
    return json.loads(buf.getvalue())


class TestMrNoteCreateDryRun(unittest.TestCase):
    @mock.patch.object(gt, "existing_note_bodies_for_mr", return_value=[])
    def test_dry_run_payload_shape(self, _mock):
        body_file = write_body("General finding text.")
        ns = argparse.Namespace(iid=7, kind="review", body_file=body_file,
                                 expect_head_sha=None, dry_run=True)
        out = run_dry(gt.cmd_mr_note_create, ns)
        self.assertEqual(out["status"], "dry_run")
        self.assertIn("General finding text.", out["payload"]["note"])
        self.assertIn("ai-hash:", out["payload"]["note"])
        self.assertEqual(out["duplicate_found"], False)
        self.assertIn("idempotence_hash", out)

    @mock.patch.object(gt, "existing_note_bodies_for_mr")
    def test_dry_run_detects_duplicate(self, mock_bodies):
        body_file = write_body("Repeated finding.")
        # Precompute the hash the real call would use, and seed it as "already posted".
        _, h = gt.build_marked_body("", "Repeated finding.", "review", "general")
        mock_bodies.return_value = [f"<!-- ai-hash:{h} -->"]
        ns = argparse.Namespace(iid=7, kind="review", body_file=body_file,
                                 expect_head_sha=None, dry_run=True)
        out = run_dry(gt.cmd_mr_note_create, ns)
        self.assertEqual(out["status"], "skipped_duplicate")


class TestMrDiscussionCreateDryRun(unittest.TestCase):
    @mock.patch.object(gt, "existing_note_bodies_for_mr", return_value=[])
    @mock.patch.object(gt, "mr_diff_raw")
    @mock.patch.object(gt, "mr_get")
    def test_valid_inline_position(self, mock_get, mock_diff, _mock_bodies):
        mock_get.return_value = {
            "diff_refs": {"base_sha": "b", "start_sha": "s", "head_sha": "h"},
        }
        mock_diff.return_value = [
            {"old_path": "src/foo.rs", "new_path": "src/foo.rs",
             "diff": "@@ -1,2 +1,2 @@\n-old\n+new\n context\n"},
        ]
        body_file = write_body("Inline comment.")
        ns = argparse.Namespace(iid=7, kind="review", path="src/foo.rs", line=1, side="new",
                                 body_file=body_file, expect_head_sha=None, dry_run=True)
        out = run_dry(gt.cmd_mr_discussion_create, ns)
        self.assertEqual(out["status"], "dry_run")
        self.assertEqual(out["payload"]["position"]["new_line"], 1)
        self.assertNotIn("fell_back_general", out)

    @mock.patch.object(gt, "existing_note_bodies_for_mr", return_value=[])
    @mock.patch.object(gt, "mr_diff_raw")
    @mock.patch.object(gt, "mr_get")
    def test_line_outside_hunk_falls_back_to_general(self, mock_get, mock_diff, _mock_bodies):
        mock_get.return_value = {
            "diff_refs": {"base_sha": "b", "start_sha": "s", "head_sha": "h"},
        }
        mock_diff.return_value = [
            {"old_path": "src/foo.rs", "new_path": "src/foo.rs",
             "diff": "@@ -1,1 +1,1 @@\n-old\n+new\n"},
        ]
        body_file = write_body("Comment on an untouched line.")
        ns = argparse.Namespace(iid=7, kind="review", path="src/foo.rs", line=999, side="new",
                                 body_file=body_file, expect_head_sha=None, dry_run=True)
        out = run_dry(gt.cmd_mr_discussion_create, ns)
        self.assertEqual(out["status"], "dry_run")
        self.assertTrue(out["fell_back_general"])
        self.assertIn("outside any hunk", out["fallback_reason"])
        self.assertNotIn("position", out["payload"])


class TestIssueNoteCreateDryRun(unittest.TestCase):
    @mock.patch.object(gt, "existing_note_bodies_for_issue", return_value=[])
    def test_dry_run_payload_shape(self, _mock):
        body_file = write_body("Proposed plan text.")
        ns = argparse.Namespace(iid=42, kind="plan", body_file=body_file, dry_run=True)
        out = run_dry(gt.cmd_issue_note_create, ns)
        self.assertEqual(out["status"], "dry_run")
        self.assertIn("Proposed plan text.", out["payload"]["body"])


class TestIssueLabelSetDryRun(unittest.TestCase):
    def test_dry_run_payload_shape(self):
        ns = argparse.Namespace(iid=42, add="plan::proposed", dry_run=True)
        out = run_dry(gt.cmd_issue_label_set, ns)
        self.assertEqual(out["status"], "dry_run")
        self.assertEqual(out["payload"]["add_labels"], "plan::proposed")


class TestMrCreateDryRun(unittest.TestCase):
    def test_closes_iid_inserted_when_absent(self):
        desc_file = write_body("Summary of the change.")
        ns = argparse.Namespace(title="Draft: my feature", source="feat/x", target="main",
                                 description_file=desc_file, label="ai-assisted",
                                 closes_iid=42, dry_run=True)
        out = run_dry(gt.cmd_mr_create, ns)
        self.assertEqual(out["status"], "dry_run")
        self.assertIn("Closes #42", out["payload"]["description"])

    def test_closes_iid_not_duplicated_when_already_present(self):
        desc_file = write_body("Closes #42\n\nSummary of the change.")
        ns = argparse.Namespace(title="Draft: my feature", source="feat/x", target="main",
                                 description_file=desc_file, label="ai-assisted",
                                 closes_iid=42, dry_run=True)
        out = run_dry(gt.cmd_mr_create, ns)
        self.assertEqual(out["payload"]["description"].count("Closes #42"), 1)

    def test_closes_iid_inserted_even_when_issue_merely_mentioned(self):
        # A bare "#42" in prose (not preceded by Closes/Fixes/Resolves) must
        # not be mistaken for an existing closing reference.
        desc_file = write_body("Implements the plan discussed on #42.")
        ns = argparse.Namespace(title="Draft: my feature", source="feat/x", target="main",
                                 description_file=desc_file, label="ai-assisted",
                                 closes_iid=42, dry_run=True)
        out = run_dry(gt.cmd_mr_create, ns)
        self.assertIn("Closes #42", out["payload"]["description"])


if __name__ == "__main__":
    unittest.main()
