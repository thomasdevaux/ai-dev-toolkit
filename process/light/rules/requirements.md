# Requirements tracking

`docs/requirements.md` holds one markdown table: an id, the requirement in one
line, a status. Nothing else — no frontmatter, no per-requirement file. With
three fields, structured metadata doesn't pay for itself.

```markdown
| ID      | Requirement              | Status   |
|---------|--------------------------|----------|
| REQ-001 | CSV export of the report | done     |
| REQ-002 | Offline mode             | deferred |
```

Statuses: `proposed`, `accepted`, `done`, `deferred`, `rejected`,
`superseded`.

- **A section below the table, only when there's something to say** —
  `## REQ-002 — Offline mode` followed by the reasoning, a pointer to an
  ADR (`ADR-0004`), whatever a one-line entry can't carry. Most requirements
  never get one, and that's the normal case.
- **No link to code or tests.** That link goes stale faster than it helps, and
  the table would then vouch for coverage it can't see.
- **Adding or changing a feature updates its line.** Not necessarily in the
  same commit — there's no commit-time obligation here — but the list is
  expected to match reality by the time `audit-docs` runs.
- **Rejecting or deferring changes the status; it never deletes the line.**
  Keeping what was considered is what stops it being re-proposed a year later
  without a new argument. A requirement replaced by a later one is
  `superseded`, naming its replacement.
- **The format holds even when you're both author and client.** It looks like
  overhead on a small tool; it's what keeps the routine in place for the
  projects where it isn't optional.
