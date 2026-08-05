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

### Commit message format

- **Subject**: imperative mood, capitalised, no trailing period, ideally
  under ~70 characters (e.g. "Add retry logic", not "Added retry logic" or
  "Adding retry logic").
- **Body required for non-trivial changes**: if the commit touches more than
  one concern, or the reasoning isn't obvious from the diff, add a blank
  line after the subject and a bulleted body — one bullet per distinct
  change. A single-purpose, self-explanatory change (e.g. a one-line typo
  fix) can ship as a bare subject.
- **Body explains why, not what**: the diff already shows what changed;
  use the body for the reasoning, trade-offs, or context a reviewer can't
  get from the code alone.
- **Not Conventional Commits**: do not prefix subjects with `feat:`,
  `fix:`, etc. — this repo's history doesn't use that format and it is not
  required here.
- Example of a good commit message following this format:

  ```
  Add retry logic to the payment webhook handler

  - Retries transient 5xx responses up to 3 times with backoff, since the
    upstream gateway occasionally times out under load.
  - Logs each retry attempt so failures are traceable without reproducing
    the outage.
  ```

  Compare with an example to avoid — a bare, generic subject with no body
  explaining why the change was made:

  ```
  fix stuff
  ```