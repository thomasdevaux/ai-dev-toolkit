# Requirements tracking

`docs/requirements.md` holds one `##` section per requirement — an id in the
heading, a status, and free-form prose below it — and nothing else. One file,
flat: no per-requirement file, no frontmatter. Statuses: `proposed`,
`accepted`, `done`, `deferred`, `rejected`, `superseded`.

```markdown
## REQ-001 — CSV export of the report

Status: done

...as much prose as the requirement actually needs.
```

- **A short requirement stays short.** The prose can be a single sentence —
  the section heading doesn't force a paragraph where a line would do.
- **Adding or changing a feature updates its section.** Not necessarily in
  the same commit — there's no commit-time obligation here — but the file is
  expected to match reality by the time `audit-docs` runs.
- **Rejecting or deferring changes the status; it never deletes the
  section.** Keeping what was considered is what stops it being re-proposed a
  year later without a new argument. A requirement replaced by a later one is
  `superseded`, naming its replacement.
- **The format holds even when you're both author and client.** It looks like
  overhead on a small tool; it's what keeps the routine in place for the
  projects where it isn't optional.

`init-project-docs` seeds the file and shows its exact shape.
