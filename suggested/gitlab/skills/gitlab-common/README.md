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
  `PATH` and logged in through **OAuth, which is the only accepted method on a
  dev workstation**. Run once per instance:

  ```
  glab auth login --hostname <host> --web      # opens the browser
  glab auth login --hostname <host> --device   # no local browser (GitLab 17.9+)
  ```

  `glab` keeps the token in the OS keyring (Windows Credential Manager) and
  refreshes it itself. On a self-managed instance, `--web` needs an OAuth
  application registered on that instance; ask the GitLab admin if the
  browser flow is refused. Check with `glab auth status`.
- **No static token.** The tool refuses to run when `GITLAB_TOKEN`,
  `GITLAB_ACCESS_TOKEN` or `OAUTH_TOKEN` is set (error `auth_policy`, exit
  code 3): such a variable silently overrides the OAuth login, never
  refreshes and ends up in shell profiles and `.env` files. Unset it. **CI is
  the only exemption** (`CI` or `GITLAB_CI` set), where a project access token
  or job token is the only option.
- **`.env`**: only `GITLAB_HOST` is read from it (see `load_glab_env`), as a
  convenience to pick the instance. Credentials are never read from a file.

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
