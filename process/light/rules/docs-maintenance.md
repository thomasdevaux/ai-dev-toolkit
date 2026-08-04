# Docs maintenance

- Every project keeps six docs current: `README.md` (entry point, links to
  the rest), `docs/architecture.md` (architecture + rationale), `docs/decisions.md`
  (the decisions log), `docs/user-manual.md`, `docs/developer-guide.md`,
  and `docs/build-and-release.md`.
- Read the one doc relevant to the change at hand before non-trivial or
  structural work — not the whole set eagerly. Pick the doc that matches
  what you're about to change.
- When a change alters something a doc describes (an architecture choice, a
  user-facing behavior, a build/release step), update that doc in the same
  change — don't let it drift from the code it describes.
- Log non-obvious or hard-to-reverse decisions in `docs/decisions.md` per the
  separate decisions-log rule, not inline in `docs/architecture.md`.
