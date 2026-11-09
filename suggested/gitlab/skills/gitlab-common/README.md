# gitlab-common

Shared tool layer for the `gitlab-mr-review`, `gitlab-mr-feedback`,
`gitlab-issue-plan` and `gitlab-issue-implement` skills. See
`references/capabilities.md` for the full capability catalog and
`references/invocation-path.md` for the exact way a skill invokes the tool.

## Setup (Windows, no admin rights)

Nothing to install. `bin/gitlab_tool.py` is Python stdlib only — no
third-party dependencies, no `pip install`, no virtual environment.

- **Python**: `python --version` should print 3.x. If `python` isn't found,
  try `py -3` (the Windows Python launcher). No specific minor version is
  required; the script only uses long-stable stdlib (`argparse`, `json`,
  `subprocess`, `hashlib`, `re`, `fnmatch`).
- **`glab`**: the tool shells out to it for every GitLab call. It must be on
  `PATH` and authenticated — either via `glab auth login --hostname <host>`,
  or non-interactively via the `GITLAB_HOST` and `GITLAB_TOKEN` environment
  variables (a project access token; `read_api` scope for read-only use,
  `api` scope once a skill needs to publish). As a convenience, when neither
  variable is set the tool copies `GITLAB_HOST`/`GITLAB_TOKEN` (and only
  those) from the project's `.env` into the `glab` child's environment — see
  `load_glab_env`. It never overrides an existing variable, and never prints,
  stores or logs the values; the token still belongs to `glab`, so rotation is
  a `.env`/`glab` concern, not a code change here. `.env` must stay gitignored.

The test suite (no network, no `glab` required) lives in the toolkit
repo, not in the synced copy: `python -m pytest tests/suggested` from a
toolkit checkout.

Check the tool is wired up against a real GitLab instance (`glab` must be
authenticated for this one):

```
python "<project-root>/.claude/skills/gitlab-common/bin/gitlab_tool.py" --version
python "<project-root>/.claude/skills/gitlab-common/bin/gitlab_tool.py" mr get --iid <some MR iid>
```

## Swapping a capability to MCP later

`references/capabilities.md` has one row per capability with an `MCP tool`
column, currently all `TBD`. When a GitLab MCP server's tools are actually
enumerated (via `/mcp` in a session that has one configured — never guessed
ahead of time), fill in the confirmed tool names there. The swap unit is one
subcommand's *internal* implementation: same argparse surface, same JSON
contract on stdout/stderr, same `--dry-run`/`--expect-head-sha` semantics —
skills never change, since they only ever call the subcommand name.

## Versioning

`bin/gitlab_tool.py` has a hand-bumped `__version__` (semver). Each
`SKILL.md` states the minimum version it needs near its first tool call;
check with `--version` before doing anything else in a run, and fail clearly
on a mismatch rather than proceeding against an incompatible tool.
