# Process profile (required choice)

- Every project adopts **exactly one** profile from the `process`
  choice-group — `process-none`, `process-light` or `process-full` — never
  two, never zero. `tools/sync` refuses to sync one while another is
  registered in `.claude/.toolkit-sync-state`.
- Before non-trivial work (a feature, a structural change, adding a
  dependency — not a one-line fix), check which profile is present.
- **A folder that is neither a git repository nor synced has no profile to
  pick** — a session opened anywhere to poke at a script behaves as
  `process-none` and doesn't get asked anything. Only raise the question in a
  repository.

## Choosing, when none is present

Stop and ask the user. Don't guess, and don't silently default to one. The
criterion is usage, not code size:

| Profile | For what | What it implies |
| --- | --- | --- |
| `process-none` | Script, one-shot, tinkering session. | Nothing to maintain: no docs, no requirements, no decisions. |
| `process-light` | An application or tool with its own repository. | Doc map, requirements list, decisions log. |
| `process-full` | Embedded, critical or certified software. | Extra rigor — **not designed yet**, see below. |

`process-full` is currently a stub: a project adopting it follows
`process-light`'s rules in the meantime. If its needs genuinely exceed them
(regulatory traceability, formal audit trail), say so to the user instead of
inventing ad hoc process — that gap is exactly what `process-full` will fill.

- If two profiles are somehow present, flag it as a conflict to resolve rather
  than picking one yourself.
