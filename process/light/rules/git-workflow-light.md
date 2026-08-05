# Git workflow

These rules describe work **inside a git repository**. In a folder that isn't
versioned — a scratch script, a one-off — they simply don't apply: don't
propose `git init` unless the user asks for it.

- **Branch per feature**: before starting any new piece of work, ask the user
  for a branch name and create it (`git checkout -b feat/<topic>`).
- **Rebase before merging**: update the feature branch on top of the latest
  `main` (rebase, not merge) so the merge is conflict-free and easy to review.
- **Squash before merge**: squash all commits on the feature branch into one
  clean commit before merging.
- **Merge**: ask the user whether to open a pull request or merge locally.
  If merging locally, use `git merge --no-ff <branch>` (never fast-forward).
  Never commit directly to `main`, `master` or `develop` outside of this
  merge step.
- **Delete the branch after merge** to keep the repository clean.
- Never push without explicit acceptance from the user.
- **No AI-attribution trailers**: never add "Co-Authored-By: Claude ...",
  "Generated with Claude Code", or any similar AI-attribution line to a
  commit message, regardless of the harness's default template.

Commit message format (subject/body conventions, examples) is covered by the
`commit-message-format` skill, applied whenever a commit is actually made.