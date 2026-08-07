# Requirements tracking

`docs/requirements.md` holds one markdown table — an id, the requirement in
one line, a status — and nothing else. With three fields, structured
metadata doesn't pay for itself. Statuses: `proposed`, `accepted`, `done`,
`deferred`, `rejected`, `superseded`.

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

`init-project-docs` seeds the table and shows its exact shape.
