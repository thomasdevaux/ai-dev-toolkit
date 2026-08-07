# Git workflow

Inside a git repository only. In an unversioned folder these don't apply —
don't propose `git init` unless asked.

- **Never commit to `main`, `master` or `develop`**, except the merge step
  that lands a finished branch.
- **Starting work while `HEAD` is on one of them**: propose a branch and its
  name before touching a file, not at commit time.
- **Never push, and never open a pull request, without explicit acceptance.**

The procedure — branch naming, squash, rebase, merge, cleanup — is the
`git-workflow-app` skill. The message itself is `commit-message-format`.
