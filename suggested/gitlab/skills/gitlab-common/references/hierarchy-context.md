# Work-item hierarchy context

An issue's parent and child tasks are not returned by a plain issue fetch —
hierarchy is a work-item widget, reachable through GraphQL only. Collect it
whenever a skill needs the full picture around an issue (planning, reviewing
an MR against its requirements, implementing a task).

## Fetching it

Call `issue get --iid <iid> --with-hierarchy` (add `--comments` too when the
skill also needs the issue's notes — this collapses what used to be two
separate steps into one). The tool runs the GraphQL query internally (a
**query**, never a mutation — see `conventions.md`) and returns:

```json
{"hierarchy": {"parent": {...}|null, "children": [...], "linked_items": [...], "caps_hit": [...]}}
```

Verified on this instance on 2026-09-30 (schema accepted; the test issue had
no parent/children, so the shape of real data is not yet confirmed against a
real parent/child pair — treat that as still open until a skill run actually
exercises it). The instance also exposes an `AGENT_PLAN` widget (GitLab's
native Workplan, tied to Duo credits): the tool does not use it and no skill
should either.

## What to do with the result

- **Parent** (epic or issue), one level up: read its title and description
  for context and inherited acceptance criteria. If the item is itself a
  task, start from its parent to understand the overall need.
- **Children** (tasks): title, state, description (fetch with the same
  capability on the child iid when the description matters). A plan maps its
  steps onto existing tasks and flags work that has no task; it never
  re-splits what already exists. When implementing one task, do not spill
  onto its sibling tasks.
- **Linked items** (`blocks` / `is_blocked_by` / `relates_to`): note blockers
  and related work. Also check for MRs already linked, to avoid redoing work
  in flight.
- **Caps**: one level up, one level down, at most 50 children and 20 links.
  `caps_hit` lists which cap was reached, if any — say so explicitly in the
  output when non-empty.
- If `hierarchy` comes back `null` (the query errored or the widget is
  missing — `issue get`'s output includes `hierarchy_error` in that case), say
  so and continue with the issue alone; do not invent hierarchy.
