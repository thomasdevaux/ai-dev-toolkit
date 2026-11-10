# How skills invoke the tool

One convention, defined here only. If the tool ever moves, this is the one
file (plus each `SKILL.md`'s `--version` line) that changes.

```
python "<project-root>/.claude/skills/gitlab-common/bin/gitlab_tool.py" <group> <subcommand> [flags]
```

`<project-root>` is the developer's real checkout: **the primary working
directory the session started in**, before entering any worktree. Use
`$CLAUDE_PROJECT_DIR` only if it is actually set — the harness sets it for hook
executions, **not** for the Bash tool, where `"$CLAUDE_PROJECT_DIR/..."`
silently expands to a bogus path (`/.claude/skills/...`) and fails with "can't
open file". Never use a plain relative path either.

This matters specifically because `gitlab-mr-review` and `gitlab-mr-feedback`
run part of their work from inside a disposable git worktree
(`.claude/worktrees/mr-<iid>-...`), whose working directory is a checkout of
the MR's own commit — not necessarily one that contains this tool, or the
same version of it. The project root always holds the developer's own copy, so
the tool that runs is always the current one.

**The tool must exist on the project root's current branch.** While the skills
are committed only on a feature branch, switching the primary checkout to the
default branch (what `gitlab-issue-implement` does to create its branch) makes
the tool disappear mid-run. Check `--version` again after any `git switch` on
the primary checkout; if the tool is gone, work in a worktree instead of
switching (see `gitlab-issue-implement` step 1.4). This constraint goes away
once the tool lives outside the project (user-level skills directory).

## Credentials and console encoding

- Authentication is `glab`'s OAuth login (`glab auth login --hostname <host>
  --web`); see `README.md`. The tool aborts with `auth_policy` if a static
  token variable (`GITLAB_TOKEN`, ...) is set outside CI. It fills only
  `GITLAB_HOST` from the project's `.env` when it is not already in the
  environment. A worktree has no `.env` of its own — the tool looks at the
  `.env` of the checkout it lives in first, so this works from a worktree too.
  On an `auth` or `auth_policy` error, stop and tell the user to log in; never
  work around it.
- Output is forced to UTF-8: comment bodies start with an emoji and would
  otherwise crash on a Windows cp1252 pipe. No `PYTHONIOENCODING` needed.

The tool itself never assumes a specific working directory for anything other
than its own path: `glab api projects/:id/...` calls resolve `:id` from the
process's current directory's git remote, so they work correctly whether the
skill is running from the repo root or from inside a worktree on the same
`origin`.
