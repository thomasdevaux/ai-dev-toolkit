"""Tests for the process-environment helpers: .env credential loading and
UTF-8 output. No network, no `glab`."""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "suggested" / "gitlab" / "skills" / "gitlab-common" / "bin"))
import gitlab_tool as gt  # noqa: E402


class TestParseEnvFile(unittest.TestCase):
    def test_keeps_only_glab_keys(self):
        text = "APP_SECRET=x\nGITLAB_HOST=https://gl.example\nGITLAB_BASE_URL=other\nGITLAB_TOKEN=abc\n"
        self.assertEqual(gt.parse_env_file(text),
                         {"GITLAB_HOST": "https://gl.example", "GITLAB_TOKEN": "abc"})

    def test_comments_export_and_quotes(self):
        text = '# GITLAB_TOKEN=ignored\nexport GITLAB_HOST="https://gl.example"\nGITLAB_TOKEN=\'tok\'\n'
        self.assertEqual(gt.parse_env_file(text),
                         {"GITLAB_HOST": "https://gl.example", "GITLAB_TOKEN": "tok"})

    def test_ignores_lines_without_equals(self):
        self.assertEqual(gt.parse_env_file("GITLAB_TOKEN\n"), {})


class TestLoadGlabEnv(unittest.TestCase):
    def _env_file(self, text: str) -> Path:
        d = Path(tempfile.mkdtemp())
        p = d / ".env"
        p.write_text(text, encoding="utf-8")
        return p

    def test_fills_missing_variables(self):
        p = self._env_file("GITLAB_HOST=https://gl.example\nGITLAB_TOKEN=abc\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            gt.load_glab_env([p])
            self.assertEqual(os.environ["GITLAB_HOST"], "https://gl.example")
            self.assertEqual(os.environ["GITLAB_TOKEN"], "abc")

    def test_never_overrides_an_existing_variable(self):
        p = self._env_file("GITLAB_TOKEN=from-file\n")
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": "explicit"}, clear=True):
            gt.load_glab_env([p])
            self.assertEqual(os.environ["GITLAB_TOKEN"], "explicit")

    def test_missing_file_is_not_an_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            gt.load_glab_env([Path(tempfile.mkdtemp()) / ".env"])
            self.assertNotIn("GITLAB_TOKEN", os.environ)

    def test_first_candidate_with_credentials_wins(self):
        first = self._env_file("APP_ONLY=1\n")
        second = self._env_file("GITLAB_TOKEN=second\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            gt.load_glab_env([first, second])
            self.assertEqual(os.environ["GITLAB_TOKEN"], "second")


class TestForceUtf8Streams(unittest.TestCase):
    def test_emoji_prints_on_a_cp1252_stream(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        with mock.patch.object(sys, "stdout", stream), mock.patch.object(sys, "stderr", io.StringIO()):
            gt.force_utf8_streams()
            gt.print_json({"body": "\U0001F916 review"})
            sys.stdout.flush()
        self.assertIn("\U0001F916".encode("utf-8"), raw.getvalue())


if __name__ == "__main__":
    unittest.main()
