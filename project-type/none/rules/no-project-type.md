# No project type

This project adopted the `project-type-none` profile: a script, a one-shot, a
useful hack. There is **no** long-term context to maintain here.

- **No document set is imposed.** No `docs/` tree, no ADR log, no
  requirements list. Don't create them "just in case".
- **No requirements or ADR tracking.** Whatever needs saying goes in the
  code, or in a `README.md` if the author wants one.
- **The common rules still apply** — security, language. A throwaway
  script that commits a secret commits it for good. The branch/merge
  workflow does not: it's `project-type-app`'s, deliberately. Commit
  messages are the exception — `commit-message-format` is a common skill
  and applies here too.
- **Still write code someone can read**: this profile lightens the process,
  not the quality.

## When to switch

Say it explicitly to the user as soon as one of these appears, rather than
silently accumulating debt:

- the work runs past a few sessions;
- it gets its own git repository;
- a second person uses it or contributes to it;
- it starts being distributed to someone else.

The switch is `project-type-app`. The profiles are mutually exclusive, so
it's one command against the toolkit checkout — never a hand-edit of
`.claude/.toolkit-sync-state`:

```
python -m tools.sync switch project-type project-type-app \
  --toolkit-root <checkout> --project-dir <this project>
```

It drops this profile, syncs the new one, and asks before deleting the files
this one left behind.
