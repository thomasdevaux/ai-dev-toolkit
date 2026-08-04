# Requirements tracking

- Keep a single flat `docs/requirements.md`: one line per requirement — a
  short ID (`REQ-001`), a one-line description, a short rationale (why it
  matters), and a status (`proposed`, `accepted`, `implemented`, `deferred`,
  `rejected`, or `superseded`).
- No per-requirement file and no structured metadata beyond that — this is
  meant to stay a quick-scan list, not a database.
- Adding or changing a feature adds or updates its requirement line in the
  same change. Don't let the list drift from what the code actually does.
- Rejecting or deferring a requirement changes its status accordingly rather
  than deleting the line — keep the history of what was considered, so it
  isn't re-proposed without a new argument. A requirement replaced by a later
  one is marked `superseded`, noting which one replaced it.
