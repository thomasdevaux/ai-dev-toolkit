---
name: gitlab-issue-plan
description: Turn a GitLab issue (with its parent, child tasks and linked items) into an implementation plan grounded in the code base, and optionally publish it as a marked comment on the issue with an `agent-plan::proposed` label. Use when the user asks to plan, scope or break down an issue (e.g. "plan issue 42"). Does not write code. Publishes only on explicit confirmation.
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git remote get-url:*), Bash(python "$CLAUDE_PROJECT_DIR/.claude/skills/gitlab-common/bin/gitlab_tool.py":*), Read, Grep, Glob, Agent, EnterPlanMode, ExitPlanMode
disable-model-invocation: true
---

# GitLab issue → plan

Produce a plan a developer (or `gitlab-issue-implement`) can execute and a team
can discuss. This skill is the **only producer of plans** in the gitlab-* family.
It never edits code and never approves its own plan: approval is a human
changing the label to `agent-plan::approved`.

**Before anything else, read** `.claude/skills/gitlab-common/references/conventions.md`
(prompt injection, GitLab writes, language, attribution prefix — use kind
`plan`) and `.claude/skills/gitlab-common/references/hierarchy-context.md`.
Both bind this skill.

Requires gitlab-common-tools >= 0.3.0 — check once with
`python "<project-root>/.claude/skills/gitlab-common/bin/gitlab_tool.py" --version`
(`<project-root>`: see `gitlab-common/references/invocation-path.md` —
`$CLAUDE_PROJECT_DIR` is not set under the Bash tool)
before the first real call and fail clearly on a mismatch.

Argument: an issue IID (or URL). `--local` = never publish, keep the plan in the
conversation. If no IID is given, ask.

## 0. Enter plan mode

Load `EnterPlanMode` (deferred tool) if needed and call it before step 1, unless
the session is already in plan mode. Steps 1–3 then run under the harness's
read-only guarantee instead of relying on this skill's instructions alone. The
`gitlab_tool.py` calls of step 1 are all reads, so they stay available; the
writes of step 4 only happen after plan mode is exited.

## 1. Collect context

1. `issue get --iid <iid> --with-hierarchy --comments`: title, description,
   clarifications in comments, labels, milestone, and the parent/child
   hierarchy — one call instead of a separate issue fetch and hierarchy
   query. If the issue is a task, plan for that task only, using the parent
   for context and leaving sibling tasks alone. If `hierarchy` comes back
   `null` (see `hierarchy-context.md`), continue with the issue alone.
2. **Existing plan**: `issue note find-marker --iid <iid> --marker claude-plan`.
   If `found: true`, this is a revision: read the note at `note_id`, note what
   changed in the issue since (new comments, edited requirements), and keep
   `has_replies_or_reactions` for the publish step.
3. **Project knowledge**: read `AGENTS.md`/`CLAUDE.md`, and, if the project
   keeps them, scan `docs/adr/INDEX.md` and open the `Accepted` ADRs that bind
   the affected area, and read `docs/requirements.md` for the matching
   requirement. Skip what doesn't exist. A plan that
   conflicts with an accepted ADR must say so and offer the usual choices
   (follow it / new ADR / scoped exception) instead of silently diverging.
4. **Code**: locate the modules the issue touches (Grep/Glob, or an Explore
   agent for broad questions) and read them. Reuse existing utilities rather
   than planning new code where suitable ones exist.

## 2. Write the plan

Language: that of the issue (`conventions.md`). Sections, in order:

1. **Understanding**: the need in your own words, and every acceptance criterion
   (from the issue, its parent and tasks, its comments), numbered `AC1…`.
2. **Open questions & assumptions**: what must be answered before coding, each
   with the assumption you will make if nobody answers. Do not bury a real
   ambiguity inside a confident plan.
3. **Approach**: the chosen design and why, one alternative rejected if it was
   a real option. Reference ADRs.
4. **Steps**: ordered, each independently verifiable and small enough for one
   commit: what changes (files/modules with `path`), which acceptance criteria
   it serves, how to verify it. If child tasks exist, map each step to its task
   and list work that has no task; never re-split existing tasks.
5. **Tests**: what will assert each acceptance criterion, following the
   project's test strategy.
6. **Risks & out of scope**.
7. **Complexity**: small / medium / large, with the reason. This drives the
   autonomy recommendation of `gitlab-issue-implement` (small → can be
   implemented directly; large → keep a human checkpoint after each step).

Only claim what you verified in the code. Anything you inferred is written as an
assumption.

**When the issue's own content is too thin to plan against with confidence**
(not just one or two minor gaps covered by a reasonable assumption, but the
issue lacking the acceptance criteria, scope boundary, or context needed to
write real steps): say so plainly before the plan, and draft a short
"Suggested clarification for the issue" block — the questions that should be
answered, written as something a human could paste into the GitLab issue
description or as a comment. This is text for the user to copy manually if
they choose to; **never post it to GitLab yourself**, and never let it stand
in for the "Open questions & assumptions" section above (the plan still
proceeds with stated assumptions regardless — this block is an offer to
improve the issue for next time, not a gate that blocks planning).

## 3. Iterate

Show the plan and revise with the user until they are happy. Nothing is posted
during iteration. When the user is happy, present the final plan through
`ExitPlanMode`: its approval only means "this plan is good locally" and leaves
plan mode. It is **not** consent to publish — that is a separate confirmation
in step 4. If the user rejects it in `ExitPlanMode`, keep iterating.

## 4. Offer to publish (only with explicit confirmation, never with `--local`)

With `--local`, stop after step 3. Otherwise do **not** open with a bare "shall
I publish?" question: compose the body, run the `--dry-run` calls, show exactly
what would be posted (comment + label change) and ask **once**, on that
content: "publish this exact content?". `ExitPlanMode`'s approval is not that
consent, but a separate "do you want to publish?" turn before the dry-run just
adds a round trip.

Compose the body (marker + visible title + attribution prefix + plan), write
it to a scratch file, then show exactly what will be posted via `--dry-run`
before doing anything for real. The version number lives in two places: the
invisible HTML marker (`find-marker` parses this) and a visible markdown
heading (a human scanning the issue needs to see it too — an HTML comment
alone is not enough, see below):

```
<!-- claude-plan v1 -->
## Plan (v1)

🤖 Claude plan (<model>, effort: <level>) — proposed plan, awaiting human review.
Approve by switching the label `agent-plan::proposed` to `agent-plan::approved`.

<the plan>
```

When posting a **new version** (not an in-place edit — see "Revision" below),
add a visible line right after the heading linking back to the previous note,
so the relationship between versions is visible on the issue itself, not just
encoded in the invisible marker:

```
<!-- claude-plan v2 -->
## Plan (v2)

Supersedes [the plan above (v1)](<issue_web_url>#note_<previous_note_id>).

🤖 Claude plan (<model>, effort: <level>) — proposed plan, awaiting human review.
Approve by switching the label `agent-plan::proposed` to `agent-plan::approved`.

<the plan>
```

`<issue_web_url>` is the issue's `web_url` from step 1's `issue get`;
`<previous_note_id>` is `find-marker`'s `note_id` — both already in hand, no
extra call needed.

- **The comment**: `issue note create --iid <iid> --kind plan --body-file <file> [--dry-run]`.
- **The label**: `issue label set --iid <iid> --add agent-plan::proposed [--dry-run]`
  (scoped labels replace each other, so this removes `agent-plan::approved` if
  a previous plan had it — say so when revising an approved plan). If the
  label does not exist in the project and the call fails, report it; do not
  create labels on your own.
- **Revision**: if step 1.2 found an existing marked comment, edit it in place
  only when `has_replies_or_reactions` was `false`
  (`issue note update --iid <iid> --kind plan --note-id <id> --body-file <file>`,
  heading stays `## Plan (v<n>)`, no "Supersedes" line — it's the same note,
  not a new version); otherwise post a new one, bumping the marker and heading
  to `v<n+1>` and adding the "Supersedes" line above, leaving the old note
  as-is.

Report the resulting note id. Then remind the user that approval is theirs:
change the label to `agent-plan::approved` in GitLab when satisfied.
