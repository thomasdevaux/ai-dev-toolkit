---
paths:
  - "src/safety/**"
---

# Safety-critical rules

Stricter rules that apply only to code under `src/safety/**`, on top of
everything in `misra.md`.

- Every change requires review from two engineers, not one — note this
  explicitly in the pull request description.
- No unbounded loops: every `while`/`for` must have a statically
  verifiable upper bound on iterations.
- Every function includes a traceability comment linking it to the
  requirement or hazard analysis ID it implements (e.g.
  `// traces: REQ-SAFE-014`).
- No function pointers or dynamic dispatch — control flow must be
  statically analyzable.
- Any deviation from `misra.md` in this directory requires a documented,
  reviewed justification comment at the point of deviation, not just a
  suppression pragma.
- When about to write or review a file matching this path, flag in your
  response that the `safety-review` subagent should review the change
  before it merges.
