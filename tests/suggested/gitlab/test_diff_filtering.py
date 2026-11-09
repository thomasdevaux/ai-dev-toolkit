"""Unit tests for diff file filtering (exclude/include/truncation). No network calls."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "suggested" / "gitlab" / "skills" / "gitlab-common" / "bin"))
import gitlab_tool as gt  # noqa: E402


class TestFilterDiffFiles(unittest.TestCase):
    def test_lockfile_excluded_by_default(self):
        files = [
            {"old_path": "package-lock.json", "new_path": "package-lock.json", "diff": "..."},
            {"old_path": "src/foo.rs", "new_path": "src/foo.rs", "diff": "@@ -1 +1 @@\n-a\n+b\n"},
        ]
        result = gt.filter_diff_files(files)
        kept_paths = [f["new_path"] for f in result["files"]]
        excluded_paths = [f["path"] for f in result["excluded_files"]]
        self.assertEqual(kept_paths, ["src/foo.rs"])
        self.assertIn("package-lock.json", excluded_paths)

    def test_vendor_and_node_modules_excluded(self):
        files = [
            {"new_path": "vendor/lib.js", "diff": "..."},
            {"new_path": "node_modules/pkg/index.js", "diff": "..."},
            {"new_path": "src/app.ts", "diff": "..."},
        ]
        result = gt.filter_diff_files(files)
        kept_paths = {f["new_path"] for f in result["files"]}
        self.assertEqual(kept_paths, {"src/app.ts"})

    def test_include_overrides_default_exclude(self):
        files = [{"old_path": "vendor/patched.js", "new_path": "vendor/patched.js", "diff": "..."}]
        result = gt.filter_diff_files(files, include_globs=["vendor/patched.js"])
        kept_paths = [f["new_path"] for f in result["files"]]
        self.assertEqual(kept_paths, ["vendor/patched.js"])
        self.assertEqual(result["excluded_files"], [])

    def test_truncated_file_reported_not_dropped(self):
        files = [{"new_path": "src/huge.rs", "diff": "", "new_file": False, "deleted_file": False}]
        result = gt.filter_diff_files(files)
        self.assertEqual(len(result["files"]), 1)  # not dropped
        self.assertEqual(len(result["truncated_files"]), 1)
        self.assertEqual(result["truncated_files"][0]["path"], "src/huge.rs")

    def test_new_empty_file_is_not_flagged_truncated(self):
        files = [{"new_path": "src/empty.rs", "diff": "", "new_file": True}]
        result = gt.filter_diff_files(files)
        self.assertEqual(result["truncated_files"], [])

    def test_minified_and_map_excluded(self):
        files = [
            {"new_path": "public/bundle.min.js", "diff": "..."},
            {"new_path": "public/bundle.js.map", "diff": "..."},
            {"new_path": "src/index.js", "diff": "..."},
        ]
        result = gt.filter_diff_files(files)
        kept_paths = {f["new_path"] for f in result["files"]}
        self.assertEqual(kept_paths, {"src/index.js"})


class TestParseClosesIssues(unittest.TestCase):
    def test_various_keywords(self):
        desc = "This closes #12 and also Fixes #7. See resolves #99 too."
        self.assertEqual(gt.parse_closes_issues_from_description(desc), [7, 12, 99])

    def test_no_match(self):
        self.assertEqual(gt.parse_closes_issues_from_description("no references here"), [])

    def test_none_description(self):
        self.assertEqual(gt.parse_closes_issues_from_description(None), [])


if __name__ == "__main__":
    unittest.main()
