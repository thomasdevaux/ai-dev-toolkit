"""Tests for the merge gate: the reference Git hooks and the session check.

Driven through real git in a temporary repository, because the contract is
git's behaviour (what fires, what state a refusal leaves), not the scripts' text.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCES = ROOT / "project-type/app/skills/git-workflow-app/references/githooks"
SESSION_CHECK = ROOT / "project-type/app/hooks/merge-gate-check.sh"

# The sh `bash` resolves to may be WSL's on Windows; the one beside git is the one
# Claude Code's hooks run under.
GIT = shutil.which("git")
GIT_BASH = Path(GIT).parents[1] / "bin" / "bash.exe" if GIT else None
BASH = str(GIT_BASH) if GIT_BASH and GIT_BASH.exists() else shutil.which("bash")

pytestmark = pytest.mark.skipif(not GIT or not BASH, reason="needs git and bash")


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args],
        cwd=repo, env=env, text=True, capture_output=True, check=check,
    )


def install_hook(repo: Path, name: str, placeholder: str, command: str) -> None:
    text = (REFERENCES / name).read_text(encoding="utf-8")
    assert placeholder in text
    path = repo / ".githooks" / name
    path.write_text(text.replace(placeholder, command), encoding="utf-8", newline="\n")
    path.chmod(0o755)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo on main with the hooks active. The full gate fails iff FULL_FAILS exists,
    and logs each run to gate.log, which is ignored so that it doesn't dirty the tree."""
    (tmp_path / ".githooks").mkdir()
    install_hook(tmp_path, "pre-merge-commit", "<the `full` command from AGENTS.md>",
                 "echo full >> gate.log; test ! -f FULL_FAILS")
    install_hook(tmp_path, "pre-commit", "<the `fast` command from AGENTS.md>",
                 "echo fast >> gate.log")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / ".gitignore").write_text("gate.log\nFULL_FAILS\n", encoding="utf-8")
    (tmp_path / "f.txt").write_text("base\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    git(tmp_path, "config", "core.hooksPath", ".githooks")
    return tmp_path


def branch_with_commit(repo: Path, name: str, filename: str = "f.txt") -> None:
    git(repo, "checkout", "-q", "-b", name)
    with (repo / filename).open("a", encoding="utf-8") as fh:
        fh.write(name + "\n")
    git(repo, "commit", "-qam", name)
    git(repo, "checkout", "-q", "main")
    (repo / "gate.log").unlink(missing_ok=True)


def gate_log(repo: Path) -> list[str]:
    log = repo / "gate.log"
    return log.read_text(encoding="utf-8").split() if log.exists() else []


def head_subject(repo: Path) -> str:
    return git(repo, "log", "-1", "--format=%s").stdout.strip()


def merge_head(repo: Path) -> bool:
    return (repo / ".git" / "MERGE_HEAD").exists()


def test_green_merge_lands_and_runs_full_once(repo: Path) -> None:
    branch_with_commit(repo, "feat/x")
    git(repo, "merge", "--no-ff", "-m", "landed", "feat/x")
    assert head_subject(repo) == "landed"
    assert gate_log(repo) == ["full"]


def test_red_gate_refuses_and_abort_restores(repo: Path) -> None:
    branch_with_commit(repo, "feat/x")
    (repo / "FULL_FAILS").touch()
    result = git(repo, "merge", "--no-ff", "-m", "landed", "feat/x", check=False)
    assert result.returncode != 0
    assert "git merge --abort" in result.stderr
    assert head_subject(repo) == "base"
    git(repo, "merge", "--abort")
    assert not merge_head(repo)


def test_git_commit_cannot_finish_a_refused_merge(repo: Path) -> None:
    """Git itself suggests this after a refusal; pre-merge-commit doesn't fire on it."""
    branch_with_commit(repo, "feat/x")
    (repo / "FULL_FAILS").touch()
    git(repo, "merge", "--no-ff", "-m", "landed", "feat/x", check=False)
    result = git(repo, "commit", "-qm", "sneaked", check=False)
    assert result.returncode != 0
    assert head_subject(repo) == "base"


def test_conflict_resolution_runs_full(repo: Path) -> None:
    branch_with_commit(repo, "feat/a")
    branch_with_commit(repo, "feat/b")
    git(repo, "merge", "--no-ff", "-m", "a", "feat/a")
    assert git(repo, "merge", "--no-ff", "-m", "b", "feat/b", check=False).returncode != 0
    (repo / "f.txt").write_text("resolved\n", encoding="utf-8")
    git(repo, "add", "f.txt")
    (repo / "gate.log").unlink()
    git(repo, "commit", "-qm", "b resolved")
    assert gate_log(repo) == ["full"]


def test_merge_into_a_feature_branch_runs_nothing(repo: Path) -> None:
    branch_with_commit(repo, "feat/x")
    (repo / "FULL_FAILS").touch()
    git(repo, "checkout", "-q", "-b", "feat/y")
    git(repo, "merge", "--no-ff", "-m", "not a landing", "feat/x")
    assert gate_log(repo) == []


def test_ordinary_commit_runs_fast_only(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "feat/x")
    (repo / "f.txt").write_text("edit\n", encoding="utf-8")
    git(repo, "commit", "-qam", "edit")
    assert gate_log(repo) == ["fast"]


def test_unstaged_change_refuses_before_running_the_gate(repo: Path) -> None:
    branch_with_commit(repo, "feat/x", filename="f.txt")
    (repo / "other.txt").write_text("tracked\n", encoding="utf-8")
    git(repo, "add", "other.txt")
    git(repo, "checkout", "-q", "feat/x")
    git(repo, "commit", "-qm", "other")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "--no-ff", "-m", "first", "feat/x")
    git(repo, "checkout", "-q", "-b", "feat/y", "HEAD~1")
    (repo / "z.txt").write_text("z\n", encoding="utf-8")
    git(repo, "add", "z.txt")
    git(repo, "commit", "-qm", "z")
    git(repo, "checkout", "-q", "main")
    (repo / "other.txt").write_text("dirty\n", encoding="utf-8")
    (repo / "gate.log").unlink()
    result = git(repo, "merge", "--no-ff", "-m", "second", "feat/y", check=False)
    assert result.returncode != 0
    assert "unstaged changes" in result.stderr
    assert gate_log(repo) == []


def test_gate_that_changes_tracked_files_refuses(repo: Path) -> None:
    install_hook(repo, "pre-merge-commit", "<the `full` command from AGENTS.md>",
                 "echo regenerated >> f.txt")
    git(repo, "commit", "-qam", "gate that regenerates")
    git(repo, "checkout", "-q", "-b", "feat/x")
    (repo / "z.txt").write_text("z\n", encoding="utf-8")
    git(repo, "add", "z.txt")
    git(repo, "commit", "-qm", "z")
    git(repo, "checkout", "-q", "main")
    result = git(repo, "merge", "--no-ff", "-m", "landed", "feat/x", check=False)
    assert result.returncode != 0
    assert "changed tracked files" in result.stderr


def test_gate_does_not_inherit_the_repository_from_the_hook(repo: Path) -> None:
    """A test creating its own repository must not commit into this one."""
    sandbox = repo.parent / "sandbox"
    install_hook(
        repo, "pre-merge-commit", "<the `full` command from AGENTS.md>",
        f"git init -q '{sandbox.as_posix()}' && cd '{sandbox.as_posix()}' "
        "&& git -c user.email=t@e -c user.name=t commit -q --allow-empty -m from-the-gate",
    )
    git(repo, "commit", "-qam", "gate that makes a repository")
    branch_with_commit(repo, "feat/x")
    git(repo, "merge", "--no-ff", "-m", "landed", "feat/x")
    assert git(sandbox, "log", "-1", "--format=%s").stdout.strip() == "from-the-gate"
    subjects = git(repo, "log", "--format=%s").stdout
    assert "from-the-gate" not in subjects


def session_check(project: Path) -> str:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": project.as_posix()}
    done = subprocess.run([BASH, SESSION_CHECK.as_posix()], env=env, text=True,
                          capture_output=True, check=True)
    return done.stdout


def test_session_check_silent_when_gate_is_active(repo: Path) -> None:
    assert session_check(repo) == ""


def test_session_check_reports_a_clone_without_hookspath(repo: Path) -> None:
    git(repo, "config", "--unset", "core.hooksPath")
    assert "core.hooksPath" in session_check(repo)


def test_session_check_reports_no_gate_and_no_ci(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    assert "no CI and no pre-merge-commit" in session_check(tmp_path)


def test_session_check_silent_with_ci_config(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    (tmp_path / ".gitlab-ci.yml").touch()
    assert session_check(tmp_path) == ""


def test_session_check_silent_outside_a_repository(tmp_path: Path) -> None:
    assert session_check(tmp_path) == ""
