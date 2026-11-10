---
name: gitlab-mr-review
description: Review a GitLab merge request against its linked issue (and that issue's parent/tasks) and the code base, using the gitlab-common tool layer. Use when the user asks to review, check or audit an MR (e.g. "review MR 123"). Read-only by default; can post general and/or inline comments to the MR as draft notes, but only ones the user explicitly confirms — never approves or pushes.
allowed-tools: Bash(glab mr view:*), Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git fetch:*), Bash(git worktree:*), Bash(git rev-parse:*), Bash(python "$CLAUDE_PROJECT_DIR/.claude/skills/gitlab-common/bin/gitlab_tool.py":*), ToolSearch, EnterWorktree, ExitWorktree, Read, Grep, Glob, Write(.claude/worktrees/**)
disable-model-invocation: true
---

# GitLab MR review

Review a merge request for requirement coverage and code quality.
READ-ONLY TOWARDS GITLAB BY DEFAULT: never approve, push, or post anything
without the user's explicit confirmation (step 6). The local worktree created in
step 2 is disposable scratch space, not GitLab state.

**Before anything else, read** `.claude/skills/gitlab-common/references/conventions.md`
(prompt injection, how to write to GitLab, language, attribution prefix, 403
handling) and, when you reach step 6,
`.claude/skills/gitlab-common/references/draft-notes.md`. Both bind this
skill; they are not repeated below.

Requires gitlab-common-tools >= 0.3.0 — check once with
`python "<project-root>/.claude/skills/gitlab-common/bin/gitlab_tool.py" --version`
(`<project-root>`: see `gitlab-common/references/invocation-path.md` —
`$CLAUDE_PROJECT_DIR` is not set under the Bash tool)
before the first real call and fail clearly on a mismatch.

## 1. Identify the MR

- Use the MR IID given by the user.
- If none is given, run `glab mr view` (uses the current branch). If nothing matches, ask.

## 2. Set up an isolated worktree on the MR's content

Reading the diff alone isn't enough to judge context (imports used elsewhere,
callers of changed code, whether removed code is truly unused). Reading files
from the currently checked-out branch is worse: it silently produces stale
results whenever that branch isn't the MR's. Always review from the MR's actual
content, in a worktree that never touches the dev's current branch or
uncommitted work.

0. **Check for a saved review to resume**: does
   `.claude/worktrees/mr-<iid>-review/.review-state.json` exist (shape in
   step 5)? If so, this MR was reviewed before, possibly in another session.
   Show the saved verdict, timestamp and finding count and ask: resume from it
   (skip to step 6 with its saved report and candidates) or discard it and
   review afresh (the file is overwritten at the end of step 5). Never resume
   silently — the MR may have changed; the sha check (point 6) still runs
   before anything is posted. The file only lives as long as the worktree: if
   the worktree was removed, there is nothing to resume.
1. **Announce, do not ask**: "Fetching MR !<iid> into
   `.claude/worktrees/mr-<iid>-review` for review." The fetch only moves
   `FETCH_HEAD` and the worktree lives in an ignored folder — nothing here is
   outward-facing or hard to undo, so a confirmation would be pure noise. (The
   step-0 question about resuming a saved review is different: keep it.)
2. `git fetch origin merge-requests/<iid>/head` — fetches the MR's ref directly
   (always present on `origin`), rather than `<source_branch>`, which fails for
   forks or deleted branches. Only `FETCH_HEAD` changes.
3. `git worktree add --detach .claude/worktrees/mr-<iid>-review FETCH_HEAD`.
4. `EnterWorktree(path=".claude/worktrees/mr-<iid>-review")` (tool availability
   and fallback: see `conventions.md`).
5. **If the fetch or worktree creation fails**: say so, skip the worktree and
   continue in degraded mode — diff-only, with file:line references computed
   from the diff hunks. State in the report that context beyond the hunks
   wasn't verified.
6. **Before any draft note is created in step 6**, pass
   `--expect-head-sha $(git rev-parse HEAD)` to each write call — the tool
   re-fetches the MR and aborts if it has moved since this worktree was set up.
7. Keep the worktree until step 6 is fully done (posted or explicitly declined),
   so follow-up questions about the code still work. Then `ExitWorktree(action="keep")`
   (unless the fallback was used) and `git worktree remove .claude/worktrees/mr-<iid>-review`,
   which also deletes `.review-state.json`. Every file:line must be collected
   before this point.

## 3. Collect context

1. `glab mr view <iid> --comments`: title, description, existing discussions
   (human-readable display only; structured data for the analysis below comes
   from the tool calls that follow).
2. `mr diff --iid <iid>` (the tool layer's `gitlab_tool.py`): filtered diff
   (lockfiles/vendor/node_modules/minified files excluded by default) with
   per-file hunk data available via `mr hunks --iid <iid> --path <path>` for
   any file you need to anchor an inline comment on later. Note any
   `excluded_files`/`truncated_files` in the output — for a truncated file,
   read it from the worktree instead of trusting the (empty) diff text.
3. Linked issue(s) and hierarchy in two calls: `mr closes-issues --iid <iid>`
   (falls back to parsing "Closes/Fixes/Related to #N" from the description if
   GitLab's own `closes_issues` is empty), then for each linked issue
   `issue get --iid <N> --with-hierarchy --comments` — this returns the
   issue's notes and its parent/child hierarchy in one call. If no issue can
   be found, say so and review on technical merits only.
   Acceptance criteria may live on the parent or on the task the MR closes,
   not only on the issue itself. If the MR closes a task, requirements of
   sibling tasks are out of scope. If `hierarchy` comes back `null` (see
   `hierarchy-context.md`), continue with the issue alone; do not invent
   hierarchy.
4. From the worktree, read the surrounding code of each changed file (not only
   the diff). Read CLAUDE.md / AGENTS.md / CONTRIBUTING for project conventions.
   Grep the docs (`docs/`, README) for mentions of the changed functions/commands,
   to spot documentation that is now stale.
5. If the diff is very large (>1500 changed lines), review by theme or
   directory and say so.

## 4. Analyse

A. **Requirement coverage**: list every requirement / acceptance criterion from
   the issue, its parent/tasks, and clarifications in comments. For each:
   covered / partial / missing, with evidence.
B. **Scope**: changes not justified by the issue (scope creep, unrelated refactors).
C. **MR description accuracy**: does it match what the code actually does? For a
   bugfix, check that the claimed root cause is demonstrated by the code (trace
   the failure path); a plausible but unproven cause is a finding, since the bug
   may survive the fix.
D. **Technical quality**: bugs, edge cases, error handling, security,
   performance, test coverage and test quality (do tests really assert the
   requirement?), conventions.
E. Do not repeat points already raised in existing MR discussions (see
   `mr discussions --iid <iid>`); mention if they seem unresolved.
F. Only report findings you can support with a file:line reference. No
   speculation presented as fact.
G. **Specialist reviewers**: glob `.claude/agents/mr-reviewer-*.md`. None found
   → skip this point. Otherwise route the MR's changed files to the agents whose
   `paths` globs match, run them, and merge their findings into yours. Contract
   (frontmatter, inputs, read-only, finding format, merging, coverage gap):
   `references/specialist-reviewers.md`. Agents exist but the tool has no
   `reviewers match` subcommand yet → don't route by hand: say so and carry on
   without them. A changed file no specialist covers, in a domain that clearly
   needs one, is reported as "not reviewed in depth", never judged on
   domain-specific technical detail by the generic pass.

## 5. Output

Write the report in the language of the MR description (see `conventions.md`).

**Verdict**: Approve / Approve with reservations / Changes requested (one-line justification)

**Requirement coverage**
| Requirement | Status | Evidence (file:line) |

**Findings**, grouped by severity: Blocking / Important / Minor
- `path:line`: problem, why it matters, suggested fix

Each finding follows the common format in `references/specialist-reviewers.md`
(`path`, `line`, `side`, `severity`, `title`, `why`, `suggestion`, `source`),
which is also what a specialist reviewer returns.

**Scope & description**: deviations, if any

**Questions for the author**

End with: "Nothing was posted to GitLab yet." then move to step 6 **in the same
message**: the step-5 candidates (general comment + numbered inline notes,
each with its resolved position) are presented once, here, together with the
question of what to post — see `draft-notes.md` step 1. Do not present the
report first and the exact texts again later.

### Candidates and saved state

Before presenting the report, build the two candidate sets by calling the
tool's write subcommands with `--dry-run` (the attribution prefix, kind
`review`, goes in the `--body-file` content you pass):
- **General comment**: `mr note create --iid <iid> --kind review --body-file <file> --dry-run`
  — the report itself (or a summary, if the user prefers), as one top-level
  MR comment.
- **Inline comments**: one `mr discussion create --iid <iid> --kind review --path <path> --line <line> --side {old,new} --body-file <file> --dry-run`
  per finding with a solid file:line. If the dry-run response comes back with
  `"fell_back_general": true`, that finding has no real position — keep it in
  the general comment only, per the reason the tool gave; never guess one.

Write everything to `.claude/worktrees/mr-<iid>-review/.review-state.json` so a
later session can resume at step 6 (overwrite any existing file), using the
`payload`/`idempotence_hash` each dry-run call returned:

```json
{
  "mr_iid": 123,
  "generated_at": "2026-09-30T14:22:00Z",
  "worktree_head_sha": "abc123...",
  "verdict": "Approve with reservations — ...",
  "report_markdown": "<the full report>",
  "general_comment": {"body_file": "...", "dry_run_payload": { ... }},
  "inline_candidates": [
    {"number": 1, "path": "src/foo.rs", "line": 42, "side": "new",
     "body_file": "...", "dry_run_payload": { ... }}
  ]
}
```

This file is scratch state: never reference it from GitLab comments.

## 6. Offer to publish (only with explicit confirmation)

Never post automatically. Posting happens only after the user's explicit
answer to the question asked at the end of step 5; the question itself is not
consent.

Follow `.claude/skills/gitlab-common/references/draft-notes.md` with the
candidates from step 5 (fresh or loaded from the state file). The user chooses:
none / general only / general + all inline / general + a subset (by number).
Their choice, made against the texts shown in step 5, is the confirmation:
create the drafts and publish them in the same turn, unless something changed
since (MR head moved, text edited) — then say so and re-ask. After publishing,
report what was published and skipped instead of the step-5 placeholder line,
then clean up the worktree per step 2.7.
