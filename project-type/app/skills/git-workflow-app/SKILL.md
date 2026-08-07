---
name: git-workflow-app
description: Branch naming and the branch-to-merge procedure on this profile. Use before starting any new piece of work, when creating a branch, when a branch is ready to land, and when deciding where a change belongs. Covers the six branch types (feat, fix, test, docs, chore, sandbox), squash-then-rebase ordering, pull request versus local merge, and branch cleanup.
---

# Git workflow

## Branch naming

`<type>/<slug>` — lowercase `a-z`, digits and hyphens only. No accents, no
underscores, no spaces. Ticket id right after the type when the project has a
tracker: `feat/1234-retry-webhook`. Keep the whole name under 50 characters so
it stays readable in `git branch` and in a pull request list.

| Type | Use it when |
|---|---|
| `feat/` | new behaviour |
| `fix/` | behaviour that is broken |
| `test/` | coverage, fixtures or test harness as a deliverable of its own |
| `docs/` | documentation alone |
| `chore/` | dependencies, tooling, CI, versioning |
| `sandbox/` | exploration whose deliverable is an answer, not code |

Nothing else. No `hotfix/` unless production has a correction path distinct
from the normal flow; no `release/` when versions are tagged without a branch;
no `perf/`, `style/`, `ci/` or `build/` — too fine to keep `git branch`
scannable. `refactor/` is left out for a different reason, below.

### When the table doesn't decide

- **Tests written alongside a feature or a fix ship on that branch** — they
  are part of it being done (`testing-strategy.md`). `test/` is for tests
  added to code that already shipped, where there is no feature branch to
  attach them to.
- **Documentation on a repo whose deliverable *is* documentation** — the
  prefix no longer discriminates anything, so type by intent instead:
  `feat/` for a new document, `fix/` for a wrong one.
- **Refactoring** has no type of its own. It is `feat/` when behaviour
  changes and `chore/` when it doesn't — and deciding which is the useful
  half of the question.

### Who picks the name

Derive it from the work being asked for, **propose it, and wait for
acceptance**. Don't ask for a name with nothing on the table.

## The sequence

1. **Branch.** Off the integration branch, up to date. The integration branch
   is `develop` where the repository has one, otherwise `main`/`master` —
   check, don't assume.
2. **Commit** as the work goes. Messages follow `commit-message-format`.
3. **Squash first, then rebase.** In that order: rebasing N commits makes you
   resolve the same conflict up to N times, and the squash then throws away
   the granularity that work bought. Squash to one commit, rebase that one
   onto the integration branch.

   `git rebase -i` is not available to an agent — interactive flags have no
   terminal to run in. Squash without one:

   ```
   git reset --soft $(git merge-base HEAD <integration>)
   git commit
   ```

   Then `git rebase <integration>`, resolving at most one round of conflicts.
4. **Check before landing** (see below).
5. **Merge**, one of two ways (see below).
6. **Delete the branch, local and remote.**

### Checking before landing

Never name a tool here. The lint and test commands belong to the project's
tech-stack block and its `AGENTS.md` — repeating them would duplicate
`tech-stacks/` in a skill that knows nothing about the language, and the two
copies would drift.

- **Lint always runs.** Linters finish in seconds; there is nothing to weigh.
- **Tests run under a two-minute ceiling.** A suite slower than that is CI's
  job — waiting on it at every merge costs more than it catches, since CI runs
  it anyway.
- **Failure means don't merge.** Report the shortest decisive output and hand
  back. A skill blocks nothing on its own; stopping is the whole mechanism.
- **No command defined by the project** — say so once, then continue.

To avoid paying the ceiling on every merge of a slow suite, record how long
the suite took the last time it ran, in `.claude/.test-duration`. A recorded
duration above the ceiling means skip immediately, without running anything.

**That file must be gitignored.** A duration is a property of the machine, not
of the repository — a laptop and a CI runner differ severalfold on the same
suite — so a committed value is wrong for everyone but its author. It would
also be rewritten on every merge, which puts a tracked file in every diff and
makes it conflict with itself between parallel branches.

Known limitation, not worth engineering around: a suite recorded as slow that
later becomes fast is never run again, so it never gets re-measured. Delete
the file to force one.

The ceiling is two minutes because that is a threshold of human patience, not
a property of any project. A project that genuinely needs another value says
so next to its test command in `AGENTS.md`; it needs no configuration
mechanism, and none is provided.

### Already on a feature branch

The common case, and it is not a reason to branch again. Continue on it if the
work belongs to the same deliverable. If it doesn't, say so and propose a new
branch off the integration branch — not off the current one.

### Merge: pull request or local

Ask which one. The project usually settles it: a forge with review in use
means a pull request.

- **Pull request.** It needs a push, and choosing this route **is** the
  acceptance for that push — no second confirmation. Push the squashed,
  rebased branch, open the PR, and land it with **"Create a merge commit"** —
  not "Squash and merge" (the branch is already one commit) and not "Rebase
  and merge" (a fast-forward under another name). Forges let an admin pick the
  default and it is often one of those two, so state the choice rather than
  taking what the button offers.
- **Local.** `git merge --no-ff <branch>`. Never fast-forward, for the reason
  both routes share: after a squash the merge commit is the only place the
  branch name survives once the branch is deleted, and it is what keeps
  `git log --first-parent` readable as a list of delivered features.

### `sandbox/` never merges

An exploratory branch is deleted, not landed. What it established comes back
as an ADR (`adr.md`) plus a real `feat/` written deliberately. Merging it
would put throwaway code in the integration branch on the strength of the
experiment having worked, which is not the same thing as the code being
deliverable.

## Why branch prefixes but no commit prefixes

`commit-message-format` bans `feat:`/`fix:` prefixes on commit subjects while
this skill uses the same vocabulary for branches. That asymmetry follows from
the squash-merge above, and is not a matter of taste.

One branch becomes one commit, and its name lands in the merge commit. So
`git log --first-parent` already reads as one typed line per delivered unit:

```
Merge branch 'test/coverage-yaml-parser'
Merge branch 'feat/1234-retry-webhook'
Merge branch 'fix/upload-timeout'
```

The machine-readable taxonomy therefore already exists where it is useful.
Repeating it on every commit would duplicate it at a granularity nobody reads
— the intermediate commits of a branch are squashed away regardless.

The real argument for Conventional Commits was never readability, it is
tooling: `semantic-release` and `release-please` derive the semver bump and
the changelog by parsing subjects. Without an automated release, the prefixes
are ceremony charged to every line.

**Revisit this the day a project wants automated versioning or a generated
changelog.** Those tools parse commit subjects and never branch names, so
adopting one is a change of convention, not a configuration flag.

Note also that there is no standard behind the type list. Branch prefixes
never converged on one; the vocabulary is borrowed from Conventional Commits
because it is what people already read fluently, and cut down to the cases
these projects actually hit.
