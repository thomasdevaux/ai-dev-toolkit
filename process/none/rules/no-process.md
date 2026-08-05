# No process

This project adopted the `process-none` profile: a script, a one-shot, a
useful hack. There is **no** long-term context to maintain here.

- **No document set is imposed.** No `docs/` tree, no decisions log, no
  requirements list. Don't create them "just in case".
- **No requirements or decisions tracking.** Whatever needs saying goes in the
  code, or in a `README.md` if the author wants one.
- **The common rules still apply** — security, language, git. A throwaway
  script that commits a secret commits it for good.
- **Still write code someone can read**: this profile lightens the process,
  not the quality.

## When to switch

Say it explicitly to the user as soon as one of these appears, rather than
silently accumulating debt:

- the work runs past a few sessions;
- it gets its own git repository;
- a second person uses it or contributes to it;
- it starts being distributed to someone else.

The switch is `process-light`. It requires removing `process-none` from
`.claude/.toolkit-sync-state` first — the profiles are mutually exclusive.
