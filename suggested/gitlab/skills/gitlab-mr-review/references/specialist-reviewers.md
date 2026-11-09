# Specialist reviewers

A specialist reviewer is a sub-agent that reviews the part of an MR it knows
better than the generic pass (e.g. AUTOSAR `.arxml` files). Specialists are
**discovered, not listed**: `SKILL.md` step 4.G holds the rule, this file holds
the contract. Adding a specialist means dropping one file, never editing the
skill.

## Discovery convention

- A specialist is `.claude/agents/mr-reviewer-<domain>.md`.
- Its frontmatter declares what it covers, in `paths` (list of globs, matched
  against repo-relative paths with `/` separators):

```markdown
---
name: mr-reviewer-autosar
description: Reviews AUTOSAR ARXML changes in a merge request. Read-only.
tools: Read, Grep, Glob
paths:
  - "**/*.arxml"
---
<domain rules, checklists, pitfalls>
```

- `paths` is required. An agent named `mr-reviewer-*` without it is ignored and
  reported as misconfigured.
- Routing is by glob on the MR's changed files, never by the model's judgement:
  a silently skipped specialist is the worst failure mode of a review.
- A file matching several specialists goes to each of them; findings are
  deduplicated afterwards.

## What a specialist receives

It does not see the conversation. The orchestrator passes, explicitly:

- its files from the MR diff (paths + hunks), and the worktree path to read
  surrounding code from;
- the linked issue's requirements and acceptance criteria;
- the project conventions relevant to those files.

## What a specialist may do

- **Read-only**: `Read`, `Grep`, `Glob` at most. Never a GitLab write tool,
  never `gitlab_tool.py` write subcommands. Publishing stays in step 6, behind
  the user's confirmation.
- Return findings in the common format below, and nothing else.

## Finding format

Shared by the generic pass and every specialist:

```json
{
  "path": "src/foo.rs",
  "line": 42,
  "side": "new",
  "severity": "blocking | important | minor",
  "title": "one line",
  "why": "why it matters",
  "suggestion": "suggested fix",
  "source": "core | mr-reviewer-<domain>"
}
```

Same rule as the generic pass: no finding without a `path:line` it can be
supported with.

## Merging

The orchestrator merges specialist findings into the single step-5 report,
dropping duplicates (same `path`, overlapping `line`, same point made) and
keeping the higher severity. `source` is kept internally for traceability; the
report groups by severity, not by reviewer.

## Coverage gap

A changed file matched by no specialist is not an error, but a file whose
domain clearly needs one is stated in the report: "not reviewed in depth: no
specialist for `<glob or extension>`". The generic pass judges such a file
against the issue and the scope only, never the domain-specific technical
detail.

## Not implemented yet

Matching is meant to be a `gitlab_tool.py` subcommand
(`reviewers match --files <...>`) so it is deterministic and unit-testable.
It gets written with the first real `mr-reviewer-*` agent. Also at that point:
add `Agent` to the skill's `allowed-tools`.
