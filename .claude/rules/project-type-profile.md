# Project-type profile (required choice)

- Every project adopts **exactly one** profile from the `project-type`
  choice-group — `project-type-none`, `project-type-app` or
  `project-type-embedded-fccu` — never two, never zero.
- Before non-trivial work (a feature, a structural change, adding a
  dependency — not a one-line fix), check which profile is present.
- **A folder that is neither a git repository nor synced has no profile to
  pick** — a session opened anywhere to poke at a script behaves as
  `project-type-none` and doesn't get asked anything. Only raise the
  question in a repository, with one exception: **someone saying they want
  to build an application or a tool has just stopped treating the folder as
  a scratch pad.** Raise it then, repo or not — that's the moment the
  choice is cheap.
- **When none is present: stop and ask the user.** Don't guess, and don't
  silently default to one. The criterion is usage, not code size — see
  `docs/maintaining.md`'s "The `project-type` group, in full" for what each
  profile means.
- If two profiles are somehow present, flag it as a conflict to resolve
  rather than picking one yourself.
