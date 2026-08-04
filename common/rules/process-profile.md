# Process profile (required choice)

- Every project must adopt exactly one profile from the `process`
  choice-group — currently `process/light` or `process/full` — never
  both, never neither. The sync tool blocks syncing one while the other
  is already present (see `.claude/.toolkit-sync-state`).
- Before doing non-trivial work (a new feature, a structural change, adding
  a dependency — not a typo fix or a one-line tweak), check whether one of
  the two is present for this project.
- If neither is present, stop and ask the user which profile applies —
  `process/light` for the default real process discipline (docs,
  requirements, decisions, minimal testing policy), `process/full` only if
  the project needs core/critical/certified-grade rigor beyond that (note:
  `process/full` is currently a stub that just points back at
  `process/light` until its extra rigor is designed) — and tell them which
  entry to sync. Don't guess and don't silently default to one.
- If both are somehow present, flag it to the user as a conflict to
  resolve rather than picking one yourself.
