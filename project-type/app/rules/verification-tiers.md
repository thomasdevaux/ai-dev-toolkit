# Verification tiers

Two tiers, which differ in **when** a check runs, never in **what** it checks.
Lint sets, denied warnings and "a finding is fixed or silenced with a reason"
are identical in both; narrowing a command to save time is not a tier.

The project names both commands in the Commands table of `AGENTS.md`, labelled
`fast` (formatters, linters, types: no tests) and `full` (everything). If they
aren't there, say so once and propose them.

## Iteration: on a branch, while the work moves

- **After an edit**, run only what that edit could break: the targeted test of
  the code touched, as named by the stack's style rule. A change with nothing
  to target (a shared type, a dependency bump) runs the suite once, when its
  code is finished.
- **When the task's code is finished**, run `fast` once. If a pre-commit hook
  runs it, committing is how it runs: don't run it by hand first.
- **After a failure**, fix it and re-run that check alone, not the whole command.
- **Never re-run a check that passed** unless something it reads has changed.
  A documentation edit does not invalidate the tests.
- **`full` does not belong here**, unless the user asks for it.

Handing work back before landing is not a reason to run more. Say what ran, and
that `full` has not.

## Ship: landing on the integration branch

`full`, once, on the final tree. Nothing lands unless it is green. Where it
runs and what enforces it is in the `git-workflow-app` skill.
