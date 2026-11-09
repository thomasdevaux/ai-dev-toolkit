"""Unit tests for the idempotence hash/marker scheme. No network calls."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "suggested" / "gitlab" / "skills" / "gitlab-common" / "bin"))
import gitlab_tool as gt  # noqa: E402


class TestIdempotenceHash(unittest.TestCase):
    def test_same_input_same_hash(self):
        h1 = gt.idempotence_hash("review", "general", "This is a finding.")
        h2 = gt.idempotence_hash("review", "general", "This is a finding.")
        self.assertEqual(h1, h2)

    def test_whitespace_only_change_same_hash(self):
        h1 = gt.idempotence_hash("review", "src/foo.rs:42", "Line too long.  \n\nFix it.")
        h2 = gt.idempotence_hash("review", "src/foo.rs:42", "Line too long. Fix it.")
        self.assertEqual(h1, h2)

    def test_real_content_change_different_hash(self):
        h1 = gt.idempotence_hash("review", "src/foo.rs:42", "Line too long.")
        h2 = gt.idempotence_hash("review", "src/foo.rs:42", "Line too short.")
        self.assertNotEqual(h1, h2)

    def test_different_target_different_hash(self):
        h1 = gt.idempotence_hash("review", "src/foo.rs:42", "same body")
        h2 = gt.idempotence_hash("review", "src/bar.rs:42", "same body")
        self.assertNotEqual(h1, h2)

    def test_different_kind_different_hash(self):
        h1 = gt.idempotence_hash("review", "general", "same body")
        h2 = gt.idempotence_hash("feedback", "general", "same body")
        self.assertNotEqual(h1, h2)


class TestMarkerRoundTrip(unittest.TestCase):
    def test_build_and_find_marker(self):
        full_body, h = gt.build_marked_body("prefix line", "the actual comment", "review", "general")
        self.assertIn(f"<!-- ai-hash:{h} -->", full_body)
        self.assertTrue(gt.find_existing_hash([full_body], h))

    def test_find_existing_hash_no_match(self):
        self.assertFalse(gt.find_existing_hash(["unrelated body"], "deadbeefdeadbeef"))

    def test_find_existing_hash_among_many_bodies(self):
        _, h = gt.build_marked_body("", "target comment", "plan", "general")
        bodies = ["irrelevant note", "another note", gt.build_marked_body("", "target comment", "plan", "general")[0]]
        self.assertTrue(gt.find_existing_hash(bodies, h))


if __name__ == "__main__":
    unittest.main()
